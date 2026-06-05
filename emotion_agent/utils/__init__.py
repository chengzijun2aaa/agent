"""Shared utilities, configuration, exceptions, and typed data models."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.utils.config import AgentConfig, ProviderConfig
from emotion_agent.utils.exceptions import (
    APIAuthenticationError,
    APINetworkError,
    APITimeoutError,
    AgentError,
    ConfigurationError,
    ProviderError,
    StorageError,
)
from emotion_agent.utils.types import (
    AgentContext,
    AnalysisResult,
    EmotionLabel,
    GenerationResult,
    IntentLabel,
    LLMResponse,
    Message,
    ProviderName,
    ProviderRequest,
    ProviderResponse,
    RankedResponse,
    RiskLevel,
    SenderRole,
    StrategyName,
)

__all__ = [
    "AgentConfig",
    "AgentContext",
    "AgentError",
    "APIAuthenticationError",
    "APINetworkError",
    "APITimeoutError",
    "AnalysisResult",
    "ConfigurationError",
    "EmotionLabel",
    "GenerationResult",
    "IntentLabel",
    "LLMResponse",
    "Message",
    "ProviderConfig",
    "ProviderError",
    "ProviderName",
    "ProviderRequest",
    "ProviderResponse",
    "RankedResponse",
    "RiskLevel",
    "SenderRole",
    "StorageError",
    "StrategyName",
]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Utils package ready")


if __name__ == "__main__":
    _demo()
