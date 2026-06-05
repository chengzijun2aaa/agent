"""Intent analyzer placeholder."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.utils.types import AgentContext, AnalysisResult, IntentLabel


class IntentAnalyzer(BaseAnalyzer):
    """Extracts user intent signals from the current conversation context."""

    @property
    def name(self) -> str:
        """Return the stable analyzer name."""
        return "intent"

    def analyze(self, context: AgentContext) -> AnalysisResult:
        """Return a placeholder intent analysis result."""
        return AnalysisResult(
            analyzer_name=self.name,
            label=IntentLabel.UNKNOWN.value,
            confidence=0.0,
            metadata={"message_role": context.current_message.role.value},
        )


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{IntentAnalyzer().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
