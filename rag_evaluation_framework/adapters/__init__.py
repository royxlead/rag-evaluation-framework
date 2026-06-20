"""LLM Adapters for RAG Evaluation Framework.

All adapter imports are lazy they only resolve when the adapter is actually
requested via get_adapter(). This allows importing rag_evaluation_framework without requiring
all optional provider dependencies (openai, anthropic, litellm, etc.).
"""

from __future__ import annotations

from typing import Any

from rag_evaluation_framework.adapters.base import LLMAdapter

__all__ = [
"LLMAdapter",
"get_adapter",
]


def _lazy_load_adapter(
provider: str, model: str, config: dict[str, Any] | None = None
) -> LLMAdapter:
    """Import and instantiate an adapter lazily.

    This avoids ModuleNotFoundError at import time for optional dependencies.
    """
    if provider == "openai":
        from rag_evaluation_framework.adapters.openai_adapter import OpenAIAdapter

        return OpenAIAdapter(model=model, **(config or {}))
    elif provider == "anthropic":
        from rag_evaluation_framework.adapters.anthropic_adapter import AnthropicAdapter

        return AnthropicAdapter(model=model, **(config or {}))
    elif provider == "ollama":
        from rag_evaluation_framework.adapters.ollama_adapter import OllamaAdapter

        return OllamaAdapter(model=model, **(config or {}))
    elif provider == "litellm":
        from rag_evaluation_framework.adapters.litellm_adapter import LiteLLMAdapter

        return LiteLLMAdapter(model=model, **(config or {}))
    else:
        raise ValueError(
        f"Unknown provider '{provider}'. Available: openai, anthropic, ollama, litellm"
        )


def get_adapter(model_string: str, config: dict | None = None) -> LLMAdapter:
    """Factory: parse 'provider/model' string and return the matching adapter.

    Adapter classes are imported lazily on first use, so optional dependencies
    (openai, anthropic, litellm) are only required when that specific adapter
    is requested.

    Args:
        model_string: Format 'provider/model', e.g. 'openai/gpt-4o',
        'anthropic/claude-3-5-sonnet', 'ollama/llama3', 'litellm/gpt-4'.
        config: Optional config dict passed to the adapter constructor.

    Returns:
        An initialized LLMAdapter instance.

    Raises:
        ValueError: If provider is unknown or model_string format is invalid.
        ModuleNotFoundError: If the provider's package is not installed.
    """
    if "/" not in model_string:
        raise ValueError(f"Model string must be in format 'provider/model', got '{model_string}'")
    provider, model = model_string.split("/", 1)
    provider = provider.lower()
    config = config or {}
    return _lazy_load_adapter(provider, model, config)
