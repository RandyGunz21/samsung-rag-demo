"""Ollama LLM wrapper for Agent Service."""

from typing import Optional
from langchain_ollama import ChatOllama


class OllamaLLM:
    """
    Wrapper for Ollama LLM via langchain.

    Provides a simple interface to Ollama language models.
    """

    def __init__(
        self,
        model: str = "llama4:scout",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        max_tokens: int = 512,
        timeout: int = 60,
    ):
        """
        Initialize Ollama LLM.

        Args:
            model: Ollama model name
            base_url: Ollama API base URL
            temperature: LLM temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # Create langchain ChatOllama instance
        self.llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=max_tokens,
            timeout=timeout,
        )

    def invoke(self, prompt: str) -> str:
        """
        Invoke LLM with a prompt.

        Args:
            prompt: Text prompt

        Returns:
            Generated text response
        """
        result = self.llm.invoke(prompt)
        return result.content if hasattr(result, "content") else str(result)
