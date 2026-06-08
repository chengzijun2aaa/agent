"""Rank reply candidates across sincere attraction and safety dimensions."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.risk_detector import RiskReport
from emotion_agent.generator.reply_generator import ReplyCandidate


class ReplyScore(BaseModel):
    """Detailed score for one reply candidate."""

    model_config = ConfigDict(extra="ignore")

    candidate: ReplyCandidate
    naturalness: float = Field(ge=0.0, le=100.0)
    wechat_feel: float = Field(ge=0.0, le=100.0)
    risk_control: float = Field(ge=0.0, le=100.0)
    emotional_value: float = Field(ge=0.0, le=100.0)
    relationship_progress: float = Field(ge=0.0, le=100.0)
    total_score: float = Field(ge=0.0, le=100.0)
    reason: str = ""


class ReplyRanker:
    """Scores replies and selects the best final answer."""

    MANIPULATION_WORDS: tuple[str, ...] = ("拿捏", "吊着", "冷她", "刺激她", "让她吃醋", "PUA", "欲擒故纵")
    RISKY_WORDS: tuple[str, ...] = ("必须", "你应该", "别矫情", "想太多", "赶紧", "保证", "查岗")
    WARM_WORDS: tuple[str, ...] = ("我在", "听着", "辛苦", "懂", "抱抱", "站你", "陪")
    ATTRACTION_WORDS: tuple[str, ...] = ("想你", "可爱", "心动", "等到你", "注意力", "偏向", "在意")
    TEMPLATE_PHRASES: tuple[str, ...] = ("怎么突然想起问我这个", "我在，慢慢说", "我先接住你这句", "听起来你")
    STIFF_WORDS: tuple[str, ...] = ("情绪", "理解你", "你可以", "建议你", "先缓", "展开说说")

    def rank(
        self,
        candidates: Sequence[ReplyCandidate],
        risk: RiskReport,
        relationship_state: Mapping[str, Any],
        chat_history: Sequence[Mapping[str, Any] | str] | None = None,
    ) -> ReplyScore:
        """Return the highest-scoring candidate."""
        scores = [self.score(candidate, risk, relationship_state, chat_history or []) for candidate in candidates]
        if not scores:
            fallback = ReplyCandidate(text="我在，你慢慢说")
            return self.score(fallback, risk, relationship_state, chat_history or [])
        return max(scores, key=lambda item: item.total_score)

    def score(
        self,
        candidate: ReplyCandidate,
        risk: RiskReport,
        relationship_state: Mapping[str, Any],
        chat_history: Sequence[Mapping[str, Any] | str],
    ) -> ReplyScore:
        """Score one reply across all configured dimensions."""
        text = candidate.text.strip()
        length = len(text)
        naturalness = self._clamp(92 - abs(length - 18) * 1.15 - text.count("，") * 1.5)
        wechat_feel = self._clamp(72 + (14 if 4 <= length <= 34 else -14) + (6 if "你" in text else 0))
        risk_control = self._risk_control(text, risk)
        emotional_value = self._emotional_value(text)
        relationship_progress = self._relationship_progress(text, relationship_state)

        penalty = self._repeat_penalty(text, chat_history)
        penalty += sum(18 for phrase in self.TEMPLATE_PHRASES if phrase in text)
        penalty += sum(35 for word in self.MANIPULATION_WORDS if word in text)
        penalty += sum(12 for word in self.STIFF_WORDS if word in text)

        total = (
            naturalness * 0.2
            + wechat_feel * 0.18
            + risk_control * 0.24
            + emotional_value * 0.24
            + relationship_progress * 0.14
            - penalty
        )
        return ReplyScore(
            candidate=candidate,
            naturalness=naturalness,
            wechat_feel=wechat_feel,
            risk_control=risk_control,
            emotional_value=emotional_value,
            relationship_progress=relationship_progress,
            total_score=self._clamp(total),
            reason=f"weighted_quality_score penalty={round(penalty, 2)}",
        )

    def _risk_control(self, text: str, risk: RiskReport) -> float:
        """Score whether reply avoids unsafe pressure."""
        score = 92
        score -= sum(18 for word in self.RISKY_WORDS if word in text)
        score -= sum(35 for word in self.MANIPULATION_WORDS if word in text)
        if risk.risk_level != "low" and any(word in text for word in ("暧昧", "喜欢你", "约会", "想你")):
            score -= 35
        if risk.risk_level != "low" and any(word in text for word in ("我在", "听着", "慢慢", "先缓")):
            score += 8
        return self._clamp(score)

    def _emotional_value(self, text: str) -> float:
        """Score whether the reply gives emotional value."""
        score = 45
        score += sum(11 for word in self.WARM_WORDS if word in text)
        score += 8 if any(word in text for word in ("怎么想", "你呢", "继续说", "说说")) else 0
        score -= 12 if any(word in text for word in ("哈哈哈", "随便", "哦")) else 0
        return self._clamp(score)

    def _relationship_progress(self, text: str, relationship_state: Mapping[str, Any]) -> float:
        """Score stage-appropriate relationship progress."""
        stage = str(relationship_state.get("stage", "L1"))
        score = 52
        attraction_hits = sum(8 for word in self.ATTRACTION_WORDS if word in text)
        score += attraction_hits
        if stage in {"L1", "L2"} and attraction_hits >= 16:
            score -= 24
        if stage in {"L4", "L5", "L6"} and attraction_hits:
            score += 12
        if "查岗" in text and stage in {"L1", "L2", "L3"}:
            score -= 20
        return self._clamp(score)

    @staticmethod
    def _repeat_penalty(text: str, chat_history: Sequence[Mapping[str, Any] | str]) -> float:
        """Penalize replies that repeat recent assistant messages."""
        normalized = ReplyRanker._normalize(text)
        penalty = 0.0
        for item in chat_history[-12:]:
            if isinstance(item, str):
                continue
            if str(item.get("role", "")) != "assistant":
                continue
            previous = ReplyRanker._normalize(str(item.get("content", "")))
            if not previous:
                continue
            if normalized == previous:
                penalty += 38
            elif normalized and (normalized in previous or previous in normalized):
                penalty += 18
        return penalty

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for repeat checks."""
        return "".join(ch for ch in text.lower() if ch.isalnum())

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp score into 0-100."""
        return max(0.0, min(100.0, float(value)))


def _demo() -> None:
    """Run a small module smoke test."""
    best = ReplyRanker().rank([ReplyCandidate(text="刚忙完，准备歇会儿")], RiskReport(), {"stage": "L1"})
    print(best.model_dump())


if __name__ == "__main__":
    _demo()
