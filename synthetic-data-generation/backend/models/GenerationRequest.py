from pydantic import BaseModel

class GenerationRequest(BaseModel):
    """
    Represents a request to generate a YAML configuration for synthetic data generation.
    """
    description: str 