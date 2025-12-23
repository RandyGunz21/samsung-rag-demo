"""Evaluation engine that orchestrates RAG quality testing."""

import httpx
from typing import List, Dict, Optional
from datetime import datetime

from ..config import settings
from ..models import TestDataset, TestQuery, PerQueryMetrics, AggregateMetrics, MetricsAtK
from .metrics import compute_all_metrics, aggregate_metrics


class EvaluationEngine:
    """Orchestrates evaluation of RAG system against test datasets."""

    def __init__(self, rag_service_url: Optional[str] = None):
        """Initialize evaluation engine.

        Args:
            rag_service_url: URL of RAG service (default: from settings)
        """
        self.rag_service_url = rag_service_url or settings.rag_service_url
        self.timeout = settings.rag_service_timeout

    def evaluate_dataset(
        self,
        dataset: TestDataset,
        retrieval_method: str,
        k_values: List[int],
        progress_callback: Optional[callable] = None,
    ) -> tuple[AggregateMetrics, List[PerQueryMetrics]]:
        """Evaluate RAG system on a test dataset.

        Args:
            dataset: Test dataset with queries and expected documents
            retrieval_method: "basic", "multi-query", or "hybrid"
            k_values: List of k values for metrics@k
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            Tuple of (aggregate_metrics, per_query_metrics)

        Raises:
            httpx.HTTPError: If RAG service calls fail
            ValueError: If invalid retrieval method
        """
        total_queries = len(dataset.queries)
        per_query_results = []
        all_metrics = []

        for i, query_data in enumerate(dataset.queries):
            # Call RAG service to retrieve documents
            retrieved_docs = self._retrieve_documents(
                query_data.query,
                retrieval_method,
                max_k=max(k_values),
            )

            # Build expected docs dict: {doc_id: relevance}
            expected_docs = {
                doc.doc_id: doc.relevance
                for doc in query_data.expected_docs
            }

            # Compute metrics for this query
            query_metrics = compute_all_metrics(
                retrieved_docs=retrieved_docs,
                expected_docs=expected_docs,
                k_values=k_values,
            )

            # Store per-query results
            per_query_results.append(
                PerQueryMetrics(
                    query=query_data.query,
                    ndcg=query_metrics["ndcg"],
                    map=query_metrics["map"],
                    mrr=query_metrics["mrr"],
                    retrieved_docs=retrieved_docs,
                    expected_docs=list(expected_docs.keys()),
                )
            )

            # Store for aggregation
            all_metrics.append(query_metrics)

            # Report progress
            if progress_callback:
                progress_callback(i + 1, total_queries)

        # Aggregate metrics across all queries
        aggregated = aggregate_metrics(all_metrics)

        aggregate_metrics = AggregateMetrics(
            ndcg=MetricsAtK(values=aggregated["ndcg"]),
            map=MetricsAtK(values=aggregated["map"]),
            mrr=MetricsAtK(values=aggregated["mrr"]),
            total_queries=total_queries,
        )

        return aggregate_metrics, per_query_results

    def _retrieve_documents(
        self,
        query: str,
        retrieval_method: str,
        max_k: int,
    ) -> List[str]:
        """Call RAG service to retrieve documents.

        Args:
            query: Query text
            retrieval_method: "basic", "multi-query", or "hybrid"
            max_k: Maximum number of documents to retrieve

        Returns:
            Ordered list of retrieved document IDs

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If invalid retrieval method
        """
        # Map retrieval method to endpoint
        endpoint_map = {
            "basic": "/retrieve",
            "multi-query": "/multi-query-retrieve",
            "hybrid": "/retrieve",  # Use search_type param
        }

        if retrieval_method not in endpoint_map:
            raise ValueError(f"Invalid retrieval method: {retrieval_method}")

        endpoint = endpoint_map[retrieval_method]
        url = f"{self.rag_service_url}{endpoint}"

        # Build request payload
        payload = {
            "query": query,
            "top_k": max_k,
        }

        # Add search_type for hybrid
        if retrieval_method == "hybrid":
            payload["search_type"] = "hybrid"

        # Make HTTP request
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

        # Parse response
        data = response.json()

        # Extract document IDs from response
        # RAG Service returns: {"documents": [{"id": "...", "content": "...", "score": ...}]}
        documents = data.get("documents", [])

        return [doc.get("id", doc.get("doc_id", "")) for doc in documents if doc.get("id") or doc.get("doc_id")]

    def health_check(self) -> bool:
        """Check if RAG service is reachable.

        Returns:
            True if RAG service is healthy, False otherwise
        """
        try:
            url = f"{self.rag_service_url}/health"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                return response.status_code == 200
        except Exception:
            return False
