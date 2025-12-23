"""Celery tasks for async evaluation processing."""

from datetime import datetime
from typing import List

from .celery_app import celery_app
from .storage import storage
from .evaluation import EvaluationEngine
from .models import EvaluationResults


@celery_app.task(bind=True, name="src.tasks.run_evaluation")
def run_evaluation(
    self,
    job_id: str,
    dataset_id: str,
    retrieval_method: str,
    k_values: List[int],
    rag_service_url: str,
) -> dict:
    """Celery task to run evaluation asynchronously.

    Args:
        self: Task instance (bind=True)
        job_id: Evaluation job UUID
        dataset_id: Test dataset UUID
        retrieval_method: "basic", "multi-query", or "hybrid"
        k_values: List of k values for metrics@k
        rag_service_url: RAG service URL

    Returns:
        Dict with job_id and status
    """
    try:
        # Update job status to running
        storage.update_job(
            job_id,
            {
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "progress": 0.0,
            },
        )

        # Load dataset
        dataset = storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Create evaluation engine
        engine = EvaluationEngine(rag_service_url=rag_service_url)

        # Progress callback
        total_queries = len(dataset.queries)

        def update_progress(current: int, total: int):
            progress = (current / total) * 100
            storage.update_job(job_id, {"progress": progress})
            # Update Celery task state
            self.update_state(
                state="PROGRESS",
                meta={"current": current, "total": total, "progress": progress},
            )

        # Run evaluation
        start_time = datetime.utcnow()
        aggregate_metrics, per_query_metrics = engine.evaluate_dataset(
            dataset=dataset,
            retrieval_method=retrieval_method,
            k_values=k_values,
            progress_callback=update_progress,
        )
        end_time = datetime.utcnow()

        # Calculate duration
        duration_seconds = (end_time - start_time).total_seconds()

        # Build results object
        results = EvaluationResults(
            job_id=job_id,
            dataset_id=dataset_id,
            dataset_name=dataset.name,
            retrieval_method=retrieval_method,
            k_values=k_values,
            aggregate_metrics=aggregate_metrics,
            per_query_metrics=per_query_metrics,
            created_at=start_time,
            completed_at=end_time,
            duration_seconds=duration_seconds,
        )

        # Save results
        storage.save_results(results)

        # Update job status to completed
        storage.update_job(
            job_id,
            {
                "status": "completed",
                "completed_at": end_time.isoformat(),
                "progress": 100.0,
            },
        )

        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        # Update job status to failed
        storage.update_job(
            job_id,
            {
                "status": "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e),
            },
        )

        # Re-raise for Celery to handle
        raise


@celery_app.task(name="src.tasks.health_check")
def health_check_task() -> dict:
    """Simple health check task for testing Celery connectivity.

    Returns:
        Dict with status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }
