"""
AI Agent Service - Chat Routes.

Endpoints for chat and streaming interactions.
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import (
    ChatRequest,
    ChatResponse,
    SourceDocument,
    RelevanceInfo,
)
from ..dependencies import get_chat_agent

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent=Depends(get_chat_agent),
):
    """
    Send a chat message and receive a complete response.

    Handles query classification, RAG retrieval, and LLM response generation.
    """
    try:
        result = await agent.chat(
            message=request.message,
            session_id=request.session_id,
            show_sources=request.options.show_sources,
            similarity_threshold=request.options.similarity_threshold,
            max_sources=request.options.max_sources,
        )

        # Convert to response model
        sources = []
        if result.get("sources"):
            sources = [
                SourceDocument(
                    content=s["content"],
                    metadata=s.get("metadata", {}),
                    relevance_score=s.get("relevance_score", 0.0),
                )
                for s in result["sources"]
            ]

        relevance_info = None
        if result.get("relevance_info"):
            relevance_info = RelevanceInfo(**result["relevance_info"])

        return ChatResponse(
            id=f"msg_{uuid4().hex[:12]}",
            session_id=result["session_id"],
            answer=result["answer"],
            classification=result["classification"],
            is_relevant=result["is_relevant"],
            context_used=result.get("context_used", False),
            expanded_question=result.get("expanded_question"),
            relevance_info=relevance_info,
            sources=sources,
            num_sources=result.get("num_sources", 0),
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    agent=Depends(get_chat_agent),
):
    """
    Stream chat response tokens in real-time using SSE.

    Returns Server-Sent Events with token, classification, sources, and done events.
    """
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # Send start event
            yield f"event: start\ndata: {{\"session_id\": \"{request.session_id or uuid4()}\", \"message_id\": \"msg_{uuid4().hex[:12]}\"}}\n\n"

            # Get response (for now, non-streaming then chunk it)
            result = await agent.chat(
                message=request.message,
                session_id=request.session_id,
                show_sources=request.options.show_sources,
                similarity_threshold=request.options.similarity_threshold,
                max_sources=request.options.max_sources,
            )

            # Send classification event
            yield f"event: classification\ndata: {{\"classification\": \"{result['classification']}\", \"is_relevant\": {str(result['is_relevant']).lower()}}}\n\n"

            # Stream answer tokens (simulate streaming by chunking)
            answer = result["answer"]
            words = answer.split()

            for i, word in enumerate(words):
                # Add space before word (except first)
                token = word if i == 0 else f" {word}"
                import json
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"
                await asyncio.sleep(0.02)  # Small delay for streaming effect

            # Send sources if available
            if result.get("sources"):
                import json
                sources_data = json.dumps({
                    "sources": result["sources"],
                    "num_sources": result.get("num_sources", 0)
                })
                yield f"event: sources\ndata: {sources_data}\n\n"

            # Send done event
            yield f"event: done\ndata: {{\"total_tokens\": {len(words)}, \"processing_time_ms\": 0}}\n\n"

        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
