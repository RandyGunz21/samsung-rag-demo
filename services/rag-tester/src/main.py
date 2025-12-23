"""FastAPI application for RAG-tester service.

Provides REST API for:
- Test dataset management (CRUD)
- Evaluation job submission and monitoring
- Evaluation results retrieval
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .storage import storage
from .api import datasets, evaluations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application.

    Ensures data directories exist on startup.
    """
    # Startup: ensure directories exist
    storage._ensure_dirs()
    print(f"✅ Data directories initialized at: {settings.data_dir}")
    print(f"✅ RAG Service URL: {settings.rag_service_url}")
    print(f"✅ Redis URL: {settings.redis_url}")

    yield

    # Shutdown: cleanup if needed
    print("👋 Shutting down RAG-tester service")


# Create FastAPI app
app = FastAPI(
    title="RAG-tester Service",
    description="Evaluation service for RAG system quality testing with NDCG, MAP, MRR metrics",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(datasets.router)
app.include_router(evaluations.router)


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "rag-tester",
        "version": "1.0.0",
    }


# Root endpoint
@app.get("/")
def root():
    """Root endpoint with service information."""
    return {
        "service": "RAG-tester",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "datasets": "/test-datasets",
            "evaluations": "/evaluations",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
