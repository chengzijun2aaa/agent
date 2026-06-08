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
    support: int = Field(default=0, ge=0, le=100)
    conflict: int = Field(default=0, ge=0, le=100)
    boundary: int = Field(default=0, ge=0, le=100)
    crisis: int = Field(default=0, ge=0, le=100)


class RiskDetector:
    """Detects safety, relationship, and reply-generation risk."""

    HIGH_RISK: tuple[str, ...] = ("自杀", "轻生", "不想活", "活不下去", "伤害自己", "结束生命")
    MEDIUM_RISK: tuple[str, ...] = ("崩溃", "绝望", "抑郁", "失眠", "喝酒", "撑不住")
    SUPPORT_RISK: tuple[str, ...] = ("难受", "想哭", "委屈", "累", "压力", "加班", "烦", "emo", "没人懂")
    CONFLICT_RISK: tuple[str, ...] = ("傻逼", "傻卵", "弱智", "有病", "滚", "闭嘴", "吵架", "别说了")
    RELATIONSHIP_RISK: tuple[str, ...] = ("拉黑", "分手", "别烦我", "不想理你", "冷静一下", "别管我")
    BOUNDARY_RISK: tuple[str, ...] = ("查岗", "凭什么", "管太多", "别问", "别催", "压力好大")

    def detect(self, chat_history: Sequence[ChatHistoryItem]) -> RiskReport:
        """Detect risk from recent chat records."""
        text = "\n".join(self._content(item) for item in chat_history)
        high_hits = self._hits(text, self.HIGH_RISK)
        medium_hits = self._hits(text, self.MEDIUM_RISK)
        support_hits = self._hits(text, self.SUPPORT_RISK)
        conflict_hits = self._hits(text, self.CONFLICT_RISK)
        relationship_hits = self._hits(text, self.RELATIONSHIP_RISK)
        boundary_hits = self._hits(text, self.BOUNDARY_RISK)

        crisis = 92 if high_hits else min(len(medium_hits) * 28, 72)
        support = min(len(support_hits) * 18 + len(medium_hits) * 20, 100)
        conflict = min(len(conflict_hits) * 32, 100)
        boundary = min(len(relationship_hits) * 35 + len(boundary_hits) * 22, 100)
        reasons = [*high_hits, *medium_hits, *support_hits, *conflict_hits, *relationship_hits, *boundary_hits]

        if crisis >= 80:
            return RiskReport(
                risk_level="high",
                blocked=True,
                reasons=reasons,
                safety_instruction="优先安全陪伴，建议寻求现实支持或紧急帮助，不推进关系。",
                support=support,
                conflict=conflict,
                boundary=boundary,
                crisis=crisis,
            )

        if crisis >= 60 or conflict >= 60 or boundary >= 60:
            instruction = (
                "降低暧昧和调侃，先承接情绪，避免刺激性表达。"
                if crisis >= 60
                else "降低压迫感，尊重边界，避免追问和强推进。"
            )
            return RiskReport(
                risk_level="medium",
                blocked=False,
                reasons=reasons,
                safety_instruction=instruction,
                support=support,
                conflict=conflict,
                boundary=boundary,
                crisis=crisis,
            )

        return RiskReport(
            risk_level="low",
            reasons=reasons,
            safety_instruction="保持自然，避免夸张承诺。",
            support=support,
            conflict=conflict,
            boundary=boundary,
            crisis=crisis,
        )

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
