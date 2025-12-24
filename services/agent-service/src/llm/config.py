"""Configuration loader for Agent Service LLM."""

import os
from typing import Any, Dict


def load_config() -> Dict[str, Any]:
    """
    Load LLM configuration from environment variables.

    Returns:
        Dict with configuration values

    Raises:
        ValueError: If OLLAMA_BEARER_TOKEN is not set
    """
    bearer_token = os.getenv("OLLAMA_BEARER_TOKEN")
    if not bearer_token:
        raise ValueError("OLLAMA_BEARER_TOKEN is required but not provided. Please set the environment variable.")

    return {
        "llm.model": os.getenv("LLM_MODEL", "qwen2.5:7b"),
        "llm.base_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "llm.bearer_token": bearer_token,
        "llm.temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
        "llm.max_tokens": int(os.getenv("LLM_MAX_TOKENS", "512")),
        "llm.timeout": int(os.getenv("LLM_TIMEOUT", "60")),
    }
