"""RAG Service API Schemas."""

from .requests import (
    RetrieveRequest,
    MultiQueryRetrieveRequest,
    AutoIngestRequest,
    IncrementalRequest,
)
from .responses import (
    DocumentResult,
    RetrieveResponse,
    MultiQueryRelevanceInfo,
    MultiQueryRetrieveResponse,
    IngestResponse,
    AutoIngestResponse,
    IncrementalResponse,
    PipelineStats,
    ClearCacheResponse,
    CollectionInfo,
    HealthResponse,
    ErrorResponse,
    DocumentListItem,
    DocumentListResponse,
)

__all__ = [
    # Requests
    "RetrieveRequest",
    "MultiQueryRetrieveRequest",
    "AutoIngestRequest",
    "IncrementalRequest",
    # Responses
    "DocumentResult",
    "RetrieveResponse",
    "MultiQueryRelevanceInfo",
    "MultiQueryRetrieveResponse",
    "IngestResponse",
    "AutoIngestResponse",
    "IncrementalResponse",
    "PipelineStats",
    "ClearCacheResponse",
    "CollectionInfo",
    "HealthResponse",
    "ErrorResponse",
    "DocumentListItem",
    "DocumentListResponse",
]
