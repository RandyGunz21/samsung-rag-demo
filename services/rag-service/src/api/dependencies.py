"""
RAG Service - FastAPI Dependencies.

Dependency injection for shared resources.
"""

from functools import lru_cache
from typing import Optional

from ..core.rag_engine import RAGEngine

# Global engine instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """
    Get or create RAG Engine instance.

    Uses singleton pattern for efficiency.
    """
    global _rag_engine

    if _rag_engine is None:
        _rag_engine = RAGEngine()

    return _rag_engine


def reset_rag_engine():
    """Reset the RAG engine (for testing)."""
    global _rag_engine
    _rag_engine = None
