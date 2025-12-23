"""Pydantic models for RAG-tester service."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime
from uuid import UUID


# ==================== Test Dataset Models ====================

class ExpectedDocument(BaseModel):
    """Expected document with relevance score."""
    doc_id: str = Field(..., description="Document ID from vector store")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")


class TestQuery(BaseModel):
    """Single test query with expected documents."""
    query: str = Field(..., min_length=1, description="Query text")
    expected_docs: list[ExpectedDocument] = Field(..., min_items=1, description="Expected relevant documents")


class TestDatasetCreate(BaseModel):
    """Request model for creating a test dataset."""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: str | None = Field(None, description="Dataset description")
    queries: list[TestQuery] = Field(..., min_items=1, description="Test queries")

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, queries: list[TestQuery]) -> list[TestQuery]:
        if len(queries) > 1000:
            raise ValueError("Maximum 1000 queries per dataset")
        return queries


class TestDatasetUpdate(BaseModel):
    """Request model for updating a test dataset."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    queries: list[TestQuery] | None = Field(None, min_items=1)


class TestDataset(BaseModel):
    """Complete test dataset with metadata."""
    id: str = Field(..., description="Dataset UUID")
    name: str
    description: str | None = None
    queries: list[TestQuery]
    created_at: datetime
    updated_at: datetime | None = None
    query_count: int = Field(..., description="Number of queries in dataset")


class TestDatasetSummary(BaseModel):
    """Summary of a test dataset (for listing)."""
    id: str
    name: str
    description: str | None = None
    query_count: int
    created_at: datetime


# ==================== Evaluation Models ====================

class EvaluationRequest(BaseModel):
    """Request to run an evaluation."""
    dataset_id: str = Field(..., description="Test dataset ID to evaluate")
    retrieval_method: Literal["basic", "multi-query", "hybrid"] = Field(
        "basic",
        description="Retrieval method to test"
    )
    k_values: list[int] = Field([1, 3, 5, 10], description="k values for metrics@k")
    rag_service_url: str | None = Field(None, description="Override RAG service URL")

    @field_validator("k_values")
    @classmethod
    def validate_k_values(cls, k_values: list[int]) -> list[int]:
        if not k_values:
            raise ValueError("At least one k value required")
        if any(k <= 0 for k in k_values):
            raise ValueError("k values must be positive integers")
        if len(k_values) > 20:
            raise ValueError("Maximum 20 k values allowed")
        return sorted(set(k_values))  # Remove duplicates and sort


class EvaluationJob(BaseModel):
    """Evaluation job metadata."""
    job_id: str = Field(..., description="Job UUID")
    dataset_id: str
    retrieval_method: str
    k_values: list[int]
    status: Literal["queued", "running", "completed", "failed"]
    progress: float | None = Field(None, ge=0.0, le=100.0, description="Progress percentage")
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = Field(None, description="Error message if failed")


class MetricsAtK(BaseModel):
    """Metrics computed at different k values."""
    values: dict[int, float] = Field(..., description="k -> metric value mapping")

    def get(self, k: int) -> float | None:
        """Get metric value for specific k."""
        return self.values.get(k)


class AggregateMetrics(BaseModel):
    """Aggregate metrics across all queries."""
    ndcg: MetricsAtK = Field(..., description="NDCG@k scores")
    map: MetricsAtK = Field(..., description="MAP@k scores")
    mrr: MetricsAtK = Field(..., description="MRR@k scores")
    total_queries: int = Field(..., description="Total number of queries evaluated")


class PerQueryMetrics(BaseModel):
    """Metrics for a single query."""
    query: str
    ndcg: dict[int, float]
    map: dict[int, float]
    mrr: dict[int, float]
    retrieved_docs: list[str] = Field(..., description="List of retrieved doc IDs")
    expected_docs: list[str] = Field(..., description="List of expected doc IDs")


class EvaluationResults(BaseModel):
    """Complete evaluation results."""
    job_id: str
    dataset_id: str
    dataset_name: str
    retrieval_method: str
    k_values: list[int]
    aggregate_metrics: AggregateMetrics
    per_query_metrics: list[PerQueryMetrics]
    created_at: datetime
    completed_at: datetime
    duration_seconds: float | None = None


# ==================== Response Models ====================

class DatasetListResponse(BaseModel):
    """Response for listing datasets."""
    datasets: list[TestDatasetSummary]
    total: int


class JobListResponse(BaseModel):
    """Response for listing evaluation jobs."""
    jobs: list[EvaluationJob]
    total: int


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None
