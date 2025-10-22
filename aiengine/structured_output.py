"""
Structured output models for AI responses using Pydantic.
"""
from pydantic import BaseModel, Field
from typing import Optional


class AIResponse(BaseModel):
    """
    Structured output model for AI responses.
    """
    needs_reply: bool = Field(
        description="Whether the AI agent should send a reply to WhatsApp",
        default=True
    )
    response_text: str = Field(
        description="The message to send to WhatsApp or explanation why no reply is needed",
        min_length=1
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "needs_reply": True,
                "response_text": "Hello! How can I help you today?"
            }
        }
