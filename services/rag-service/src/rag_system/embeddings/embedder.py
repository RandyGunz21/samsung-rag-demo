"""
Embedding generator using Ollama embeddings.

Provides embeddings for document chunks using Ollama's embedding models.
"""

from typing import List
from langchain_ollama import OllamaEmbeddings

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text using Ollama embeddings."""

    def __init__(
        self,
        model_name: str = "qwen3-embedding:8b",
        base_url: str = "http://localhost:11434",
        bearer_token: str = None,
    ):
        """
        Initialize embedding generator using Ollama.

        Args:
            model_name: Ollama embedding model name (e.g., 'qwen3-embedding:8b')
            base_url: Ollama API base URL (e.g., 'http://localhost:11434')
            bearer_token: Bearer token for authentication (required for cloudflare tunnels)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.bearer_token = bearer_token

        logger.info(f"Initializing Ollama embeddings model: {model_name}")
        logger.info(f"Connecting to Ollama at: {base_url}")

        # Prepare client kwargs for authentication
        client_kwargs = {}
        if bearer_token:
            client_kwargs["headers"] = {
                "Authorization": f"Bearer {bearer_token}"
            }
            logger.info("Bearer token authentication configured")

        # Initialize Ollama embeddings
        self.embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=base_url,
            client_kwargs=client_kwargs if client_kwargs else None,
        )

        logger.info(f"Ollama embeddings model loaded successfully")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        logger.debug(f"Generating embeddings for {len(texts)} documents")
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a query.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        logger.debug(f"Generating embedding for query: {text[:50]}...")
        return self.embeddings.embed_query(text)

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension
        """
        # Generate a test embedding to determine dimension
        test_embedding = self.embed_query("test")
        return len(test_embedding)
