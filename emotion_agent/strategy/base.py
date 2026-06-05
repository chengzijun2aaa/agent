"""Base interfaces for response strategy selection."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod
from typing import Sequence

from emotion_agent.strategy.reply_strategy import ReplyStrategy
from emotion_agent.utils.types import AgentContext, AnalysisResult


class BaseStrategySelector(ABC):
    """Abstract interface for selecting a response strategy."""

    @abstractmethod
    def select(
        self,
        context: AgentContext,
        analyses: Sequence[AnalysisResult],
    ) -> ReplyStrategy:
        """Select a response strategy for the current context."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseStrategySelector interface ready")


if __name__ == "__main__":
    _demo()
