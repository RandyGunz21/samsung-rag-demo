"""
AI Agent Service - Response Schemas.

Pydantic models for API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Source document in response."""
    content: str
    metadata: Dict[str, Any]
    relevance_score: float


class RelevanceInfo(BaseModel):
    """Relevance scoring information."""
    best_score: float
    threshold: float
    documents_found: int


class ChatResponse(BaseModel):
    """Chat response to frontend."""
    id: str = Field(default_factory=lambda: f"msg_{uuid4().hex[:12]}")
    session_id: UUID
    answer: str
    classification: str  # factual, conversational, ambiguous
    is_relevant: bool
    context_used: bool = False
    expanded_question: Optional[str] = None
    relevance_info: Optional[RelevanceInfo] = None
    sources: List[SourceDocument] = Field(default_factory=list)
    num_sources: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionInfo(BaseModel):
    """Session information."""
    session_id: UUID
    created_at: datetime
    last_activity: datetime
    message_count: int
    title: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of sessions response."""
    sessions: List[SessionInfo]
    total: int
    limit: int
    offset: int


class MessageHistory(BaseModel):
    """Single message in history."""
    id: str
    role: str  # user, assistant
    content: str
    classification: Optional[str] = None
    sources: Optional[List[SourceDocument]] = None
    created_at: datetime


class SessionHistoryResponse(BaseModel):
    """Session history response."""
    session_id: UUID
    messages: List[MessageHistory]
    has_more: bool


class DeleteResponse(BaseModel):
    """Delete response."""
    status: str
    message: str
    session_id: UUID


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    services: Dict[str, str]
    uptime_seconds: int


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    error_code: str
