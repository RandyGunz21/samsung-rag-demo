"""API endpoints for evaluation jobs and results."""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from datetime import datetime
from uuid import uuid4

from ..storage import storage
from ..tasks import run_evaluation
from ..config import settings
from ..models import (
    EvaluationRequest,
    EvaluationJob,
    EvaluationResults,
    JobListResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("", response_model=dict, status_code=202)
def submit_evaluation(request: EvaluationRequest):
    """Submit a new evaluation job for async processing.

    Args:
        request: Evaluation request with dataset_id, retrieval_method, k_values

    Returns:
        Dict with job_id and status (202 Accepted)
    """
    # Validate dataset exists
    dataset = storage.get_dataset(request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Create job ID
    job_id = str(uuid4())

    # Create job metadata
    job = EvaluationJob(
        job_id=job_id,
        dataset_id=request.dataset_id,
        retrieval_method=request.retrieval_method,
        k_values=request.k_values,
        status="queued",
        progress=None,
        created_at=datetime.utcnow(),
    )

    # Save job metadata
    storage.create_job(job)

    # Submit Celery task
    rag_service_url = request.rag_service_url or settings.rag_service_url

    run_evaluation.delay(
        job_id=job_id,
        dataset_id=request.dataset_id,
        retrieval_method=request.retrieval_method,
        k_values=request.k_values,
        rag_service_url=rag_service_url,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "created_at": job.created_at,
    }


@router.get("/{job_id}", response_model=EvaluationJob)
def get_job_status(job_id: str):
    """Get the status of an evaluation job.

    Args:
        job_id: Evaluation job UUID

    Returns:
        Job metadata with current status and progress
    """
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/{job_id}/results", response_model=EvaluationResults)
def get_job_results(job_id: str):
    """Get the results of a completed evaluation job.

    Args:
        job_id: Evaluation job UUID

    Returns:
        Complete evaluation results with aggregate and per-query metrics

    Raises:
        404: Job not found
        400: Job not completed yet
    """
    # Check job exists and is completed
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet. Current status: {job.status}",
        )

    # Get results
    results = storage.get_results(job_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")

    return results


@router.get("", response_model=JobListResponse)
def list_jobs(
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum jobs to return"),
    status: str | None = Query(None, description="Filter by status"),
):
    """List all evaluation jobs with pagination.

    Args:
        skip: Number of jobs to skip (pagination offset)
        limit: Maximum number of jobs to return
        status: Optional status filter (queued, running, completed, failed)

    Returns:
        List of job summaries with total count
    """
    try:
        jobs = storage.list_jobs(skip=skip, limit=limit)

        # Filter by status if provided
        if status:
            jobs = [job for job in jobs if job.status == status]

        total = len(storage.list_jobs(skip=0, limit=10000))  # TODO: optimize

        return JobListResponse(jobs=jobs, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
