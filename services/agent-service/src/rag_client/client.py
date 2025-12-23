"""
RAG Service Client.

HTTP client for communicating with the RAG Service API.
"""

import os
from typing import Any, Dict, List, Optional

import httpx


class RAGServiceError(Exception):
    """Exception raised when RAG Service communication fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class RAGClient:
    """
    Async HTTP client for RAG Service API.

    Handles all communication with the RAG Service including:
    - Document retrieval
    - Multi-query retrieval
    - Pipeline statistics
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize RAG Client.

        Args:
            base_url: RAG Service base URL (default from env or localhost)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv(
            "RAG_SERVICE_URL",
            "http://localhost:8000/api/v1"
        )
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        search_type: str = "similarity",
        similarity_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            top_k: Number of results
            search_type: similarity, mmr, or hybrid
            similarity_threshold: Minimum relevance score
            filters: Optional metadata filters

        Returns:
            Dictionary with documents and metadata

        Raises:
            RAGServiceError: If request fails
        """
        client = await self._get_client()

        try:
            response = await client.post(
                "/retrieve",
                json={
                    "query": query,
                    "top_k": top_k,
                    "search_type": search_type,
                    "similarity_threshold": similarity_threshold,
                    "filters": filters or {},
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RAGServiceError(
                f"RAG Service error: {e.response.text}",
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            raise RAGServiceError(f"RAG Service unavailable: {str(e)}")

    async def multi_query_retrieve(
        self,
        query: str,
        num_queries: int = 3,
        top_k: int = 4,
        similarity_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Retrieve with automatic query expansion.

        Args:
            query: Original query
            num_queries: Number of query variations
            top_k: Results per query
            similarity_threshold: Minimum relevance score

        Returns:
            Dictionary with documents, generated queries, and relevance info
        """
        client = await self._get_client()

        try:
            response = await client.post(
                "/multi-query-retrieve",
                json={
                    "query": query,
                    "num_queries": num_queries,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RAGServiceError(
                f"RAG Service error: {e.response.text}",
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            raise RAGServiceError(f"RAG Service unavailable: {str(e)}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        client = await self._get_client()

        try:
            response = await client.get("/stats")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RAGServiceError(
                f"RAG Service error: {e.response.text}",
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            raise RAGServiceError(f"RAG Service unavailable: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Check RAG service health."""
        client = await self._get_client()

        try:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RAGServiceError(
                f"RAG Service error: {e.response.text}",
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            raise RAGServiceError(f"RAG Service unavailable: {str(e)}")


# Singleton instance
_rag_client: Optional[RAGClient] = None


def get_rag_client() -> RAGClient:
    """Get or create RAG client singleton."""
    global _rag_client
    if _rag_client is None:
        _rag_client = RAGClient()
    return _rag_client


async def close_rag_client():
    """Close the RAG client."""
    global _rag_client
    if _rag_client:
        await _rag_client.close()
        _rag_client = None
