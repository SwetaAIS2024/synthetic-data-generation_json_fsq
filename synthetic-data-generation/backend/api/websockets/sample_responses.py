from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import List, Dict, Any, Optional
import json
import asyncio
import math
from datetime import datetime
from models.SampleResponse import SampleResponse
from models.YAMLConfig import YAMLConfig

router = APIRouter()

# Store active connections for each YAML config
class SampleResponseConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, config_id: str, websocket: WebSocket):
        await websocket.accept()
        if config_id not in self.active_connections:
            self.active_connections[config_id] = []
        self.active_connections[config_id].append(websocket)

    def disconnect(self, config_id: str, websocket: WebSocket):
        if config_id in self.active_connections:
            if websocket in self.active_connections[config_id]:
                self.active_connections[config_id].remove(websocket)
            if not self.active_connections[config_id]:
                del self.active_connections[config_id]

    async def broadcast_to_config(self, config_id: str, message: str):
        if config_id in self.active_connections:
            for connection in self.active_connections[config_id]:
                await connection.send_text(message)

sample_response_manager = SampleResponseConnectionManager()

# Helper function to format sample response data for the frontend
def format_sample_response(response: Dict[str, Any]) -> Dict[str, Any]:
    # Convert MongoDB ObjectId to string and use last 8 characters
    full_id = str(response.id) if hasattr(response, 'id') else str(response.get("_id", ""))
    response_id = full_id[-8:] if len(full_id) >= 8 else full_id
    
    # Format created_at date
    created_at = response.created_at if hasattr(response, 'created_at') else response.get("created_at", "")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    elif isinstance(created_at, dict) and "$date" in created_at:
        created_at = created_at["$date"]
    
    # Handle both document and dictionary access
    def get_attr(obj, attr, default=""):
        if hasattr(obj, attr):
            return getattr(obj, attr, default)
        elif isinstance(obj, dict):
            return obj.get(attr, default)
        return default
    
    return {
        "id": full_id,  # Keep the full ID for database operations
        "display_id": response_id,  # Add the shortened display ID
        "yaml_config_id": get_attr(response, "yaml_config_id", ""),
        "created_at": created_at,
        "temperature": get_attr(response, "temperature", 0.0),
        "top_p": get_attr(response, "top_p", 0.0),
        "max_tokens": get_attr(response, "max_tokens", 0),
        "seed_value": get_attr(response, "seed_value", 0),
        "model": get_attr(response, "model", ""),
        "response_text": get_attr(response, "response_text", ""),
        "input_request": get_attr(response, "input_request", ""),
        "tokens_per_second": get_attr(response, "tokens_per_second", 0.0),
        "time_to_first_token": get_attr(response, "time_to_first_token", 0.0),
        "latency": get_attr(response, "latency", 0.0),
        "total_tokens": get_attr(response, "total_tokens", 0)
    }

@router.websocket("/ws/config/{config_id}/responses")
async def websocket_endpoint(
    websocket: WebSocket,
    config_id: str,
    page: int = Query(1),
    page_size: int = Query(10)
):
    await sample_response_manager.connect(config_id, websocket)
    try:
        # Send initial data
        await send_paginated_responses(websocket, config_id, page, page_size)
        
        # Start background task to periodically update data
        update_task = asyncio.create_task(periodic_updates(websocket, config_id, page, page_size))
        
        # Listen for client messages
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            if request.get("type") == "pagination":
                page = request.get("page", 1)
                page_size = request.get("page_size", 10)
                await send_paginated_responses(websocket, config_id, page, page_size)
            
    except WebSocketDisconnect:
        sample_response_manager.disconnect(config_id, websocket)
        # Cancel the update task when the client disconnects
        update_task.cancel()
    except Exception as e:
        print(f"WebSocket error: {e}")
        sample_response_manager.disconnect(config_id, websocket)

async def send_paginated_responses(websocket: WebSocket, config_id: str, page: int, page_size: int):
    try:
        # Verify that the YAML config exists
        yaml_config = YAMLConfig.find_by_id(config_id)
        if not yaml_config:
            await websocket.send_json({
                "type": "data_update",
                "error": "YAML config not found"
            })
            return
        
        # Get total count for this config
        total_count = SampleResponse.objects(yaml_config_id=config_id).count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Get paginated responses for this config
        responses = SampleResponse.objects(yaml_config_id=config_id).skip((page - 1) * page_size).limit(page_size).order_by("-created_at")
        
        # Format data for frontend
        formatted_responses = []
        for response in responses:
            try:
                formatted_response = format_sample_response(response)
                formatted_responses.append(formatted_response)
            except Exception as e:
                print(f"Error formatting sample response: {e}")
                import traceback
                traceback.print_exc()
        
        # Send data with pagination info
        await websocket.send_json({
            "type": "data_update",
            "data": formatted_responses,
            "config": {
                "id": str(yaml_config.id),
                "name": yaml_config.name,
                "progress": {
                    "completed": total_count,
                    "total": yaml_config.number_of_samples,
                    "percent": min(100, round((total_count / yaml_config.number_of_samples) * 100)) if yaml_config.number_of_samples > 0 else 0
                }
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count
            }
        })
    except Exception as e:
        print(f"Error sending paginated responses data: {e}")
        import traceback
        traceback.print_exc()
        # Send empty data with error message
        await websocket.send_json({
            "type": "data_update",
            "data": [],
            "pagination": {
                "page": 1,
                "page_size": page_size,
                "total_pages": 1,
                "total_count": 0
            },
            "error": str(e)
        })

async def periodic_updates(websocket: WebSocket, config_id: str, page: int, page_size: int):
    """Periodically send updated responses data to the client"""
    while True:
        await asyncio.sleep(5)  # Update every 5 seconds
        try:
            await send_paginated_responses(websocket, config_id, page, page_size)
        except Exception as e:
            print(f"Error in periodic update: {e}")
            break

@router.websocket("/ws/response/{response_id}")
async def response_detail_websocket(
    websocket: WebSocket,
    response_id: str
):
    await websocket.accept()
    try:
        # Send initial response data
        response = SampleResponse.find_by_id(response_id)
        if response:
            await websocket.send_json({
                "type": "response_detail",
                "data": format_sample_response(response)
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Response not found"
            })
        
        # No need for periodic updates for a single response as it won't change
        
        # Keep connection open and handle any requests
        while True:
            data = await websocket.receive_text()
            # Currently no specific actions needed for sample response details
            # But we can add them in the future if needed
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}") 