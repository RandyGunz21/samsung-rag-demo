"""
ChromaDB vector store for persistent document storage and retrieval.

Provides interface for storing, updating, and querying document embeddings.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain.embeddings.base import Embeddings

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore:
    """ChromaDB-based vector store for document retrieval."""

    def __init__(
        self,
        embedding_function: Embeddings,
        persist_directory: str = "./data/vector_store",
        collection_name: str = "rag_documents",
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            embedding_function: Embedding function for vectorization
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection
        """
        self.embedding_function = embedding_function
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        logger.info(f"Initializing ChromaDB at {persist_directory}")

        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_function,
            persist_directory=str(persist_directory),
        )

        logger.info(f"ChromaDB initialized: collection={collection_name}")

    @property
    def collection(self):
        """Get the underlying ChromaDB collection."""
        return self.vector_store._collection

    def add_documents(
        self,
        documents: List[Document],
        batch_size: int = 100,
    ) -> List[str]:
        """
        Add documents to vector store.

        Args:
            documents: List of documents to add
            batch_size: Batch size for processing

        Returns:
            List of document IDs
        """
        if not documents:
            logger.warning("No documents to add")
            return []

        logger.info(f"Adding {len(documents)} documents to vector store")

        # Process in batches for large document sets
        all_ids = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            ids = self.vector_store.add_documents(batch)
            all_ids.extend(ids)

            logger.info(
                f"Processed batch {i // batch_size + 1}: "
                f"{len(batch)} documents added"
            )

        logger.info(f"Total {len(all_ids)} documents added to vector store")

        return all_ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Search for similar documents.

        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of similar documents
        """
        logger.debug(f"Similarity search: query='{query[:50]}...', k={k}")

        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )

        logger.debug(f"Found {len(results)} results")

        return results

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[tuple[Document, float]]:
        """
        Search for similar documents with relevance scores.

        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of (document, score) tuples
        """
        logger.debug(f"Similarity search with scores: query='{query[:50]}...', k={k}")

        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter,
        )

        logger.debug(f"Found {len(results)} results with scores")

        return results

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """
        Search using Maximal Marginal Relevance for diverse results.

        Args:
            query: Query text
            k: Number of results to return
            fetch_k: Number of results to initially fetch
            lambda_mult: Diversity vs relevance trade-off (0=max diversity, 1=max relevance)

        Returns:
            List of diverse relevant documents
        """
        logger.debug(
            f"MMR search: query='{query[:50]}...', k={k}, "
            f"fetch_k={fetch_k}, lambda={lambda_mult}"
        )

        results = self.vector_store.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
        )

        logger.debug(f"MMR search returned {len(results)} results")

        return results

    def get_retriever(
        self,
        search_type: str = "similarity",
        search_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Get a retriever instance for use in chains.

        Args:
            search_type: Type of search ('similarity', 'mmr', 'similarity_score_threshold', 'hybrid')
            search_kwargs: Additional search parameters

        Returns:
            VectorStoreRetriever or HybridRetriever instance
        """
        search_kwargs = search_kwargs or {"k": 4}

        logger.info(f"Creating retriever: search_type={search_type}")

        if search_type == "hybrid":
            # Create hybrid retriever
            return self.get_hybrid_retriever(**search_kwargs)
        else:
            # Standard vector retriever
            return self.vector_store.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs,
            )

    def get_hybrid_retriever(
        self,
        k: int = 4,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
    ):
        """
        Get a hybrid retriever combining BM25 and vector search.

        Args:
            k: Number of documents to retrieve
            bm25_weight: Weight for BM25 keyword search (default: 0.3)
            vector_weight: Weight for vector semantic search (default: 0.7)

        Returns:
            HybridRetriever instance
        """
        from src.rag_system.retrieval.hybrid_retriever import BM25Retriever, HybridRetriever

        logger.info(f"Creating hybrid retriever (k={k}, BM25={bm25_weight}, Vector={vector_weight})")

        # Get all documents from vector store for BM25 indexing
        try:
            collection = self.vector_store._collection
            results = collection.get()

            # Convert to Document objects
            documents = []
            for i in range(len(results["ids"])):
                doc = Document(
                    page_content=results["documents"][i],
                    metadata=results["metadatas"][i] if results["metadatas"] else {}
                )
                documents.append(doc)

            logger.info(f"Loaded {len(documents)} documents for BM25 indexing")

            # Create BM25 retriever
            bm25_retriever = BM25Retriever(documents=documents, k=k)

            # Create vector retriever
            vector_retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )

            # Create hybrid retriever
            hybrid_retriever = HybridRetriever(
                bm25_retriever=bm25_retriever,
                vector_retriever=vector_retriever,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight,
                k=k,
            )

            return hybrid_retriever

        except Exception as e:
            logger.error(f"Failed to create hybrid retriever: {e}")
            logger.warning("Falling back to vector-only retriever")
            return self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )

    def delete_collection(self):
        """Delete the entire collection."""
        logger.warning(f"Deleting collection: {self.collection_name}")
        self.vector_store.delete_collection()

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.vector_store._collection
            count = collection.count()

            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": str(self.persist_directory),
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "error": str(e),
            }
