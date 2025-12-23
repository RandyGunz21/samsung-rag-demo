"""
Configuration loader for RAG system.

Loads configuration from YAML file and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for RAG system."""

    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize configuration from dictionary."""
        self._config = config_dict

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def to_dict(self) -> Dict[str, Any]:
        """Return full configuration as dictionary."""
        return self._config.copy()


# Global configuration instance
_config: Optional[Config] = None


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to YAML config file. If None, uses default.

    Returns:
        Config instance with loaded configuration.
    """
    global _config

    # Load environment variables
    load_dotenv()

    # Determine config file path
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    # Load YAML configuration
    if config_path.exists():
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)
    else:
        config_dict = {}

    # Override with environment variables
    config_dict = _override_from_env(config_dict)

    _config = Config(config_dict)
    return _config


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config instance.

    Raises:
        RuntimeError: If configuration not loaded yet.
    """
    global _config

    if _config is None:
        _config = load_config()

    return _config


def _override_from_env(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Override configuration values from environment variables."""

    # LLM configuration
    if os.getenv("OLLAMA_BASE_URL"):
        config_dict.setdefault("llm", {})
        config_dict["llm"]["base_url"] = os.getenv("OLLAMA_BASE_URL")

    if os.getenv("OLLAMA_MODEL"):
        config_dict.setdefault("llm", {})
        config_dict["llm"]["model"] = os.getenv("OLLAMA_MODEL")

    # Embedding configuration
    if os.getenv("EMBEDDING_MODEL"):
        config_dict.setdefault("embeddings", {})
        config_dict["embeddings"]["model"] = os.getenv("EMBEDDING_MODEL")

    if os.getenv("EMBEDDING_DIMENSION"):
        config_dict.setdefault("embeddings", {})
        config_dict["embeddings"]["dimension"] = int(os.getenv("EMBEDDING_DIMENSION"))

    # Vector store configuration
    if os.getenv("CHROMA_PERSIST_DIR"):
        config_dict.setdefault("vector_store", {})
        config_dict["vector_store"]["persist_directory"] = os.getenv("CHROMA_PERSIST_DIR")

    if os.getenv("CHROMA_COLLECTION_NAME"):
        config_dict.setdefault("vector_store", {})
        config_dict["vector_store"]["collection_name"] = os.getenv("CHROMA_COLLECTION_NAME")

    # Document processing
    if os.getenv("CHUNK_SIZE"):
        config_dict.setdefault("document_processing", {})
        config_dict["document_processing"]["chunk_size"] = int(os.getenv("CHUNK_SIZE"))

    if os.getenv("CHUNK_OVERLAP"):
        config_dict.setdefault("document_processing", {})
        config_dict["document_processing"]["chunk_overlap"] = int(os.getenv("CHUNK_OVERLAP"))

    # Retrieval configuration
    if os.getenv("RETRIEVAL_TOP_K"):
        config_dict.setdefault("retrieval", {})
        config_dict["retrieval"]["top_k"] = int(os.getenv("RETRIEVAL_TOP_K"))

    if os.getenv("SIMILARITY_THRESHOLD"):
        config_dict.setdefault("retrieval", {})
        config_dict["retrieval"]["similarity_threshold"] = float(os.getenv("SIMILARITY_THRESHOLD"))

    # Logging
    if os.getenv("LOG_LEVEL"):
        config_dict.setdefault("logging", {})
        config_dict["logging"]["level"] = os.getenv("LOG_LEVEL")

    if os.getenv("LOG_FILE"):
        config_dict.setdefault("logging", {})
        config_dict["logging"]["file"] = os.getenv("LOG_FILE")

    return config_dict
