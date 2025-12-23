"""
Hybrid Retriever combining BM25 (keyword) and Vector (semantic) search.

Implements ensemble retrieval for improved accuracy on entity-based queries.
"""

from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from rank_bm25 import BM25Okapi

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class BM25Retriever(BaseRetriever):
    """BM25-based keyword retriever for document search."""

    documents: List[Document]
    bm25: BM25Okapi
    k: int = 4

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, documents: List[Document], k: int = 4):
        """
        Initialize BM25 retriever.

        Args:
            documents: List of documents to search
            k: Number of documents to retrieve (default: 4)
        """
        # Tokenize documents for BM25
        tokenized_docs = [doc.page_content.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)

        super().__init__(documents=documents, bm25=bm25, k=k)
        logger.info(f"BM25Retriever initialized with {len(documents)} documents")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """
        Retrieve documents using BM25 keyword matching.

        Args:
            query: Search query
            run_manager: Callback manager

        Returns:
            List of relevant documents
        """
        # Tokenize query
        tokenized_query = query.lower().split()

        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k document indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: self.k]

        # Return top documents
        results = [self.documents[i] for i in top_indices]
        logger.debug(f"BM25 retrieved {len(results)} documents for query: {query[:50]}...")
        return results


class HybridRetriever(BaseRetriever):
    """
    Ensemble retriever combining BM25 and vector search.

    Merges results from keyword-based BM25 and semantic vector search
    using weighted scoring for improved accuracy.
    """

    bm25_retriever: BM25Retriever
    vector_retriever: BaseRetriever
    bm25_weight: float = 0.3
    vector_weight: float = 0.7
    k: int = 4

    class Config:
        arbitrary_types_allowed = True

    @property
    def vectorstore(self):
        """Expose underlying vectorstore for compatibility with RAGChain."""
        return self.vector_retriever.vectorstore

    @property
    def search_kwargs(self):
        """Expose search kwargs for compatibility with RAGChain."""
        return {"k": self.k}

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: BaseRetriever,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        k: int = 4,
    ):
        """
        Initialize hybrid retriever.

        Args:
            bm25_retriever: BM25 keyword retriever
            vector_retriever: Vector semantic retriever
            bm25_weight: Weight for BM25 scores (default: 0.3)
            vector_weight: Weight for vector scores (default: 0.7)
            k: Number of documents to retrieve (default: 4)
        """
        super().__init__(
            bm25_retriever=bm25_retriever,
            vector_retriever=vector_retriever,
            bm25_weight=bm25_weight,
            vector_weight=vector_weight,
            k=k,
        )

        # Normalize weights
        total_weight = bm25_weight + vector_weight
        self.bm25_weight = bm25_weight / total_weight
        self.vector_weight = vector_weight / total_weight

        logger.info(
            f"HybridRetriever initialized (BM25: {self.bm25_weight:.2f}, "
            f"Vector: {self.vector_weight:.2f}, k={k})"
        )

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """
        Retrieve documents using hybrid search (BM25 + Vector).

        Args:
            query: Search query
            run_manager: Callback manager

        Returns:
            List of relevant documents with weighted scores
        """
        # Get results from both retrievers
        bm25_docs = self.bm25_retriever.get_relevant_documents(query)
        vector_docs = self.vector_retriever.get_relevant_documents(query)

        logger.info(f"BM25: {len(bm25_docs)} docs, Vector: {len(vector_docs)} docs")

        # Merge and deduplicate results
        doc_map = {}

        # Add BM25 results with weighted scores
        for idx, doc in enumerate(bm25_docs):
            # BM25 score: higher rank = higher score
            score = self.bm25_weight * (1.0 - idx / len(bm25_docs))
            doc_id = doc.page_content[:100]  # Use content prefix as ID

            if doc_id not in doc_map:
                doc_map[doc_id] = {"doc": doc, "score": score}
            else:
                doc_map[doc_id]["score"] += score

        # Add vector results with weighted scores
        for idx, doc in enumerate(vector_docs):
            # Vector score: higher rank = higher score
            score = self.vector_weight * (1.0 - idx / len(vector_docs))
            doc_id = doc.page_content[:100]

            if doc_id not in doc_map:
                doc_map[doc_id] = {"doc": doc, "score": score}
            else:
                doc_map[doc_id]["score"] += score

        # Sort by combined score and return top-k
        sorted_docs = sorted(doc_map.values(), key=lambda x: x["score"], reverse=True)
        results = [item["doc"] for item in sorted_docs[: self.k]]

        logger.info(f"Hybrid search returned {len(results)} documents")
        return results
