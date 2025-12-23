"""Information retrieval metrics for RAG evaluation.

Implements standard IR metrics:
- NDCG@k: Normalized Discounted Cumulative Gain
- MAP@k: Mean Average Precision
- MRR@k: Mean Reciprocal Rank
"""

import numpy as np
from typing import Dict, List


def compute_ndcg(
    retrieved_docs: List[str],
    expected_docs: Dict[str, float],
    k: int
) -> float:
    """Compute Normalized Discounted Cumulative Gain at rank k.

    NDCG measures ranking quality considering both relevance and position.
    Higher scores indicate better ranking of relevant documents.

    Args:
        retrieved_docs: Ordered list of retrieved document IDs
        expected_docs: Dict mapping doc_id -> relevance score (0-1)
        k: Rank cutoff (compute NDCG@k)

    Returns:
        NDCG@k score (0-1), where 1 is perfect ranking
    """
    if not retrieved_docs or not expected_docs:
        return 0.0

    # Limit to top-k retrieved
    retrieved_at_k = retrieved_docs[:k]

    # Compute DCG@k (Discounted Cumulative Gain)
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_at_k):
        relevance = expected_docs.get(doc_id, 0.0)
        # Discount by log2(rank+1), rank starts at 1
        dcg += relevance / np.log2(i + 2)

    # Compute IDCG@k (Ideal DCG - perfect ranking)
    # Sort expected docs by relevance descending
    ideal_relevances = sorted(expected_docs.values(), reverse=True)[:k]
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevances))

    # Normalize
    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def compute_map(
    retrieved_docs: List[str],
    expected_docs: Dict[str, float],
    k: int,
    binary_threshold: float = 0.5
) -> float:
    """Compute Mean Average Precision at rank k.

    MAP@k measures precision across different recall levels.

    Args:
        retrieved_docs: Ordered list of retrieved document IDs
        expected_docs: Dict mapping doc_id -> relevance score
        k: Rank cutoff
        binary_threshold: Threshold to consider doc as relevant (default 0.5)

    Returns:
        MAP@k score (0-1)
    """
    if not retrieved_docs or not expected_docs:
        return 0.0

    # Convert to binary relevance
    relevant_set = {
        doc_id for doc_id, rel in expected_docs.items()
        if rel >= binary_threshold
    }

    if not relevant_set:
        return 0.0

    # Limit to top-k
    retrieved_at_k = retrieved_docs[:k]

    # Compute average precision
    num_relevant_found = 0
    precision_sum = 0.0

    for i, doc_id in enumerate(retrieved_at_k):
        if doc_id in relevant_set:
            num_relevant_found += 1
            # Precision at this position
            precision_at_i = num_relevant_found / (i + 1)
            precision_sum += precision_at_i

    if num_relevant_found == 0:
        return 0.0

    # Average precision
    return precision_sum / len(relevant_set)


def compute_mrr(
    retrieved_docs: List[str],
    expected_docs: Dict[str, float],
    k: int,
    binary_threshold: float = 0.5
) -> float:
    """Compute Mean Reciprocal Rank at k.

    MRR focuses on the position of the first relevant document.

    Args:
        retrieved_docs: Ordered list of retrieved document IDs
        expected_docs: Dict mapping doc_id -> relevance score
        k: Rank cutoff
        binary_threshold: Threshold to consider doc as relevant

    Returns:
        MRR@k score (0-1), or 0 if no relevant doc found in top-k
    """
    if not retrieved_docs or not expected_docs:
        return 0.0

    # Convert to binary relevance
    relevant_set = {
        doc_id for doc_id, rel in expected_docs.items()
        if rel >= binary_threshold
    }

    if not relevant_set:
        return 0.0

    # Find first relevant document in top-k
    for i, doc_id in enumerate(retrieved_docs[:k]):
        if doc_id in relevant_set:
            # Return reciprocal rank (1-indexed)
            return 1.0 / (i + 1)

    # No relevant document found in top-k
    return 0.0


def compute_all_metrics(
    retrieved_docs: List[str],
    expected_docs: Dict[str, float],
    k_values: List[int]
) -> Dict[str, Dict[int, float]]:
    """Compute all metrics (NDCG, MAP, MRR) at multiple k values.

    Args:
        retrieved_docs: Ordered list of retrieved document IDs
        expected_docs: Dict mapping doc_id -> relevance score
        k_values: List of k values to compute metrics at

    Returns:
        Dict with metrics:
        {
            "ndcg": {k1: score, k3: score, ...},
            "map": {k1: score, k3: score, ...},
            "mrr": {k1: score, k3: score, ...}
        }
    """
    results = {
        "ndcg": {},
        "map": {},
        "mrr": {},
    }

    for k in k_values:
        results["ndcg"][k] = compute_ndcg(retrieved_docs, expected_docs, k)
        results["map"][k] = compute_map(retrieved_docs, expected_docs, k)
        results["mrr"][k] = compute_mrr(retrieved_docs, expected_docs, k)

    return results


def aggregate_metrics(
    per_query_metrics: List[Dict[str, Dict[int, float]]]
) -> Dict[str, Dict[int, float]]:
    """Aggregate metrics across multiple queries by averaging.

    Args:
        per_query_metrics: List of metric dicts (one per query)

    Returns:
        Averaged metrics across all queries
    """
    if not per_query_metrics:
        return {"ndcg": {}, "map": {}, "mrr": {}}

    # Get all k values from first query
    first_query = per_query_metrics[0]
    k_values = list(first_query["ndcg"].keys())

    aggregated = {
        "ndcg": {},
        "map": {},
        "mrr": {},
    }

    # Average each metric at each k
    for metric_name in ["ndcg", "map", "mrr"]:
        for k in k_values:
            scores = [
                query_metrics[metric_name][k]
                for query_metrics in per_query_metrics
            ]
            aggregated[metric_name][k] = float(np.mean(scores))

    return aggregated
