"""AI Agent Service API Schemas."""

from .requests import ChatRequest, ChatOptions, WebSocketMessage
from .responses import (
    SourceDocument,
    RelevanceInfo,
    ChatResponse,
    SessionInfo,
    SessionListResponse,
    MessageHistory,
    SessionHistoryResponse,
    DeleteResponse,
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    # Requests
    "ChatRequest",
    "ChatOptions",
    "WebSocketMessage",
    # Responses
    "SourceDocument",
    "RelevanceInfo",
    "ChatResponse",
    "SessionInfo",
    "SessionListResponse",
    "MessageHistory",
    "SessionHistoryResponse",
    "DeleteResponse",
    "HealthResponse",
    "ErrorResponse",
]
