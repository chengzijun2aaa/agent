"""Risk detection for emotional WeChat replies."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.utils.types import Message, SenderRole


ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message"


class RiskReport(BaseModel):
    """Structured risk report used before strategy planning."""

    model_config = ConfigDict(extra="ignore")

    risk_level: str = Field(default="low")
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    safety_instruction: str = ""


class RiskDetector:
    """Detects safety, relationship, and reply-generation risk."""

    HIGH_RISK: tuple[str, ...] = ("自杀", "轻生", "不想活", "活不下去", "伤害自己", "结束生命")
    MEDIUM_RISK: tuple[str, ...] = ("崩溃", "绝望", "抑郁", "失眠", "喝酒", "撑不住")
    RELATIONSHIP_RISK: tuple[str, ...] = ("拉黑", "分手", "别烦我", "不想理你", "冷静一下")

    def detect(self, chat_history: Sequence[ChatHistoryItem]) -> RiskReport:
        """Detect risk from recent chat records."""
        text = "\n".join(self._content(item) for item in chat_history)
        reasons: list[str] = []
        if hits := self._hits(text, self.HIGH_RISK):
            reasons.extend(hits)
            return RiskReport(
                risk_level="high",
                blocked=True,
                reasons=reasons,
                safety_instruction="优先安全陪伴，建议寻求现实支持或紧急帮助，不推进关系。",
            )
        if hits := self._hits(text, self.MEDIUM_RISK):
            reasons.extend(hits)
            return RiskReport(
                risk_level="medium",
                blocked=False,
                reasons=reasons,
                safety_instruction="降低暧昧和调侃，先承接情绪，避免刺激性表达。",
            )
        if hits := self._hits(text, self.RELATIONSHIP_RISK):
            reasons.extend(hits)
            return RiskReport(
                risk_level="medium",
                blocked=False,
                reasons=reasons,
                safety_instruction="降低压迫感，尊重边界，避免追问和强推进。",
            )
        return RiskReport(risk_level="low", safety_instruction="保持自然，避免夸张承诺。")

    @staticmethod
    def _hits(text: str, keywords: Sequence[str]) -> list[str]:
        """Return matched risk keywords."""
        return [keyword for keyword in keywords if keyword in text]

    @staticmethod
    def _content(item: ChatHistoryItem) -> str:
        """Extract message content from supported input shapes."""
        if isinstance(item, Message):
            return item.content
        if isinstance(item, str):
            return item
        return str(item.get("content", item.get("text", item.get("message", ""))))


def _demo() -> None:
    """Run a small module smoke test."""
    print(RiskDetector().detect(["今天压力好大，快崩溃了"]).model_dump())


if __name__ == "__main__":
    _demo()
