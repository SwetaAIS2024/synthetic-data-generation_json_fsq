from fastapi import APIRouter, HTTPException
from models.GenerationRequest import GenerationRequest
from modules.processor import generate_yaml_config

router = APIRouter()

@router.post("/generate-yaml")
async def generate_yaml_endpoint(request: GenerationRequest):
    """Endpoint to generate a YAML configuration based on the user's description"""
    return await generate_yaml_config(request) 