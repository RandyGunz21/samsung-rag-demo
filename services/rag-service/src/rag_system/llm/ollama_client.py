"""
Ollama LLM client for local inference.

Provides interface for querying local LLM models via Ollama.
"""

from typing import Optional, Dict, Any
from langchain_ollama import ChatOllama

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaLLM:
    """Ollama LLM client for local inference."""

    def __init__(
        self,
        model: str = "gemma2:2b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        max_tokens: Optional[int] = 512,
        timeout: int = 60,
    ):
        """
        Initialize Ollama LLM client.

        Args:
            model: Model name (e.g., 'gemma2:2b', 'llama3:8b')
            base_url: Ollama API base URL
            temperature: Sampling temperature (0=deterministic, 1=creative)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        logger.info(f"Initializing Ollama LLM: model={model}, base_url={base_url}")

        self.llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=max_tokens,
            timeout=timeout,
        )

        logger.info("Ollama LLM initialized successfully")

    def invoke(self, prompt: str) -> str:
        """
        Invoke LLM with a prompt.

        Args:
            prompt: Input prompt

        Returns:
            Generated response
        """
        logger.debug(f"Invoking LLM with prompt: {prompt[:100]}...")

        try:
            response = self.llm.invoke(prompt)
            result = response.content if hasattr(response, "content") else str(response)

            logger.debug(f"LLM response: {result[:100]}...")

            return result

        except Exception as e:
            logger.error(f"LLM invocation failed: {str(e)}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }
