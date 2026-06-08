"""Strategy selector for natural relationship progression."""

from __future__ import annotations

from typing import Sequence

from emotion_agent.strategy.base import BaseStrategySelector
from emotion_agent.strategy.reply_strategy import ReplyStrategy
from emotion_agent.utils.types import AgentContext, AnalysisResult


class ConquestStrategySelector(BaseStrategySelector):
    """Select legacy reply strategies without falling into pure comfort mode."""

    def __init__(self, fallback_strategy: ReplyStrategy | None = None) -> None:
        self._fallback_strategy = fallback_strategy or ReplyStrategy.default()

    @classmethod
    def default(cls) -> "ConquestStrategySelector":
        return cls()

    def select(
        self,
        context: AgentContext,
        analyses: Sequence[AnalysisResult],
    ) -> ReplyStrategy:
        """Select a high-level relationship move."""
        
        # 提取关键分析数据
        conv_analysis = next((a for a in analyses if a.analyzer_name == "conversation"), None)
        risk_analysis = next((a for a in analyses if a.analyzer_name == "risk"), None)
        if not conv_analysis:
            return self._fallback_strategy

        metadata = conv_analysis.metadata if hasattr(conv_analysis, 'metadata') else {}
        risk_meta = risk_analysis.metadata if risk_analysis and hasattr(risk_analysis, 'metadata') else {}

        stage = getattr(conv_analysis, 'relationship_stage', 'L1')
        escalation = getattr(conv_analysis, 'escalation_window', 'low')
        vuln = risk_meta.get('vulnerability', 0) or getattr(conv_analysis, 'vulnerability', 0)
        sex_tension = risk_meta.get('sexual_openness', 0) or getattr(conv_analysis, 'sexual_tension', 0)
        compliance = risk_meta.get('compliance', 0) or getattr(conv_analysis, 'compliance', 0)
        intent = getattr(conv_analysis, 'intent', '分享生活')

        # Strong intimacy signal: keep it playful, explicit, and feedback-aware.
        if escalation == "high" or (sex_tension >= 70 and vuln >= 60):
            return ReplyStrategy(
                name="playful_intimacy_progression",
                description="轻暧昧推进，表达期待，同时观察对方反馈",
                priority=100,
                tactics=["tease", "future_projection", "clear_preference", "feedback_check"]
            )

        # Emotional support should include a relationship direction, not just tree-hole comfort.
        if vuln >= 75 or intent in ("求安慰", "抱怨", "分享情绪"):
            return ReplyStrategy(
                name="support_then_progress",
                description="先接住情绪，再给偏爱感或低压力见面钩子",
                priority=95,
                tactics=["empathy", "preference_signal", "low_pressure_invite", "no_lecture"]
            )

        if compliance >= 65 or intent in ("服从测试", "寻求支配"):
            return ReplyStrategy(
                name="calm_leadership",
                description="给出清晰安排和稳定感，不使用命令或压迫",
                priority=90,
                tactics=["clear_plan", "warmth", "boundary_respect", "light_tease"]
            )

        if stage in ("L4", "L3") or intent in ("吃醋", "测试", "框架挑战"):
            return ReplyStrategy(
                name="tease_with_reassurance",
                description="轻调侃接住试探，同时给一点确定感",
                priority=85,
                tactics=["tease", "reassurance", "no_defensive_explaining", "preference_signal"]
            )

        if intent == "邀约" or (stage == "L5" and escalation != "low"):
            return ReplyStrategy(
                name="logistics_escalation",
                description="快速敲定线下安排，加一点轻松期待",
                priority=88,
                tactics=["logistics_close", "specific_time", "light_expectation", "low_pressure"]
            )

        return ReplyStrategy(
            name="attraction_building",
            description="轻松接话，避免纯闲聊，给下一句可回的口子",
            priority=70,
            tactics=["tease", "storytelling", "future_projection", "natural_question"]
        )


# 兼容旧代码
StrategySelector = ConquestStrategySelector


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{StrategySelector.default().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
