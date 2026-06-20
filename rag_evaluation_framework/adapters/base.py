"""Abstract base class for LLM adapters."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters.

    All adapters support async completion, batch processing, and embeddings.
    """

    def __init__(self, model: str, **kwargs: Any):
        self.model: str = model
        self._embedder: SentenceTransformer | None = None
        self._max_retries: int = kwargs.pop("max_retries", 3)
        self._base_delay: float = kwargs.pop("base_delay", 1.0)

    @abstractmethod
    async def complete(self, prompt: str, temperature: float = 0.0, **kwargs: Any) -> str:
        """Send a completion request and return the response text.

        Args:
            prompt: The prompt string.
            temperature: Sampling temperature (0 = deterministic).
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated text response.
        """
        ...

    async def complete_batch(
        self, prompts: list[str], temperature: float = 0.0, **kwargs: Any
    ) -> list[str]:
        """Process multiple prompts in parallel.

        Default implementation uses asyncio.gather. Override for provider-specific batching.
        """
        tasks = [self.complete(p, temperature=temperature, **kwargs) for p in prompts]
        return await asyncio.gather(*tasks)

    async def embed(self, text: str | list[str]) -> np.ndarray:
        """Generate embeddings using sentence-transformers.

        Args:
            text: Single string or list of strings.

        Returns:
            numpy array of embeddings.
        """
        embedder = self.get_embedder()
        if isinstance(text, str):
            return embedder.encode(text, normalize_embeddings=True)
        return embedder.encode(text, normalize_embeddings=True)

    def get_embedder(self) -> SentenceTransformer:
        """Return the sentence-transformer embedder (singleton)."""
        if self._embedder is None:
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    async def _retry_with_backoff(self, coro_factory, retries: int | None = None) -> Any:
        """Execute a coroutine with exponential backoff retry."""
        retries = retries or self._max_retries
        last_exception: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return await coro_factory()
            except Exception as e:
                last_exception = e
                if attempt < retries:
                    delay = self._base_delay * (2**attempt)
                    await asyncio.sleep(delay)
        raise last_exception  # type: ignore[misc]
