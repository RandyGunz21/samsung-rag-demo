"""
RAG Service Core - Wraps existing RAG system components.

This module provides access to the core RAG functionality.
The rag_system package is included locally in this service.
"""

# Re-export core components from local rag_system package
from src.rag_system.config_loader import load_config
from src.rag_system.document_processor import DocumentLoader, DocumentChunker
from src.rag_system.embeddings import EmbeddingGenerator
from src.rag_system.vector_db import ChromaVectorStore
from src.rag_system.pipeline import IngestionPipeline, PipelineOrchestrator, create_orchestrator
from src.rag_system.retrieval import RAGChain, SmartRAGAgent
from src.rag_system.retrieval.multi_query_retriever import MultiQueryRetriever
from src.rag_system.retrieval.hybrid_retriever import HybridRetriever, BM25Retriever

__all__ = [
    "load_config",
    "DocumentLoader",
    "DocumentChunker",
    "EmbeddingGenerator",
    "ChromaVectorStore",
    "IngestionPipeline",
    "PipelineOrchestrator",
    "create_orchestrator",
    "RAGChain",
    "SmartRAGAgent",
    "MultiQueryRetriever",
    "HybridRetriever",
    "BM25Retriever",
]
