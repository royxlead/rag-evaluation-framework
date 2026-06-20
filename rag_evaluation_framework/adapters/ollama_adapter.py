"""Ollama LLM adapter for local models."""

from __future__ import annotations

import os
from typing import Any

import httpx

from rag_evaluation_framework.adapters.base import LLMAdapter


class OllamaAdapter(LLMAdapter):
    """Adapter for local models via Ollama."""

    def __init__(self, model: str = "llama3", **kwargs: Any):
        super().__init__(model, **kwargs)
        self._base_url: str = (
        kwargs.get("base_url") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        )

    async def complete(self, prompt: str, temperature: float = 0.0, **kwargs: Any) -> str:
        async def _call() -> str:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False,
                        **kwargs,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")

        return await self._retry_with_backoff(_call)
