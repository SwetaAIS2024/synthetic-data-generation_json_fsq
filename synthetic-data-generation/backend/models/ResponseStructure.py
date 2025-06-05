from pydantic import BaseModel, model_validator, ValidationError
from enum import Enum
from typing import List


class RoleType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: RoleType
    content: str


class ResponseStructure(BaseModel):
    messages: List[Message]

    @model_validator(mode='before')
    def check_user_assistant_pairs(cls, values):
        messages = values.get('messages')

        # Ensure exactly 2 messages
        if len(messages) != 2:
            raise ValueError("There must be exactly 2 messages: one from 'user' and one from 'assistant'.")

        # Check if the first message is from 'user' and the second is from 'assistant'
        if messages[0].role != RoleType.USER:
            raise ValueError("The first message must be from 'user'.")
        if messages[1].role != RoleType.ASSISTANT:
            raise ValueError("The second message must be from 'assistant'.")

        return values