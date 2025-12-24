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
        bearer_token: str = None,
        temperature: float = 0.1,
        max_tokens: int = 512,
        timeout: int = 60,
    ):
        """
        Initialize Ollama LLM.

        Args:
            model: Ollama model name
            base_url: Ollama API base URL
            bearer_token: Bearer token for Ollama API authentication (REQUIRED)
            temperature: LLM temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Raises:
            ValueError: If bearer_token is not provided
        """
        if not bearer_token:
            raise ValueError("OLLAMA_BEARER_TOKEN is required but not provided. Please set the environment variable.")

        self.model = model
        self.base_url = base_url
        self.bearer_token = bearer_token
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # Configure client with bearer token authentication
        client_kwargs = {
            "headers": {
                "Authorization": f"Bearer {bearer_token}"
            }
        }

        # Create langchain ChatOllama instance with authentication
        self.llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=max_tokens,
            timeout=timeout,
            client_kwargs=client_kwargs,
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
