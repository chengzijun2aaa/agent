"""Analyzer components for extracting non-authoritative conversation signals."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.analyzers.conversation_analyzer import (
    ChatMessage,
    ConversationAnalysis,
    ConversationAnalysisPromptTemplate,
    ConversationAnalyzer,
)
from emotion_agent.analyzers.emotion_analyzer import EmotionAnalyzer
from emotion_agent.analyzers.intent_analyzer import IntentAnalyzer
from emotion_agent.analyzers.risk_detector import RiskDetector, RiskReport
from emotion_agent.analyzers.risk_analyzer import RiskAnalyzer

__all__ = [
    "BaseAnalyzer",
    "ChatMessage",
    "ConversationAnalysis",
    "ConversationAnalysisPromptTemplate",
    "ConversationAnalyzer",
    "EmotionAnalyzer",
    "IntentAnalyzer",
    "RiskDetector",
    "RiskReport",
    "RiskAnalyzer",
]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Analyzer package ready")


if __name__ == "__main__":
    _demo()
