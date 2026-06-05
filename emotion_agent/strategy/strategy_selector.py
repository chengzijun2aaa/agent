"""Default strategy selector placeholder."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Sequence

from emotion_agent.strategy.base import BaseStrategySelector
from emotion_agent.strategy.reply_strategy import ReplyStrategy
from emotion_agent.utils.types import AgentContext, AnalysisResult


class StrategySelector(BaseStrategySelector):
    """Selects a reply strategy using pluggable future policy logic."""

    def __init__(self, fallback_strategy: ReplyStrategy | None = None) -> None:
        """Create a strategy selector with a fallback strategy."""
        self._fallback_strategy = fallback_strategy or ReplyStrategy.default()

    @classmethod
    def default(cls) -> "StrategySelector":
        """Create a default selector instance."""
        return cls()

    def select(
        self,
        context: AgentContext,
        analyses: Sequence[AnalysisResult],
    ) -> ReplyStrategy:
        """Return the configured fallback strategy as a placeholder."""
        _ = context
        _ = analyses
        return self._fallback_strategy


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{StrategySelector.default().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
