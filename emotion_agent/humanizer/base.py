"""Base interfaces for response humanization."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod

from emotion_agent.utils.types import AgentContext, GenerationResult


class BaseHumanizer(ABC):
    """Abstract interface for response humanizers."""

    @abstractmethod
    def humanize(self, context: AgentContext, draft: GenerationResult) -> GenerationResult:
        """Polish a draft response while preserving generation metadata."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseHumanizer interface ready")


if __name__ == "__main__":
    _demo()
