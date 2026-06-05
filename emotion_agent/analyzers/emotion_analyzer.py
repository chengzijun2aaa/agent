"""Emotion analyzer placeholder."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.utils.types import AgentContext, AnalysisResult, EmotionLabel


class EmotionAnalyzer(BaseAnalyzer):
    """Extracts coarse emotion signals from the current conversation context."""

    @property
    def name(self) -> str:
        """Return the stable analyzer name."""
        return "emotion"

    def analyze(self, context: AgentContext) -> AnalysisResult:
        """Return a placeholder emotion analysis result."""
        return AnalysisResult(
            analyzer_name=self.name,
            label=EmotionLabel.UNKNOWN.value,
            confidence=0.0,
            metadata={"user_id": context.user_id},
        )


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{EmotionAnalyzer().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
