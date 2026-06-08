"""Risk analyzer for progression opportunities and boundary signals."""

from __future__ import annotations

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.utils.types import AgentContext, AnalysisResult
from .risk_detector import ConquestOpportunityDetector


class RiskAnalyzer(BaseAnalyzer):
    """Detect support needs, progression windows, and caution signals."""

    def __init__(self):
        self.detector = ConquestOpportunityDetector()

    @property
    def name(self) -> str:
        return "risk"

    def analyze(self, context: AgentContext) -> AnalysisResult:
        history = [*context.recent_messages, context.current_message]
        report = self.detector.detect(history)

        return AnalysisResult(
            analyzer_name=self.name,
            label=report.risk_level,
            confidence=90,
            metadata={
                "vulnerability": report.vulnerability,
                "sexual_openness": report.sexual_openness,
                "compliance": report.compliance,
                "escalation_potential": report.escalation_potential,
                "strategy_instruction": report.strategy_instruction,
            }
        )


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{RiskAnalyzer().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
