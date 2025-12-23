"""Unit tests for evaluation metrics."""

import pytest
from src.evaluation.metrics import compute_ndcg, compute_map, compute_mrr, compute_all_metrics


def test_compute_ndcg_perfect_ranking():
    """Test NDCG with perfect ranking (score should be 1.0)."""
    retrieved_docs = ["doc1", "doc2", "doc3"]
    expected_docs = {"doc1": 1.0, "doc2": 0.8, "doc3": 0.6}

    ndcg = compute_ndcg(retrieved_docs, expected_docs, k=3)

    assert ndcg == pytest.approx(1.0, rel=0.01)


def test_compute_ndcg_reversed_ranking():
    """Test NDCG with reversed ranking (score should be lower)."""
    retrieved_docs = ["doc3", "doc2", "doc1"]  # Reversed
    expected_docs = {"doc1": 1.0, "doc2": 0.8, "doc3": 0.6}

    ndcg = compute_ndcg(retrieved_docs, expected_docs, k=3)

    # Should be less than perfect (1.0)
    assert 0.0 < ndcg < 1.0


def test_compute_ndcg_no_relevant():
    """Test NDCG when no relevant documents retrieved (score should be 0)."""
    retrieved_docs = ["doc4", "doc5", "doc6"]
    expected_docs = {"doc1": 1.0, "doc2": 0.8}

    ndcg = compute_ndcg(retrieved_docs, expected_docs, k=3)

    assert ndcg == 0.0


def test_compute_map_perfect():
    """Test MAP with perfect retrieval."""
    retrieved_docs = ["doc1", "doc2"]
    expected_docs = {"doc1": 1.0, "doc2": 1.0}

    map_score = compute_map(retrieved_docs, expected_docs, k=2)

    assert map_score == pytest.approx(1.0, rel=0.01)


def test_compute_map_partial():
    """Test MAP with partial retrieval."""
    retrieved_docs = ["doc1", "doc3", "doc2"]
    expected_docs = {"doc1": 1.0, "doc2": 1.0}  # doc3 not relevant

    map_score = compute_map(retrieved_docs, expected_docs, k=3)

    # Should be between 0 and 1
    assert 0.0 < map_score < 1.0


def test_compute_mrr_first_relevant():
    """Test MRR when first document is relevant (score should be 1.0)."""
    retrieved_docs = ["doc1", "doc2", "doc3"]
    expected_docs = {"doc1": 1.0}

    mrr = compute_mrr(retrieved_docs, expected_docs, k=3)

    assert mrr == 1.0


def test_compute_mrr_third_relevant():
    """Test MRR when third document is relevant (score should be 1/3)."""
    retrieved_docs = ["doc1", "doc2", "doc3"]
    expected_docs = {"doc3": 1.0}

    mrr = compute_mrr(retrieved_docs, expected_docs, k=3)

    assert mrr == pytest.approx(1.0 / 3.0, rel=0.01)


def test_compute_mrr_no_relevant():
    """Test MRR when no relevant documents (score should be 0)."""
    retrieved_docs = ["doc1", "doc2", "doc3"]
    expected_docs = {"doc4": 1.0}

    mrr = compute_mrr(retrieved_docs, expected_docs, k=3)

    assert mrr == 0.0


def test_compute_all_metrics():
    """Test computing all metrics at once."""
    retrieved_docs = ["doc1", "doc2", "doc3"]
    expected_docs = {"doc1": 1.0, "doc2": 0.8}
    k_values = [1, 3, 5]

    results = compute_all_metrics(retrieved_docs, expected_docs, k_values)

    # Check structure
    assert "ndcg" in results
    assert "map" in results
    assert "mrr" in results

    # Check all k values present
    for k in k_values:
        assert k in results["ndcg"]
        assert k in results["map"]
        assert k in results["mrr"]

    # Check all scores are between 0 and 1
    for metric in ["ndcg", "map", "mrr"]:
        for k in k_values:
            assert 0.0 <= results[metric][k] <= 1.0


def test_empty_inputs():
    """Test metrics with empty inputs."""
    assert compute_ndcg([], {}, k=1) == 0.0
    assert compute_map([], {}, k=1) == 0.0
    assert compute_mrr([], {}, k=1) == 0.0
