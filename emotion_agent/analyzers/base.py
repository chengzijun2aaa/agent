"""Base interfaces for conversation analyzers."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod

from emotion_agent.utils.types import AgentContext, AnalysisResult


class BaseAnalyzer(ABC):
    """Abstract base class for all conversation signal analyzers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable analyzer name used in logs and downstream metadata."""

    @abstractmethod
    def analyze(self, context: AgentContext) -> AnalysisResult:
        """Analyze the current context and return a typed result."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseAnalyzer interface ready")


if __name__ == "__main__":
    _demo()
