"""Base interfaces for response ranking."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod
from typing import Sequence

from emotion_agent.utils.types import AgentContext, GenerationResult, RankedResponse


class BaseRanker(ABC):
    """Abstract interface for selecting the best response candidate."""

    @abstractmethod
    def rank(self, context: AgentContext, candidates: Sequence[GenerationResult]) -> RankedResponse:
        """Rank candidates and return the selected response wrapper."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseRanker interface ready")


if __name__ == "__main__":
    _demo()
