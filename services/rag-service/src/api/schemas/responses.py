"""
RAG Service - Response Schemas.

Pydantic models for API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentResult(BaseModel):
    """Single document result."""
    content: str
    metadata: Dict[str, Any]
    relevance_score: float


class RetrieveResponse(BaseModel):
    """Document retrieval response."""
    documents: List[DocumentResult]
    query_processed: str
    search_type_used: str
    total_found: int
    processing_time_ms: int


class MultiQueryRelevanceInfo(BaseModel):
    """Multi-query relevance information."""
    best_score: float
    threshold: float
    is_relevant: bool
    unique_documents: int


class MultiQueryRetrieveResponse(BaseModel):
    """Multi-query retrieval response."""
    documents: List[DocumentResult]
    generated_queries: List[str]
    relevance_info: MultiQueryRelevanceInfo
    processing_time_ms: int


class IngestResponse(BaseModel):
    """File ingest response."""
    status: str
    file_name: str
    chunks_created: int
    processing_time_ms: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutoIngestResponse(BaseModel):
    """Auto-ingest pipeline response."""
    status: str
    flow_run_id: Optional[str] = None
    files_discovered: int
    duplicates_skipped: int
    files_ingested: int
    chunks_created: int
    was_archive: bool = False
    extracted_path: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    processing_time_ms: int


class IncrementalResponse(BaseModel):
    """Incremental update response."""
    status: str
    new_files: int
    modified_files: int = 0
    chunks_created: int
    duplicates_skipped: int
    processing_time_ms: int


class PipelineStats(BaseModel):
    """Pipeline statistics response."""
    runs: int
    total_files_processed: int
    total_chunks_created: int
    duplicates_skipped: int
    errors: int
    known_documents: int
    vector_store_count: int
    last_run: Optional[datetime] = None
    avg_processing_time_ms: Optional[int] = None


class ClearCacheResponse(BaseModel):
    """Clear cache response."""
    status: str
    message: str
    documents_cleared: int


class CollectionInfo(BaseModel):
    """Vector store collection info."""
    collection_name: str
    document_count: int
    embedding_dimension: int
    embedding_model: str
    distance_metric: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    components: Dict[str, str]
    uptime_seconds: int


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    error_code: str


class DocumentListItem(BaseModel):
    """Single document in list response."""
    id: str
    content: str
    metadata: Dict[str, Any]
    source: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Document list response."""
    documents: List[DocumentListItem]
    total: int
    page: int
    limit: int
