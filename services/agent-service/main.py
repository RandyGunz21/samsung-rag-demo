"""
AI Agent Service - Main FastAPI Application.

LLM orchestration, chat interface, and session management.
Communicates with RAG Service for document retrieval.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import chat_router, sessions_router, frontend_compat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("AI Agent Service starting...")
    print(f"RAG Service URL: {os.getenv('RAG_SERVICE_URL', 'http://localhost:8000')}")
    print(f"Ollama URL: {os.getenv('OLLAMA_URL', 'http://localhost:11434')}")
    yield
    # Shutdown
    print("AI Agent Service shutting down...")


app = FastAPI(
    title="AI Agent Service",
    description="LLM orchestration, chat interface, and session management for RAG-powered Q&A",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(frontend_compat_router)  # Vercel AI Chatbot compatibility


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "AI Agent Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8001")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
