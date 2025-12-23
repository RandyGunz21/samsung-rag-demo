"""
RAG Service - Retrieval Routes.

Endpoints for document retrieval operations.
"""

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import (
    RetrieveRequest,
    RetrieveResponse,
    MultiQueryRetrieveRequest,
    MultiQueryRetrieveResponse,
    DocumentResult,
    MultiQueryRelevanceInfo,
)
from ..dependencies import get_rag_engine

router = APIRouter(prefix="/api/v1", tags=["Retrieval"])


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_documents(
    request: RetrieveRequest,
    engine=Depends(get_rag_engine),
):
    """
    Retrieve relevant documents for a query.

    Uses vector similarity search to find documents matching the query.
    """
    try:
        result = engine.retrieve(
            query=request.query,
            top_k=request.top_k,
            search_type=request.search_type,
            similarity_threshold=request.similarity_threshold,
            filters=request.filters if request.filters else None,
        )

        return RetrieveResponse(
            documents=[DocumentResult(**doc) for doc in result["documents"]],
            query_processed=result["query_processed"],
            search_type_used=result["search_type_used"],
            total_found=result["total_found"],
            processing_time_ms=result["processing_time_ms"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-query-retrieve", response_model=MultiQueryRetrieveResponse)
async def multi_query_retrieve(
    request: MultiQueryRetrieveRequest,
    engine=Depends(get_rag_engine),
):
    """
    Retrieve documents using automatic query expansion.

    Generates multiple query variations for better recall.
    """
    try:
        result = engine.multi_query_retrieve(
            query=request.query,
            num_queries=request.num_queries,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        return MultiQueryRetrieveResponse(
            documents=[DocumentResult(**doc) for doc in result["documents"]],
            generated_queries=result["generated_queries"],
            relevance_info=MultiQueryRelevanceInfo(**result["relevance_info"]),
            processing_time_ms=result["processing_time_ms"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
