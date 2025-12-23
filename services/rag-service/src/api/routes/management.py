"""
RAG Service - Management Routes.

Endpoints for cache, stats, and collection management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from ..schemas import (
    PipelineStats,
    ClearCacheResponse,
    CollectionInfo,
    HealthResponse,
    DocumentListResponse,
)
from ..dependencies import get_rag_engine

router = APIRouter(prefix="/api/v1", tags=["Management"])


@router.get("/stats", response_model=PipelineStats)
async def get_pipeline_stats(engine=Depends(get_rag_engine)):
    """
    Get pipeline execution statistics.

    Implements FR-ORCH-003: Pipeline Monitoring.
    """
    result = engine.get_stats()
    return PipelineStats(**result)


@router.post("/clear-cache", response_model=ClearCacheResponse)
async def clear_cache(engine=Depends(get_rag_engine)):
    """
    Clear document hash cache.

    Use this for full re-ingestion of all documents.
    """
    result = engine.clear_cache()
    return ClearCacheResponse(**result)


@router.get("/collection", response_model=CollectionInfo)
async def get_collection_info(engine=Depends(get_rag_engine)):
    """
    Get vector store collection information.
    """
    result = engine.get_collection_info()
    return CollectionInfo(**result)


@router.get("/health", response_model=HealthResponse)
async def health_check(engine=Depends(get_rag_engine)):
    """
    Check service health and component status.
    """
    result = engine.get_health()
    return HealthResponse(**result)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search filter"),
    engine=Depends(get_rag_engine),
):
    """
    List documents in the vector store.

    Returns paginated list of indexed documents with metadata.
    """
    result = engine.list_documents(page=page, limit=limit, search=search)
    return DocumentListResponse(**result)
