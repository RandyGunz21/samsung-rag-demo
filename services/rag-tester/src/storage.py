"""File-based storage layer for RAG-tester service.

This module provides a simple, lightweight storage solution using JSON files
instead of a traditional database. Perfect for MVP and small-scale deployments.
"""

import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import Optional
from threading import Lock

from .config import settings
from .models import (
    TestDataset,
    TestDatasetCreate,
    TestDatasetUpdate,
    TestDatasetSummary,
    EvaluationJob,
    EvaluationResults,
)


class FileStorage:
    """File-based storage manager for datasets and evaluation results."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize storage with data directory.

        Args:
            data_dir: Root data directory (default: from settings)
        """
        self.data_dir = data_dir or settings.data_dir
        self.datasets_dir = self.data_dir / "test-datasets"
        self.results_dir = self.data_dir / "evaluation-results"
        self.jobs_dir = self.data_dir / "jobs"

        # Thread-safe file operations
        self._lock = Lock()

        # Ensure directories exist
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create data directories if they don't exist."""
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path) -> dict:
        """Thread-safe JSON file read."""
        with self._lock:
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            return json.loads(path.read_text())

    def _write_json(self, path: Path, data: dict):
        """Thread-safe JSON file write."""
        with self._lock:
            path.write_text(json.dumps(data, indent=2, default=str))

    # ==================== Dataset Operations ====================

    def create_dataset(self, dataset: TestDatasetCreate) -> str:
        """Create a new test dataset.

        Args:
            dataset: Dataset creation request

        Returns:
            Dataset ID (UUID)
        """
        dataset_id = str(uuid4())
        now = datetime.utcnow()

        # Build dataset object
        dataset_data = {
            "id": dataset_id,
            "name": dataset.name,
            "description": dataset.description,
            "queries": [q.model_dump() for q in dataset.queries],
            "created_at": now.isoformat(),
            "updated_at": None,
            "query_count": len(dataset.queries),
        }

        # Write dataset file
        dataset_path = self.datasets_dir / f"{dataset_id}.json"
        self._write_json(dataset_path, dataset_data)

        # Update index
        self._update_datasets_index()

        return dataset_id

    def get_dataset(self, dataset_id: str) -> Optional[TestDataset]:
        """Retrieve a dataset by ID.

        Args:
            dataset_id: Dataset UUID

        Returns:
            TestDataset or None if not found
        """
        dataset_path = self.datasets_dir / f"{dataset_id}.json"
        if not dataset_path.exists():
            return None

        data = self._read_json(dataset_path)
        return TestDataset(**data)

    def list_datasets(self, skip: int = 0, limit: int = 100) -> list[TestDatasetSummary]:
        """List all datasets with pagination.

        Args:
            skip: Number of datasets to skip
            limit: Maximum number of datasets to return

        Returns:
            List of dataset summaries
        """
        index_path = self.datasets_dir / "index.json"
        if not index_path.exists():
            return []

        index_data = self._read_json(index_path)
        datasets = index_data.get("datasets", [])

        # Apply pagination
        paginated = datasets[skip : skip + limit]

        return [TestDatasetSummary(**d) for d in paginated]

    def update_dataset(self, dataset_id: str, updates: TestDatasetUpdate) -> bool:
        """Update an existing dataset.

        Args:
            dataset_id: Dataset UUID
            updates: Fields to update

        Returns:
            True if updated, False if not found
        """
        dataset_path = self.datasets_dir / f"{dataset_id}.json"
        if not dataset_path.exists():
            return False

        # Read current data
        data = self._read_json(dataset_path)

        # Apply updates
        if updates.name is not None:
            data["name"] = updates.name
        if updates.description is not None:
            data["description"] = updates.description
        if updates.queries is not None:
            data["queries"] = [q.model_dump() for q in updates.queries]
            data["query_count"] = len(updates.queries)

        data["updated_at"] = datetime.utcnow().isoformat()

        # Write back
        self._write_json(dataset_path, data)

        # Update index
        self._update_datasets_index()

        return True

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset.

        Args:
            dataset_id: Dataset UUID

        Returns:
            True if deleted, False if not found
        """
        dataset_path = self.datasets_dir / f"{dataset_id}.json"
        if not dataset_path.exists():
            return False

        with self._lock:
            dataset_path.unlink()

        # Update index
        self._update_datasets_index()

        return True

    def _update_datasets_index(self):
        """Rebuild the datasets index file."""
        datasets = []

        for path in self.datasets_dir.glob("*.json"):
            if path.name == "index.json":
                continue

            try:
                data = self._read_json(path)
                datasets.append(
                    {
                        "id": data["id"],
                        "name": data["name"],
                        "description": data.get("description"),
                        "query_count": data["query_count"],
                        "created_at": data["created_at"],
                    }
                )
            except Exception:
                # Skip corrupted files
                continue

        # Sort by created_at descending (newest first)
        datasets.sort(key=lambda x: x["created_at"], reverse=True)

        # Write index
        index_path = self.datasets_dir / "index.json"
        self._write_json(index_path, {"datasets": datasets, "total": len(datasets)})

    # ==================== Evaluation Job Operations ====================

    def create_job(self, job: EvaluationJob) -> str:
        """Create a new evaluation job entry.

        Args:
            job: Job metadata

        Returns:
            Job ID
        """
        job_path = self.jobs_dir / f"{job.job_id}.json"
        self._write_json(job_path, job.model_dump(mode="json"))
        self._update_jobs_index()
        return job.job_id

    def get_job(self, job_id: str) -> Optional[EvaluationJob]:
        """Retrieve a job by ID.

        Args:
            job_id: Job UUID

        Returns:
            EvaluationJob or None if not found
        """
        job_path = self.jobs_dir / f"{job_id}.json"
        if not job_path.exists():
            return None

        data = self._read_json(job_path)
        return EvaluationJob(**data)

    def update_job(self, job_id: str, updates: dict) -> bool:
        """Update job metadata.

        Args:
            job_id: Job UUID
            updates: Fields to update

        Returns:
            True if updated, False if not found
        """
        job_path = self.jobs_dir / f"{job_id}.json"
        if not job_path.exists():
            return False

        data = self._read_json(job_path)
        data.update(updates)
        self._write_json(job_path, data)
        self._update_jobs_index()

        return True

    def list_jobs(self, skip: int = 0, limit: int = 100) -> list[EvaluationJob]:
        """List all evaluation jobs with pagination.

        Args:
            skip: Number of jobs to skip
            limit: Maximum number of jobs to return

        Returns:
            List of evaluation jobs
        """
        index_path = self.jobs_dir / "index.json"
        if not index_path.exists():
            return []

        index_data = self._read_json(index_path)
        jobs = index_data.get("jobs", [])

        # Apply pagination
        paginated = jobs[skip : skip + limit]

        return [EvaluationJob(**j) for j in paginated]

    def _update_jobs_index(self):
        """Rebuild the jobs index file."""
        jobs = []

        for path in self.jobs_dir.glob("*.json"):
            if path.name == "index.json":
                continue

            try:
                data = self._read_json(path)
                jobs.append(data)
            except Exception:
                continue

        # Sort by created_at descending
        jobs.sort(key=lambda x: x["created_at"], reverse=True)

        index_path = self.jobs_dir / "index.json"
        self._write_json(index_path, {"jobs": jobs, "total": len(jobs)})

    # ==================== Evaluation Results Operations ====================

    def save_results(self, results: EvaluationResults):
        """Save evaluation results.

        Args:
            results: Complete evaluation results
        """
        results_path = self.results_dir / f"{results.job_id}.json"
        self._write_json(results_path, results.model_dump(mode="json"))

    def get_results(self, job_id: str) -> Optional[EvaluationResults]:
        """Retrieve evaluation results.

        Args:
            job_id: Job UUID

        Returns:
            EvaluationResults or None if not found
        """
        results_path = self.results_dir / f"{job_id}.json"
        if not results_path.exists():
            return None

        data = self._read_json(results_path)
        return EvaluationResults(**data)


# Global storage instance
storage = FileStorage()
