"""
RAG Service - Request Schemas.

Pydantic models for API request validation.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    """Document retrieval request."""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=4, ge=1, le=50, description="Number of results")
    search_type: str = Field(
        default="similarity",
        pattern="^(similarity|mmr|hybrid)$",
        description="Search algorithm"
    )
    similarity_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Minimum relevance score"
    )
    filters: Dict[str, Any] = Field(default_factory=dict, description="Metadata filters")


class MultiQueryRetrieveRequest(BaseModel):
    """Multi-query retrieval request."""
    query: str = Field(..., min_length=1, description="Original query")
    num_queries: int = Field(default=3, ge=1, le=5, description="Query variations")
    top_k: int = Field(default=4, ge=1, le=50)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class AutoIngestRequest(BaseModel):
    """Auto-ingest pipeline request."""
    source_path: str = Field(..., description="Path to file, directory, or archive")
    recursive: bool = Field(default=True, description="Process subdirectories")
    skip_duplicates: bool = Field(default=True, description="Skip processed files")
    output_dir: str = Field(default="data/raw", description="Archive extraction dir")


class IncrementalRequest(BaseModel):
    """Incremental update request."""
    source_path: str = Field(..., description="Path to scan")
    recursive: bool = Field(default=True)
