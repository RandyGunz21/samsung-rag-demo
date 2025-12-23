"""
AI Agent Service - Request Schemas.

Pydantic models for API request validation.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatOptions(BaseModel):
    """Options for chat requests."""
    show_sources: bool = Field(default=True, description="Include source documents")
    similarity_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Minimum relevance score"
    )
    max_sources: int = Field(default=4, ge=1, le=20, description="Max sources to return")


class ChatRequest(BaseModel):
    """Chat request from frontend."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: Optional[UUID] = Field(default=None, description="Session ID for context")
    options: ChatOptions = Field(default_factory=ChatOptions)


class WebSocketMessage(BaseModel):
    """WebSocket message from client."""
    type: str = Field(..., pattern="^(message|clear_history|ping)$")
    content: Optional[str] = None
    options: Optional[ChatOptions] = None
