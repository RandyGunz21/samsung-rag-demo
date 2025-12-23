"""Unit tests for file-based storage."""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.storage import FileStorage
from src.models import TestDatasetCreate, TestDatasetUpdate, ExpectedDocument, TestQuery


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    temp_dir = tempfile.mkdtemp()
    storage = FileStorage(data_dir=Path(temp_dir))
    yield storage
    # Cleanup
    shutil.rmtree(temp_dir)


def test_create_dataset(temp_storage):
    """Test creating a dataset."""
    dataset = TestDatasetCreate(
        name="Test Dataset",
        description="A test dataset",
        queries=[
            TestQuery(
                query="What is RAG?",
                expected_docs=[
                    ExpectedDocument(doc_id="doc1", relevance=1.0),
                    ExpectedDocument(doc_id="doc2", relevance=0.8),
                ],
            )
        ],
    )

    dataset_id = temp_storage.create_dataset(dataset)

    assert dataset_id is not None
    assert len(dataset_id) > 0


def test_get_dataset(temp_storage):
    """Test retrieving a dataset."""
    dataset_create = TestDatasetCreate(
        name="Test Dataset",
        queries=[
            TestQuery(
                query="Test query",
                expected_docs=[ExpectedDocument(doc_id="doc1", relevance=1.0)],
            )
        ],
    )

    dataset_id = temp_storage.create_dataset(dataset_create)
    retrieved = temp_storage.get_dataset(dataset_id)

    assert retrieved is not None
    assert retrieved.name == "Test Dataset"
    assert len(retrieved.queries) == 1
    assert retrieved.query_count == 1


def test_get_nonexistent_dataset(temp_storage):
    """Test retrieving a dataset that doesn't exist."""
    result = temp_storage.get_dataset("nonexistent-id")
    assert result is None


def test_list_datasets(temp_storage):
    """Test listing datasets."""
    # Create multiple datasets
    for i in range(3):
        dataset = TestDatasetCreate(
            name=f"Dataset {i}",
            queries=[
                TestQuery(
                    query=f"Query {i}",
                    expected_docs=[ExpectedDocument(doc_id=f"doc{i}", relevance=1.0)],
                )
            ],
        )
        temp_storage.create_dataset(dataset)

    datasets = temp_storage.list_datasets()

    assert len(datasets) == 3


def test_update_dataset(temp_storage):
    """Test updating a dataset."""
    dataset_create = TestDatasetCreate(
        name="Original Name",
        queries=[
            TestQuery(
                query="Test query",
                expected_docs=[ExpectedDocument(doc_id="doc1", relevance=1.0)],
            )
        ],
    )

    dataset_id = temp_storage.create_dataset(dataset_create)

    # Update
    update = TestDatasetUpdate(name="Updated Name", description="New description")
    success = temp_storage.update_dataset(dataset_id, update)

    assert success is True

    # Verify
    updated = temp_storage.get_dataset(dataset_id)
    assert updated.name == "Updated Name"
    assert updated.description == "New description"


def test_delete_dataset(temp_storage):
    """Test deleting a dataset."""
    dataset_create = TestDatasetCreate(
        name="To Delete",
        queries=[
            TestQuery(
                query="Test query",
                expected_docs=[ExpectedDocument(doc_id="doc1", relevance=1.0)],
            )
        ],
    )

    dataset_id = temp_storage.create_dataset(dataset_create)

    # Delete
    success = temp_storage.delete_dataset(dataset_id)
    assert success is True

    # Verify deletion
    retrieved = temp_storage.get_dataset(dataset_id)
    assert retrieved is None


def test_delete_nonexistent_dataset(temp_storage):
    """Test deleting a dataset that doesn't exist."""
    success = temp_storage.delete_dataset("nonexistent-id")
    assert success is False
