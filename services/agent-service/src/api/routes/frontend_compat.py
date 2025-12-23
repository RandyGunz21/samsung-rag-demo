"""
AI Agent Service - Frontend Compatibility Routes.

Adapter endpoints for Vercel AI Chatbot frontend compatibility.
Converts frontend message format to Agent Service format.
"""

import json
from typing import AsyncGenerator, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..dependencies import get_chat_agent


router = APIRouter(tags=["Frontend Compatibility"])


class FrontendMessage(BaseModel):
    """Message in Vercel AI SDK format."""
    role: str  # user, assistant, system
    content: str


class FrontendChatRequest(BaseModel):
    """Chat request from Vercel AI Chatbot frontend."""
    messages: List[FrontendMessage]


@router.post("/api/chat")
async def frontend_chat(
    request: FrontendChatRequest,
    agent=Depends(get_chat_agent),
):
    """
    Frontend-compatible streaming chat endpoint.

    Accepts Vercel AI SDK message format and returns SSE stream
    in the format expected by frontend (Vercel AI SDK compatible).

    Frontend sends:
        {messages: [{role: "user", content: "..."}]}

    Returns SSE:
        data: {"type":"text-delta","content":"word "}
        data: {"type":"text-end"}
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Get last user message
    last_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_message = msg.content
            break

    if not last_message:
        raise HTTPException(status_code=400, detail="No user message found")

    async def generate_sse_stream() -> AsyncGenerator[str, None]:
        try:
            # Call agent service (uses RAG Service internally)
            result = await agent.chat(
                message=last_message,
                session_id=None,  # Frontend handles session
                show_sources=True,  # Enable source citations
                similarity_threshold=0.5,
                max_sources=4,
            )

            # Stream response in Vercel AI SDK format
            answer = result.get("answer", "")
            words = answer.split()

            for i, word in enumerate(words):
                # Add space after each word except last
                content = word if i == len(words) - 1 else word + " "

                chunk = {
                    "type": "text-delta",
                    "content": content,
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            # Send sources if available
            sources = result.get("sources", [])
            if sources:
                sources_chunk = {
                    "type": "sources",
                    "sources": [
                        {
                            "title": source.get("metadata", {}).get("source", "Unknown source"),
                            "url": source.get("metadata", {}).get("source", "#"),
                            "content": source.get("content", "")[:200],  # Preview first 200 chars
                            "relevance_score": source.get("relevance_score", 0.0),
                            "page": source.get("metadata", {}).get("page"),
                            "chunk_index": source.get("metadata", {}).get("chunk_index"),
                        }
                        for source in sources
                    ],
                    "num_sources": len(sources),
                }
                yield f"data: {json.dumps(sources_chunk)}\n\n"

            # Send end marker
            yield f'data: {json.dumps({"type": "text-end"})}\n\n'

        except Exception as e:
            # Send error in Vercel AI SDK format
            error_chunk = {
                "type": "error",
                "error": str(e),
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/health")
async def frontend_health():
    """
    Health check endpoint compatible with frontend expectations.
    """
    return {
        "status": "healthy",
        "service": "AI Agent Service",
        "version": "1.0.0",
    }
