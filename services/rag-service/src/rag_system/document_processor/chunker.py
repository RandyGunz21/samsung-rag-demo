"""
Document chunker for splitting documents into smaller chunks.

Implements semantic chunking strategy using embeddings for retrieval accuracy.
Uses LangChain's SemanticChunker with Ollama embeddings for semantic similarity-based splitting.
"""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    """Split documents into semantically meaningful chunks."""

    def __init__(
        self,
        embedding_model: str = "qwen3-embedding:8b",
        base_url: str = "http://localhost:11434",
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: Optional[float] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_chunk_size: int = 1500,  # NEW: Maximum chunk size for post-processing
        separators: Optional[List[str]] = None,
        add_start_index: bool = True,
    ):
        """
        Initialize semantic document chunker.

        Args:
            embedding_model: Ollama embedding model to use (default: qwen3-embedding:8b)
            base_url: Ollama API base URL (default: http://localhost:11434)
            breakpoint_threshold_type: Method for determining split points
                - "percentile" (default): Split at differences greater than X percentile
                - "standard_deviation": Split at differences greater than X std devs
                - "interquartile": Use interquartile distance for splits
            breakpoint_threshold_amount: Optional custom threshold value (lower = more chunks)
            chunk_size: Target size for recursive splitting of oversized chunks
            chunk_overlap: Character overlap for recursive splitting (preserves context)
            max_chunk_size: Maximum characters per chunk before recursive splitting (default: 1500)
            separators: Separators for recursive text splitting
            add_start_index: Whether to add start index metadata to chunks
        """
        self.embedding_model = embedding_model
        self.base_url = base_url
        self.breakpoint_threshold_type = breakpoint_threshold_type
        self.breakpoint_threshold_amount = breakpoint_threshold_amount
        self.add_start_index = add_start_index

        # Chunk size constraints for post-processing
        self.max_chunk_size = max_chunk_size
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

        # Initialize Ollama embeddings
        try:
            logger.info(f"Initializing OllamaEmbeddings with model: {embedding_model}")

            self.embeddings = OllamaEmbeddings(
                model=embedding_model,
                base_url=base_url,
            )

            # Initialize SemanticChunker
            chunker_kwargs = {"breakpoint_threshold_type": breakpoint_threshold_type}
            if breakpoint_threshold_amount is not None:
                chunker_kwargs["breakpoint_threshold_amount"] = breakpoint_threshold_amount

            self.text_splitter = SemanticChunker(
                self.embeddings,
                **chunker_kwargs
            )

            logger.info(
                f"SemanticChunker initialized with {embedding_model} embeddings "
                f"(threshold_type={breakpoint_threshold_type})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize SemanticChunker: {e}")
            raise RuntimeError(
                f"Failed to initialize semantic chunking with {embedding_model}: {e}\n"
                "Ensure Ollama is running and the model is available."
            ) from e

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into semantic chunks using embeddings.

        Args:
            documents: List of documents to chunk

        Returns:
            List of semantically chunked documents with metadata
        """
        logger.info(f"Chunking {len(documents)} documents using semantic similarity")

        # Step 1: Initial semantic chunking
        all_chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Initial semantic chunking created {len(all_chunks)} chunks")

        # Step 2: Post-process to enforce maximum chunk size
        final_chunks = []
        split_count = 0

        for chunk in all_chunks:
            if len(chunk.page_content) > self.max_chunk_size:
                # Split oversized chunks using recursive character splitting
                from langchain_text_splitters import RecursiveCharacterTextSplitter

                recursive_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separators=self.separators,
                    length_function=len,
                )

                # Split the oversized chunk
                sub_chunks = recursive_splitter.create_documents(
                    [chunk.page_content],
                    metadatas=[chunk.metadata.copy()]
                )

                final_chunks.extend(sub_chunks)
                split_count += 1
                logger.info(
                    f"Split oversized chunk ({len(chunk.page_content)} chars) "
                    f"into {len(sub_chunks)} sub-chunks"
                )
            else:
                final_chunks.append(chunk)

        if split_count > 0:
            logger.info(f"Split {split_count} oversized chunks into smaller pieces")

        # Add chunk metadata
        for idx, chunk in enumerate(final_chunks):
            chunk.metadata["chunk_id"] = idx
            chunk.metadata["chunk_size"] = len(chunk.page_content)
            chunk.metadata["chunking_method"] = "semantic_hybrid" if split_count > 0 else "semantic"

        logger.info(
            f"Created {len(final_chunks)} chunks from {len(documents)} documents "
            f"(avg size: {sum(len(c.page_content) for c in final_chunks) / len(final_chunks):.0f} chars)"
        )

        return final_chunks

    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        Split raw text into semantic chunks.

        Args:
            text: Text to chunk
            metadata: Optional metadata for chunks

        Returns:
            List of Document chunks with semantic boundaries
        """
        # SemanticChunker uses create_documents for raw text
        base_metadata = metadata.copy() if metadata else {}
        documents = self.text_splitter.create_documents([text], [base_metadata])

        # Add chunk metadata
        for idx, doc in enumerate(documents):
            doc.metadata["chunk_id"] = idx
            doc.metadata["chunk_size"] = len(doc.page_content)
            doc.metadata["chunking_method"] = "semantic"

        return documents

    def get_chunk_stats(self, chunks: List[Document]) -> dict:
        """
        Get statistics about chunks.

        Args:
            chunks: List of chunked documents

        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
            }

        chunk_sizes = [len(chunk.page_content) for chunk in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
        }
