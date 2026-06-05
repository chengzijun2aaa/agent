"""Rank reply candidates across emotional chat quality dimensions."""

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

    RISKY_WORDS: tuple[str, ...] = ("必须", "你应该", "别矫情", "想太多", "赶紧", "保证")
    WARM_WORDS: tuple[str, ...] = ("我在", "听你说", "抱抱", "辛苦", "懂", "陪", "在意", "想")
    PUSH_WORDS: tuple[str, ...] = ("一起", "下次", "见", "回你", "问我", "想")

    def rank(
        self,
        candidates: Sequence[ReplyCandidate],
        risk: RiskReport,
        relationship_state: Mapping[str, Any],
    ) -> ReplyScore:
        """Return the highest-scoring candidate."""
        scores = [self.score(candidate, risk, relationship_state) for candidate in candidates]
        if not scores:
            fallback = ReplyCandidate(text="我在，你慢慢说")
            return self.score(fallback, risk, relationship_state)
        return max(scores, key=lambda item: item.total_score)

    def score(self, candidate: ReplyCandidate, risk: RiskReport, relationship_state: Mapping[str, Any]) -> ReplyScore:
        """Score one reply across all configured dimensions."""
        text = candidate.text
        length = len(text)
        naturalness = self._clamp(90 - abs(length - 22) * 1.4 - text.count("，") * 2)
        wechat_feel = self._clamp(70 + (15 if length <= 36 else -10) + (8 if "你" in text else 0))
        risk_control = self._risk_control(text, risk)
        emotional_value = self._clamp(45 + sum(10 for word in self.WARM_WORDS if word in text))
        relationship_progress = self._relationship_progress(text, relationship_state)
        total = (
            naturalness * 0.22
            + wechat_feel * 0.2
            + risk_control * 0.24
            + emotional_value * 0.2
            + relationship_progress * 0.14
        )
        return ReplyScore(
            candidate=candidate,
            naturalness=naturalness,
            wechat_feel=wechat_feel,
            risk_control=risk_control,
            emotional_value=emotional_value,
            relationship_progress=relationship_progress,
            total_score=self._clamp(total),
            reason="weighted_quality_score",
        )

    def _risk_control(self, text: str, risk: RiskReport) -> float:
        """Score whether reply avoids unsafe pressure."""
        score = 90
        score -= sum(18 for word in self.RISKY_WORDS if word in text)
        if risk.risk_level != "low" and any(word in text for word in ("暧昧", "喜欢你", "约会")):
            score -= 35
        if risk.risk_level != "low" and any(word in text for word in ("我在", "听你", "慢慢")):
            score += 8
        return self._clamp(score)

    def _relationship_progress(self, text: str, relationship_state: Mapping[str, Any]) -> float:
        """Score stage-appropriate relationship progress."""
        stage = str(relationship_state.get("stage", "L1"))
        progress_hits = sum(8 for word in self.PUSH_WORDS if word in text)
        base = 50 + progress_hits
        if stage in {"L1", "L2"} and progress_hits > 16:
            base -= 20
        if stage in {"L4", "L5", "L6"} and progress_hits:
            base += 12
        return self._clamp(base)

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp score into 0-100."""
        return max(0.0, min(100.0, float(value)))


def _demo() -> None:
    """Run a small module smoke test."""
    best = ReplyRanker().rank([ReplyCandidate(text="我在，你慢慢说")], RiskReport(), {"stage": "L1"})
    print(best.model_dump())


if __name__ == "__main__":
    _demo()
