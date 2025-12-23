"""
AI Agent Service - Session Routes.

Endpoints for conversation session management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import (
    SessionListResponse,
    SessionHistoryResponse,
    SessionInfo,
    MessageHistory,
    DeleteResponse,
    HealthResponse,
)
from ..dependencies import get_session_manager, get_service_health

router = APIRouter(prefix="/api/v1", tags=["Sessions"])


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    session_manager=Depends(get_session_manager),
):
    """
    Get all active conversation sessions.
    """
    result = session_manager.list_sessions(limit=limit, offset=offset)

    sessions = [
        SessionInfo(
            session_id=UUID(s["session_id"]),
            created_at=s["created_at"],
            last_activity=s["last_activity"],
            message_count=s["message_count"],
            title=s.get("title"),
        )
        for s in result["sessions"]
    ]

    return SessionListResponse(
        sessions=sessions,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: UUID,
    limit: int = 50,
    before: str = None,
    session_manager=Depends(get_session_manager),
):
    """
    Retrieve conversation history for a session.
    """
    result = session_manager.get_session_history(
        session_id=session_id,
        limit=limit,
        before=before,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )

    messages = [
        MessageHistory(
            id=m["id"],
            role=m["role"],
            content=m["content"],
            classification=m.get("classification"),
            sources=m.get("sources"),
            created_at=m["created_at"],
        )
        for m in result["messages"]
    ]

    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
        has_more=result["has_more"],
    )


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: UUID,
    session_manager=Depends(get_session_manager),
):
    """
    Clear conversation history and delete session.
    """
    deleted = session_manager.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )

    return DeleteResponse(
        status="success",
        message="Session deleted successfully",
        session_id=session_id,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(health=Depends(get_service_health)):
    """
    Check service health and dependencies.
    """
    return HealthResponse(**health)
