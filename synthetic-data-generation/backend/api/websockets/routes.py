from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import asyncio
from models.YAMLConfig import YAMLConfig
import math
from api.websockets import sample_responses
#from api.websockets import yaml_config_details  # We'll create this file later

router = APIRouter()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
# NEW: Helper function to format YAML config data for the frontend
def format_yaml_config_data(config: Dict[str, Any]) -> Dict[str, Any]:
    # Convert MongoDB ObjectId to string and use last 8 characters
    full_id = str(config.id) if hasattr(config, 'id') else str(config.get("_id", ""))
    config_id = full_id[-8:] if len(full_id) >= 8 else full_id
    
    # Format dates
    created_at = config.created_at if hasattr(config, 'created_at') else config.get("created_at", "")
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
    
    # Calculate progress percentage
    total_responses = get_attr(config, "total_responses_generated", 0)
    target_samples = get_attr(config, "number_of_samples", 1)  # Default to 1 to avoid division by zero
    progress_percent = min(100, round((total_responses / target_samples) * 100)) if target_samples > 0 else 0
    
    # Get performance metrics (these are now property methods that calculate averages)
    tokens_per_second = get_attr(config, "tokens_per_second", 0)
    time_to_first_token = get_attr(config, "time_to_first_token", 0)
    queries_per_second = get_attr(config, "queries_per_second", 0)
    latency = get_attr(config, "average_latency", 0)
    
    return {
        "id": full_id,  # Keep the full ID for database operations
        "display_id": config_id,  # Add the shortened display ID
        "name": get_attr(config, "name", "Unnamed Config"),
        "created_at": created_at,
        "model": get_attr(config, "model", "gpt-4o-mini"),
        "number_of_samples": target_samples,
        "total_responses_generated": total_responses,
        "progress_percent": progress_percent,
        "progress_status": "Complete" if progress_percent == 100 else "In Progress",
        "output_format": get_attr(config, "output_format", "json"),
        "avg_tokens_per_second": round(tokens_per_second, 2),
        "avg_time_to_first_token": round(time_to_first_token, 2),
        "avg_queries_per_second": round(queries_per_second, 2),
        "avg_latency": round(latency, 2),
        "temperature_range": get_attr(config, "temperature_range", [0.7, 0.9]),
        "top_p": get_attr(config, "top_p", 0.9),
        "max_tokens": get_attr(config, "max_tokens", 200)
    }


# NEW: WebSocket endpoint for YAML configs
@router.websocket("/ws/yaml_configs")
async def yaml_configs_websocket_endpoint(
    websocket: WebSocket,
    page: int = Query(1),
    page_size: int = Query(10),
    live_mode: bool = Query(True)
):
    await manager.connect(websocket)
    try:
        # Initial data load
        await send_paginated_yaml_configs(websocket, page, page_size, live_mode)
        
        # Start background task to periodically update data
        update_task = asyncio.create_task(periodic_yaml_config_updates(websocket, page, page_size, live_mode))
        
        # Listen for client messages (pagination requests, etc.)
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            if request.get("type") == "pagination":
                page = request.get("page", 1)
                page_size = request.get("page_size", 10)
                await send_paginated_yaml_configs(websocket, page, page_size, live_mode)
            
            elif request.get("type") == "toggle_live_mode":
                live_mode = request.get("live_mode", True)
                # Reset to first page when enabling live mode
                if live_mode:
                    page = 1
                await send_paginated_yaml_configs(websocket, page, page_size, live_mode)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Cancel the update task when the client disconnects
        update_task.cancel()
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# NEW: Function to send paginated YAML config data
async def send_paginated_yaml_configs(websocket: WebSocket, page: int, page_size: int, live_mode: bool = True):
    try:
        # Get total count for pagination
        total_count = YAMLConfig.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Get paginated configs
        if live_mode:
            configs = YAMLConfig.find(page=page, per_page=page_size).order_by("-created_at")
        else:
            configs = YAMLConfig.find(page=page, per_page=page_size)
        
        # Format data for frontend
        formatted_configs = []
        for config in configs:
            try:
                formatted_config = format_yaml_config_data(config)
                formatted_configs.append(formatted_config)
            except Exception as e:
                print(f"Error formatting YAML config: {e}")
                import traceback
                traceback.print_exc()
        
        # Send data with pagination info
        await websocket.send_json({
            "type": "data_update",
            "data": formatted_configs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count
            },
            "live_mode": live_mode
        })
    except Exception as e:
        print(f"Error sending paginated YAML config data: {e}")
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
            "live_mode": live_mode,
            "error": str(e)
        })

async def periodic_yaml_config_updates(websocket: WebSocket, page: int, page_size: int, live_mode: bool = True):
    """Periodically send updated YAML config data to the client"""
    while True:
        await asyncio.sleep(5)  # Update every 5 seconds
        try:
            await send_paginated_yaml_configs(websocket, page, page_size, live_mode)
        except Exception as e:
            print(f"Error in periodic YAML config update: {e}")
            break

# Include the YAML config details router
#router.include_router(yaml_config_details.router)

# Include the sample responses router
router.include_router(sample_responses.router)
