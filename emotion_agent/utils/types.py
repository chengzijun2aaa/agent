"""Shared typed models and enums used across the agent architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class ProviderName(str, Enum):
    """Supported LLM provider identifiers."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    GEMINI = "gemini"


class SenderRole(str, Enum):
    """Conversation message sender roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EmotionLabel(str, Enum):
    """Coarse emotion labels shared by analyzer and state layers."""

    UNKNOWN = "unknown"
    NEUTRAL = "neutral"
    SAD = "sad"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    HAPPY = "happy"


class IntentLabel(str, Enum):
    """Coarse intent labels shared by analyzer and strategy layers."""

    UNKNOWN = "unknown"
    SEEKING_COMFORT = "seeking_comfort"
    SEEKING_ADVICE = "seeking_advice"
    VENTING = "venting"
    CASUAL_CHAT = "casual_chat"


class RiskLevel(str, Enum):
    """Risk levels for escalation and safety-aware response planning."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyName(str, Enum):
    """Stable response strategy identifiers."""

    DEFAULT = "default"
    COMFORT = "comfort"
    CLARIFY = "clarify"
    BOUNDARY = "boundary"


@dataclass(frozen=True, slots=True)
class Message:
    """One conversation message with basic metadata."""

    role: SenderRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Typed result emitted by one analyzer."""

    analyzer_name: str
    label: str
    confidence: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Context object passed across pipeline components."""

    user_id: str
    current_message: Message
    recent_messages: Sequence[Message]
    state: Any
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Provider-agnostic request sent to an LLM adapter."""

    user_id: str
    message: str
    strategy_name: str
    analysis_labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Provider-agnostic response returned by any LLM adapter method."""

    provider: ProviderName
    content: str
    model: str | None = None
    success: bool = True
    status_code: int | None = None
    usage: Mapping[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def placeholder(cls, provider: ProviderName) -> "LLMResponse":
        """Create an empty placeholder provider response."""
        return cls(provider=provider, content="", metadata={"placeholder": True})

    @classmethod
    def failed(
        cls,
        provider: ProviderName,
        error_type: str,
        error_message: str,
        *,
        model: str | None = None,
        status_code: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "LLMResponse":
        """Create a failed response while preserving the unified return shape."""
        return cls(
            provider=provider,
            content="",
            model=model,
            success=False,
            status_code=status_code,
            error_type=error_type,
            error_message=error_message,
            metadata=metadata or {},
        )


ProviderResponse = LLMResponse


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Generated response plus provider and generation metadata."""

    text: str
    provider: ProviderName | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "GenerationResult":
        """Create an empty generation result."""
        return cls(text="", metadata={"placeholder": True})


@dataclass(frozen=True, slots=True)
class RankedResponse:
    """Final selected response with ranking metadata."""

    result: GenerationResult
    score: float
    reason: str


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"Types ready: {ProviderName.OPENAI.value}")


if __name__ == "__main__":
    _demo()
