"""LLM provider boundaries for supported model vendors."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.providers.base import BaseLLM, BaseLLMProvider
from emotion_agent.providers.claude_provider import ClaudeProvider
from emotion_agent.providers.deepseek_provider import DeepSeekProvider
from emotion_agent.providers.gemini_provider import GeminiProvider
from emotion_agent.providers.openai_provider import OpenAIProvider
from emotion_agent.providers.provider_factory import ProviderFactory

__all__ = [
    "BaseLLMProvider",
    "BaseLLM",
    "ClaudeProvider",
    "DeepSeekProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "ProviderFactory",
]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Providers package ready")


if __name__ == "__main__":
    _demo()
