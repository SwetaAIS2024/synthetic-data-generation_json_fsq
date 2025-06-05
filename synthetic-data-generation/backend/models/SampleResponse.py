from mongoengine import *
from datetime import datetime
from .base_model import BaseModel

class SampleResponse(BaseModel):
    yaml_config_id = StringField(required=True)
    created_at = DateTimeField(default=datetime.now)
    
    # Input parameters
    temperature = FloatField(required=True)
    top_p = FloatField(required=True)
    prompt = StringField(required=True)
    input_request = StringField(required=False)  # Store the specific example input used
    max_tokens = IntField(required=True)
    seed_value = IntField(required=True)
    model = StringField(required=True)
    
    # Response data
    response_text = StringField(required=True)
    
    # Performance metrics
    tokens_per_second = FloatField(required=True)
    time_to_first_token = FloatField(required=True)  # In milliseconds
    latency = FloatField(required=True)  # In milliseconds
    total_tokens = IntField(required=True)
    
    meta = {
        'collection': 'sample_responses',
        'indexes': [
            'yaml_config_id',
            'created_at'
        ]
    }
    
    def to_dict(self):
        """
        Convert the sample response to a dictionary suitable for JSON serialization.
        This format is appropriate for creating a dataset to upload to Fireworks AI.
        
        Returns:
            Dictionary with sample data formatted for the dataset
        """
        return {
            "id": str(self.id),
            "prompt": self.prompt,
            "input_request": self.input_request,
            "completion": self.response_text,
            "metadata": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "seed_value": self.seed_value,
                "model": self.model,
                "yaml_config_id": self.yaml_config_id,
                "created_at": self.created_at.isoformat(),
                "metrics": {
                    "tokens_per_second": self.tokens_per_second,
                    "time_to_first_token": self.time_to_first_token,
                    "latency": self.latency,
                    "total_tokens": self.total_tokens
                }
            }
        } 