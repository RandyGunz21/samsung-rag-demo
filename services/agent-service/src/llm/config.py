"""Configuration loader for Agent Service LLM."""

import os
from typing import Any, Dict


def load_config() -> Dict[str, Any]:
    """
    Load LLM configuration from environment variables.

    Returns:
        Dict with configuration values
    """
    return {
        "llm.model": os.getenv("LLM_MODEL", "qwen2.5:7b"),
        "llm.base_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "llm.temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
        "llm.max_tokens": int(os.getenv("LLM_MAX_TOKENS", "512")),
        "llm.timeout": int(os.getenv("LLM_TIMEOUT", "60")),
    }
