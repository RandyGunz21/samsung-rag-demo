"""
RAG Service - FastAPI Application.

Document retrieval and pipeline orchestration API.
Implements FR-ORCH-001, FR-ORCH-002, FR-ORCH-003, OR-PIPE-001.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import retrieve_router, ingest_router, management_router
from src.api.dependencies import get_rag_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Initialize RAG engine
    print("Starting RAG Service...")
    engine = get_rag_engine()
    print(f"RAG Engine initialized. Vector store ready.")
    yield
    # Shutdown
    print("Shutting down RAG Service...")


app = FastAPI(
    title="RAG Service",
    description="Document retrieval and pipeline orchestration API with Prefect integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://agent-service:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(retrieve_router)
app.include_router(ingest_router)
app.include_router(management_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RAG Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
