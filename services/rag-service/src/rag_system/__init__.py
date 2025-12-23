"""
RAG System - Retrieval-Augmented Generation for Question Answering

A modular RAG system built with LangChain for accurate document-based question answering.
"""

__version__ = "0.1.0"
__author__ = "RAG Development Team"

from src.rag_system.config_loader import load_config, get_config

__all__ = ["load_config", "get_config", "__version__"]
