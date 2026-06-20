"""LiteLLM adapter fallback for any model supported by LiteLLM."""

from __future__ import annotations

from typing import Any

from litellm import acompletion

from rag_evaluation_framework.adapters.base import LLMAdapter


class LiteLLMAdapter(LLMAdapter):
    """Adapter for any model via LiteLLM (fallback)."""

    def __init__(self, model: str = "gpt-4o", **kwargs: Any):
        # LiteLLM model string includes provider, e.g. "openai/gpt-4o"
        super().__init__(model, **kwargs)
        self._litellm_model: str = kwargs.get("litellm_model", model)

    async def complete(self, prompt: str, temperature: float = 0.0, **kwargs: Any) -> str:
        async def _call() -> str:
            response = await acompletion(
                model=self._litellm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **kwargs,
            )
            return response.choices[0].message.content or ""

        return await self._retry_with_backoff(_call)
