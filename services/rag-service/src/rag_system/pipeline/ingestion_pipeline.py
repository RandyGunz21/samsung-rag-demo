"""
Data ingestion pipeline for processing and storing documents.

Orchestrates document loading, chunking, embedding, and storage.
"""

from pathlib import Path
from typing import Union, List, Optional
from tqdm import tqdm

from src.rag_system.document_processor import DocumentLoader, DocumentChunker
from src.rag_system.embeddings import EmbeddingGenerator
from src.rag_system.vector_db import ChromaVectorStore
from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    """Pipeline for ingesting documents into vector store."""

    def __init__(
        self,
        document_loader: DocumentLoader,
        document_chunker: DocumentChunker,
        embedding_generator: EmbeddingGenerator,
        vector_store: ChromaVectorStore,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            document_loader: Document loader instance
            document_chunker: Document chunker instance
            embedding_generator: Embedding generator instance
            vector_store: Vector store instance
        """
        self.document_loader = document_loader
        self.document_chunker = document_chunker
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store

        logger.info("Ingestion pipeline initialized")

    def ingest_file(self, file_path: Union[str, Path]) -> dict:
        """
        Ingest a single file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Ingesting file: {file_path}")

        try:
            # Load document with Docling (full text extraction)
            documents = self.document_loader.load_document(file_path)
            logger.info(f"Loaded {len(documents)} documents from {file_path}")

            # Check if documents are pre-chunked (legacy support)
            pre_chunked = all(doc.metadata.get("pre_chunked", False) for doc in documents)

            if pre_chunked:
                # Legacy: Documents are already chunked - use as-is
                chunks = documents
                logger.info(f"Using {len(chunks)} pre-chunked documents (skipping re-chunking)")
            else:
                # Standard workflow: Chunk documents using SemanticChunker
                chunks = self.document_chunker.chunk_documents(documents)
                logger.info(f"Created {len(chunks)} semantic chunks via SemanticChunker")

            # Add to vector store
            ids = self.vector_store.add_documents(chunks)
            logger.info(f"Added {len(ids)} chunks to vector store")

            # Collect chunk details for evaluation
            chunk_details = []
            for idx, chunk in enumerate(chunks):
                # Store full content for detailed evaluation (limited to 2000 chars for display)
                content = chunk.page_content
                display_content = content if len(content) <= 2000 else content[:2000] + "\n\n[... content truncated for display ...]"

                detail = {
                    "chunk_index": idx,
                    "content_preview": display_content,  # Full or truncated content for display
                    "content_length": len(chunk.page_content),  # Actual full length
                    "source": chunk.metadata.get("source", "Unknown"),
                    "page": chunk.metadata.get("page", "N/A"),
                    "chunking_method": chunk.metadata.get("chunking_method", "unknown"),
                    "metadata": chunk.metadata,
                }
                chunk_details.append(detail)

            # Get chunk statistics
            if pre_chunked:
                # For pre-chunked documents, calculate stats directly
                stats = {
                    "avg_chunk_length": sum(len(doc.page_content) for doc in chunks) / len(chunks) if chunks else 0,
                    "min_chunk_length": min(len(doc.page_content) for doc in chunks) if chunks else 0,
                    "max_chunk_length": max(len(doc.page_content) for doc in chunks) if chunks else 0,
                }
            else:
                stats = self.document_chunker.get_chunk_stats(chunks)

            return {
                "file": str(file_path),
                "status": "success",
                "documents_loaded": len(documents),
                "chunks_created": len(chunks),
                "chunks_stored": len(ids),
                "pre_chunked": pre_chunked,
                "chunk_details": chunk_details,  # NEW: detailed chunk information
                **stats,
            }

        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {str(e)}")
            return {
                "file": str(file_path),
                "status": "failed",
                "error": str(e),
            }

    def ingest_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        show_progress: bool = True,
    ) -> dict:
        """
        Ingest all documents from a directory.

        Args:
            directory_path: Path to directory
            recursive: Whether to process subdirectories
            show_progress: Whether to show progress bar

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Ingesting directory: {directory_path}")

        directory_path = Path(directory_path)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        # Find all supported files
        pattern = "**/*" if recursive else "*"
        all_files = []

        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                extension = file_path.suffix.lower().lstrip(".")
                if extension in self.document_loader.supported_formats:
                    all_files.append(file_path)

        logger.info(f"Found {len(all_files)} files to process")

        # Process files
        results = []
        total_chunks = 0
        failed_files = 0

        iterator = tqdm(all_files, desc="Ingesting files") if show_progress else all_files

        for file_path in iterator:
            result = self.ingest_file(file_path)
            results.append(result)

            if result["status"] == "success":
                total_chunks += result.get("chunks_stored", 0)
            else:
                failed_files += 1

        # Summary statistics
        summary = {
            "directory": str(directory_path),
            "total_files": len(all_files),
            "successful_files": len(all_files) - failed_files,
            "failed_files": failed_files,
            "total_chunks_stored": total_chunks,
            "results": results,
        }

        logger.info(
            f"Ingestion complete: {summary['successful_files']}/{summary['total_files']} "
            f"files processed, {total_chunks} chunks stored"
        )

        return summary

    def ingest_batch(
        self,
        file_paths: List[Union[str, Path]],
        show_progress: bool = True,
    ) -> dict:
        """
        Ingest a batch of files.

        Args:
            file_paths: List of file paths
            show_progress: Whether to show progress bar

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Ingesting batch of {len(file_paths)} files")

        results = []
        total_chunks = 0
        failed_files = 0

        iterator = tqdm(file_paths, desc="Ingesting files") if show_progress else file_paths

        for file_path in iterator:
            result = self.ingest_file(file_path)
            results.append(result)

            if result["status"] == "success":
                total_chunks += result.get("chunks_stored", 0)
            else:
                failed_files += 1

        summary = {
            "total_files": len(file_paths),
            "successful_files": len(file_paths) - failed_files,
            "failed_files": failed_files,
            "total_chunks_stored": total_chunks,
            "results": results,
        }

        logger.info(
            f"Batch ingestion complete: {summary['successful_files']}/{summary['total_files']} "
            f"files processed, {total_chunks} chunks stored"
        )

        return summary
