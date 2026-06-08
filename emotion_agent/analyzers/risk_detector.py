"""Risk detector for romantic progression and boundary control."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, TypeAlias
from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.utils.types import Message, SenderRole


ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message"


class RiskReport(BaseModel):
    """Progression report used by strategy planning."""

    model_config = ConfigDict(extra="ignore")

    risk_level: str = Field(default="low")  # low/medium/high progression caution
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    strategy_instruction: str = ""
    vulnerability: int = Field(default=0, ge=0, le=100)
    sexual_openness: int = Field(default=0, ge=0, le=100)
    compliance: int = Field(default=0, ge=0, le=100)
    escalation_potential: int = Field(default=0, ge=0, le=100)


class ConquestOpportunityDetector:
    """Detect whether the next reply can progress without feeling like a tree hole."""

    VULNERABILITY_KEYWORDS = ("难受", "想哭", "委屈", "累", "压力", "没人懂", "崩溃", "emo", "孤独", "空虚")
    SEXUAL_SIGNALS = ("想你", "抱抱", "晚安", "睡觉", "洗澡", "穿什么", "好热", "无聊", "坏", "色", "讨厌你")
    COMPLIANCE_SIGNALS = ("听你的", "好吧", "嗯嗯", "你说", "随便你", "看你", "都可以")
    HIGH_ESCALATION = ("想见你", "一起", "见面", "来我家", "你好坏", "讨厌", "哼")

    def detect(self, chat_history: Sequence[ChatHistoryItem]) -> RiskReport:
        text = "\n".join(self._content(item) for item in chat_history).lower()

        vuln_hits = [k for k in self.VULNERABILITY_KEYWORDS if k in text]
        sex_hits = [k for k in self.SEXUAL_SIGNALS if k in text]
        comp_hits = [k for k in self.COMPLIANCE_SIGNALS if k in text]
        esc_hits = [k for k in self.HIGH_ESCALATION if k in text]

        vulnerability = min(len(vuln_hits) * 25 + len(sex_hits) * 15, 100)
        sexual_openness = min(len(sex_hits) * 22 + len(esc_hits) * 18, 100)
        compliance = min(len(comp_hits) * 20 + len(esc_hits) * 15, 100)
        escalation = min(len(esc_hits) * 30 + vulnerability * 0.6, 100)

        reasons = vuln_hits + sex_hits + comp_hits + esc_hits

        if escalation >= 75 or vulnerability >= 70:
            level = "high"
            instruction = "先稳住情绪，再给低压力见面/陪伴钩子；不要压迫或跳过对方反馈。"
        elif sexual_openness >= 50 or compliance >= 60:
            level = "medium"
            instruction = "可以轻暧昧推进，优先表达偏爱和见面期待，观察对方是否继续接。"
        else:
            level = "low"
            instruction = "保持轻松接话，减少纯安慰，适合加入一个自然延展或轻邀约。"

        return RiskReport(
            risk_level=level,
            blocked=False,
            reasons=reasons,
            strategy_instruction=instruction,
            vulnerability=vulnerability,
            sexual_openness=sexual_openness,
            compliance=compliance,
            escalation_potential=escalation,
        )

    @staticmethod
    def _content(item: ChatHistoryItem) -> str:
        if isinstance(item, Message):
            return item.content
        if isinstance(item, str):
            return item
        return str(item.get("content", item.get("text", item.get("message", ""))))


# 兼容旧代码
RiskDetector = ConquestOpportunityDetector


def _demo() -> None:
    """Run a small module smoke test."""
    print(RiskDetector().detect(["今天压力好大，快崩溃了"]).model_dump())


if __name__ == "__main__":
    _demo()
