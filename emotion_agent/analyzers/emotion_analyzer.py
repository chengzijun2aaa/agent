"""Emotion Analyzer - 深度心理+性情绪探测"""

from __future__ import annotations

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.utils.types import AgentContext, AnalysisResult, EmotionLabel


class EmotionAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "emotion"

    def analyze(self, context: AgentContext) -> AnalysisResult:
        text = context.current_message.content.lower() + " " + " ".join([m.content.lower() for m in context.recent_messages[-5:]])

        # 更细粒度情绪 + 性欲信号
        if any(k in text for k in ["想你", "抱抱", "晚安想你", "好热", "洗澡", "坏坏"]):
            emotion = "sexual_interest"
            confidence = 85
        elif any(k in text for k in ["难受", "委屈", "没人懂", "压力好大"]):
            emotion = "vulnerable"
            confidence = 90
        elif any(k in text for k in ["哈哈", "笑死", "逗你"]):
            emotion = "playful"
            confidence = 75
        else:
            emotion = "neutral"
            confidence = 60

        return AnalysisResult(
            analyzer_name=self.name,
            label=emotion,
            confidence=confidence,
            metadata={"raw_text": context.current_message.content}
        )


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{EmotionAnalyzer().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
