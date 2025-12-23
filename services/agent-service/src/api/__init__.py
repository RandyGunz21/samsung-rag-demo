"""AI Agent Service API Module."""

from .routes import chat_router, sessions_router, frontend_compat_router
from .dependencies import get_chat_agent, get_session_manager, get_service_health

__all__ = [
    "chat_router",
    "sessions_router",
    "frontend_compat_router",
    "get_chat_agent",
    "get_session_manager",
    "get_service_health",
]
