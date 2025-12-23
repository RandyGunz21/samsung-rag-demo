"""RAG Service API Routes."""

from .retrieve import router as retrieve_router
from .ingest import router as ingest_router
from .management import router as management_router

__all__ = ["retrieve_router", "ingest_router", "management_router"]
