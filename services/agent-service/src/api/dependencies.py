"""
AI Agent Service - FastAPI Dependencies.

Dependency injection for shared resources.
"""

import time
from typing import Any, Dict

from ..agents import get_chat_agent as _get_chat_agent, get_session_manager as _get_session_manager
from ..rag_client import get_rag_client

# Service start time for uptime tracking
_start_time = time.time()


def get_chat_agent():
    """Get chat agent instance."""
    return _get_chat_agent()


def get_session_manager():
    """Get session manager instance."""
    return _get_session_manager()


async def get_service_health() -> Dict[str, Any]:
    """Get service health status."""
    services = {}

    # Check RAG Service
    try:
        rag_client = get_rag_client()
        health = await rag_client.health_check()
        services["rag_service"] = "connected" if health.get("status") == "healthy" else "degraded"
    except Exception:
        services["rag_service"] = "disconnected"

    # Check Ollama LLM
    try:
        agent = get_chat_agent()
        agent._get_llm()  # Trigger LLM initialization
        services["ollama_llm"] = "available"
    except Exception:
        services["ollama_llm"] = "unavailable"

    uptime = int(time.time() - _start_time)
    all_healthy = all(v in ["connected", "available"] for v in services.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": "1.0.0",
        "services": services,
        "uptime_seconds": uptime,
    }
