"""RAG Service API Module."""

from .routes import retrieve_router, ingest_router, management_router
from .dependencies import get_rag_engine

__all__ = [
    "retrieve_router",
    "ingest_router",
    "management_router",
    "get_rag_engine",
]
