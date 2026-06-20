"""Shared test fixtures and mock adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rag_evaluation_framework.adapters.base import LLMAdapter


class MockLLMAdapter(LLMAdapter):
    """Mock adapter that returns canned responses for deterministic tests."""

    def __init__(self, model: str = "mock/gpt-4o", responses: dict | None = None, **kwargs: Any):
        super().__init__(model, **kwargs)
        self.responses = responses or {}
        self.call_history: list[dict] = []

    async def complete(self, prompt: str, temperature: float = 0.0, **kwargs: Any) -> str:
        self.call_history.append({"prompt": prompt[:50], "temperature": temperature})

        # Check for exact match
        if prompt in self.responses:
            return self.responses[prompt]

        # Check for partial match
        for key, response in self.responses.items():
            if key in prompt:
                return response

        # Default responses based on prompt content
        if "decompose" in prompt.lower() or "atomic" in prompt.lower():
            return '["The capital of France is Paris.", "Paris is in Europe."]'
        if (
            "SUPPORTED" in prompt.upper()
            or "NOT_SUPPORTED" in prompt.upper()
            or "fact-checking" in prompt.lower()
            or "claim" in prompt.lower()
        ):
            return "SUPPORTED"
        if "grounded" in prompt.lower() or "hallucination" in prompt.lower():
            return '{"grounded": true, "factual": true, "reason": "Supported by context"}'
        if "relevance" in prompt.lower():
            return "0.95"
        if "coverage" in prompt.lower():
            return "0.90"
        if "extract" in prompt.lower() or "claims" in prompt.lower():
            return '["Paris is the capital of France."]'

        return "Mock response"

    async def embed(self, text: str | list[str]) -> Any:
        import numpy as np

        if isinstance(text, str):
            return np.random.randn(384).astype(np.float32)
        return np.random.randn(len(text), 384).astype(np.float32)


@pytest.fixture
def mock_adapter():
    """Return a MockLLMAdapter."""
    return MockLLMAdapter()


@pytest.fixture
def sample_eval_input():
    """Standard test input for evaluation."""
    return {
        "question": "What is the capital of France?",
        "context": ["France is a country in Western Europe. Its capital is Paris."],
        "answer": "The capital of France is Paris.",
    }


@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"
