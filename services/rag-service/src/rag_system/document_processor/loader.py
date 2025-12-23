"""
Document loader for various file formats.

Uses Docling for advanced document understanding and text extraction across all formats.
Supports PDF, text, markdown, DOCX, and image files (with OCR).
Documents are loaded as full text in Markdown format for downstream semantic chunking.
"""

import os
from pathlib import Path
from typing import List, Optional, Union
from langchain_core.documents import Document

# Docling imports for advanced document processing (REQUIRED - No fallback)
# If these imports fail, the module will fail to load immediately
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentLoader:
    """Load documents from various file formats with Docling support."""

    def __init__(
        self,
        supported_formats: Optional[List[str]] = None,
        enable_ocr: bool = False,
        max_tokens: int = 1000,
    ):
        """
        Initialize document loader with Docling (REQUIRED).

        Args:
            supported_formats: List of supported file extensions
            enable_ocr: Whether to enable OCR for image files
            max_tokens: Maximum tokens per chunk (used by downstream SemanticChunker)

        Raises:
            ImportError: If Docling dependencies are not installed (fails at module import time)

        Note:
            Documents are loaded as full text in Markdown format. Chunking is handled
            separately by SemanticChunker using Ollama embeddings (qwen3-embedding:8b).
        """
        self.supported_formats = supported_formats or ["pdf", "txt", "md", "docx"]
        self.enable_ocr = enable_ocr
        self.max_tokens = max_tokens

        logger.info(f"DocumentLoader initialized (formats: {self.supported_formats})")

        # Initialize OCR if requested
        if enable_ocr:
            try:
                import pytesseract
                from PIL import Image

                self.pytesseract = pytesseract
                self.PIL_Image = Image
                self.supported_formats.extend(["png", "jpg", "jpeg"])
                logger.info("OCR enabled for image processing")
            except ImportError:
                logger.warning(
                    "OCR dependencies not installed. Image processing disabled."
                )
                self.enable_ocr = False

    def load_document(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Load a single document.

        Args:
            file_path: Path to document file

        Returns:
            List of Document objects

        Raises:
            ValueError: If file format not supported
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = file_path.suffix.lower().lstrip(".")

        if extension not in self.supported_formats:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )

        logger.info(f"Loading document: {file_path}")

        try:
            # Use Docling for all document formats (PDF, TXT, MD, DOCX)
            if extension in ["pdf", "txt", "md", "docx"]:
                return self._load_with_docling(file_path, extension)
            elif extension in ["png", "jpg", "jpeg"] and self.enable_ocr:
                return self._load_image_with_ocr(file_path)
            else:
                raise ValueError(f"Unsupported format: {extension}")

        except Exception as e:
            logger.error(f"Error loading {file_path}: {str(e)}")
            raise

    def load_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
    ) -> List[Document]:
        """
        Load all supported documents from a directory.

        Args:
            directory_path: Path to directory
            recursive: Whether to search subdirectories

        Returns:
            List of all loaded documents
        """
        directory_path = Path(directory_path)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        logger.info(f"Loading documents from: {directory_path}")

        all_documents = []
        pattern = "**/*" if recursive else "*"

        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                extension = file_path.suffix.lower().lstrip(".")
                if extension in self.supported_formats:
                    try:
                        documents = self.load_document(file_path)
                        all_documents.extend(documents)
                        logger.info(f"Loaded {len(documents)} documents from {file_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to load {file_path}: {str(e)}")
                        continue

        logger.info(f"Total documents loaded: {len(all_documents)}")
        return all_documents

    def _load_with_docling(self, file_path: Path, file_type: str) -> List[Document]:
        """
        Unified document loading using Docling for all formats (PDF, TXT, MD, DOCX).

        Docling provides:
        - Advanced layout understanding (especially for PDFs)
        - Table structure extraction
        - Figure/image extraction
        - Heading hierarchy preservation
        - Markdown export for structured text
        - Consistent processing across all formats

        Documents are returned as full text in Markdown format for downstream
        semantic chunking by SemanticChunker.

        Args:
            file_path: Path to the document file
            file_type: File extension (pdf, txt, md, docx)

        Returns:
            List of Document objects with full text and metadata

        Raises:
            RuntimeError: If Docling is not properly initialized
            Exception: If document processing fails
        """

        try:
            logger.info(f"Loading {file_type.upper()} with Docling: {file_path}")

            # Create custom DocumentConverter with external plugins enabled
            # This allows langchain_docling plugin to be loaded
            pipeline_options = PdfPipelineOptions()
            pipeline_options.allow_external_plugins = True

            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )

            # DoclingLoader for document understanding and text extraction
            # Works for all formats: PDF, DOCX, TXT, MD
            # Returns full documents in Markdown format for downstream semantic chunking
            loader = DoclingLoader(
                file_path=str(file_path),
                export_type=ExportType.MARKDOWN,  # Returns full document without chunking
                converter=doc_converter,  # Use custom converter with plugins enabled
            )

            documents = loader.load()

            # Add metadata for document format and loader info
            for doc in documents:
                doc.metadata["source"] = str(file_path)
                doc.metadata["file_type"] = file_type
                doc.metadata["loader"] = "docling"
                doc.metadata["export_format"] = "markdown"
                # Docling metadata may also include:
                # - page numbers (for PDFs)
                # - heading information
                # - section hierarchy
                # - table and figure information

            logger.info(f"Docling loaded {len(documents)} document(s) from {file_type.upper()}")
            return documents

        except Exception as e:
            logger.error(f"Docling failed to process {file_path}: {e}")
            raise RuntimeError(
                f"Failed to process {file_type.upper()} with Docling: {e}\n\n"
                "Troubleshooting steps:\n"
                "1. Verify Docling is installed: pip install docling langchain-docling docling-core\n"
                "2. Check if file is corrupted or has access restrictions\n"
                "3. Try with a different file to isolate the issue\n"
                "4. Check logs for detailed error information"
            ) from e

    def _load_image_with_ocr(self, file_path: Path) -> List[Document]:
        """Load image file and extract text using OCR."""
        if not self.enable_ocr:
            raise ValueError("OCR not enabled")

        try:
            image = self.PIL_Image.open(file_path)
            text = self.pytesseract.image_to_string(image)

            # Create document with extracted text
            doc = Document(
                page_content=text,
                metadata={
                    "source": str(file_path),
                    "file_type": "image_ocr",
                    "original_format": file_path.suffix.lower().lstrip("."),
                },
            )

            return [doc]

        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {str(e)}")
            raise
