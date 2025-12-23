"""API endpoints for test dataset management."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..storage import storage
from ..models import (
    TestDatasetCreate,
    TestDatasetUpdate,
    TestDataset,
    DatasetListResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/test-datasets", tags=["datasets"])


@router.post("", response_model=dict, status_code=201)
def create_dataset(dataset: TestDatasetCreate):
    """Create a new test dataset.

    Args:
        dataset: Dataset creation request with queries and expected documents

    Returns:
        Dict with dataset_id and created_at timestamp
    """
    try:
        dataset_id = storage.create_dataset(dataset)
        created_dataset = storage.get_dataset(dataset_id)

        return {
            "dataset_id": dataset_id,
            "created_at": created_dataset.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    skip: int = Query(0, ge=0, description="Number of datasets to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum datasets to return"),
):
    """List all test datasets with pagination.

    Args:
        skip: Number of datasets to skip (pagination offset)
        limit: Maximum number of datasets to return

    Returns:
        List of dataset summaries with total count
    """
    try:
        datasets = storage.list_datasets(skip=skip, limit=limit)

        # Get total count from index
        total = len(storage.list_datasets(skip=0, limit=10000))  # TODO: optimize

        return DatasetListResponse(datasets=datasets, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}", response_model=TestDataset)
def get_dataset(dataset_id: str):
    """Retrieve a specific test dataset by ID.

    Args:
        dataset_id: Dataset UUID

    Returns:
        Complete dataset with all queries and expected documents
    """
    dataset = storage.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return dataset


@router.put("/{dataset_id}", response_model=dict)
def update_dataset(dataset_id: str, updates: TestDatasetUpdate):
    """Update an existing test dataset.

    Args:
        dataset_id: Dataset UUID
        updates: Fields to update (name, description, queries)

    Returns:
        Dict with success message and updated_at timestamp
    """
    success = storage.update_dataset(dataset_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")

    updated_dataset = storage.get_dataset(dataset_id)

    return {
        "message": "Dataset updated successfully",
        "updated_at": updated_dataset.updated_at,
    }


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str):
    """Delete a test dataset.

    Args:
        dataset_id: Dataset UUID

    Returns:
        204 No Content on success
    """
    success = storage.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
