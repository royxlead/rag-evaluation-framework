"""OpenAI LLM adapter."""

from __future__ import annotations

import os
from typing import Any

import openai

from rag_evaluation_framework.adapters.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI models (GPT-4, GPT-3.5, etc.)."""

    def __init__(self, model: str = "gpt-4o", **kwargs: Any):
        super().__init__(model, **kwargs)
        api_key = kwargs.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Pass api_key or set OPENAI_API_KEY environment variable."
            )
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(self, prompt: str, temperature: float = 0.0, **kwargs: Any) -> str:
        async def _call() -> str:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **kwargs,
            )
            return response.choices[0].message.content or ""

        return await self._retry_with_backoff(_call)
