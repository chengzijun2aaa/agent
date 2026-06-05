"""Base interfaces for response generation."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod
from typing import Sequence

from emotion_agent.strategy.reply_strategy import ReplyStrategy
from emotion_agent.utils.types import AgentContext, AnalysisResult, GenerationResult


class BaseGenerator(ABC):
    """Abstract interface for draft response generators."""

    @abstractmethod
    def generate(
        self,
        context: AgentContext,
        strategy: ReplyStrategy,
        analyses: Sequence[AnalysisResult],
    ) -> GenerationResult:
        """Generate a draft response for the current context."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseGenerator interface ready")


if __name__ == "__main__":
    _demo()
