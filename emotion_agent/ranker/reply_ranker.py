"""Reply Ranker - 升级版真实男性回复评分器"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.generator.reply_generator import ReplyCandidate


class ReplyScore(BaseModel):
    """增强版评分"""
    model_config = ConfigDict(extra="ignore")

    candidate: ReplyCandidate
    naturalness: float = Field(ge=0.0, le=100.0)      # 真实男性感
    wechat_feel: float = Field(ge=0.0, le=100.0)     # 微信自然度
    no_simping: float = Field(ge=0.0, le=100.0)      # 不讨好 / 不舔
    no_greasy: float = Field(ge=0.0, le=100.0)       # 不油腻
    advance_speed: float = Field(ge=0.0, le=100.0)   # 推进是否合适
    pressure: float = Field(ge=0.0, le=100.0)        # 压迫感（越低越好）
    emotional_value: float = Field(default=0.0, ge=0.0, le=100.0)
    profile_fit: float = Field(default=0.0, ge=0.0, le=100.0)
    total_score: float = Field(ge=0.0, le=100.0)
    reason: str = ""


class ReplyRanker:
    """真实男性回复排序器"""

    GREASY_WORDS = ("宝贝", "亲爱的", "小仙女", "女神", "心肝", "老婆", "老公", "么么", "啵啵", "想死你了")
    SIMP_PHRASES = ("我都听你的", "你说怎样就怎样", "只要你开心", "我无条件", "我全都给你")
    PRESSURE_WORDS = ("必须", "赶紧", "别矫情", "你应该", "听话", "现在就要", "不许", "快点", "别临时怂")
    TOO_FAST_WORDS = ("爱你", "在一起", "做我女朋友", "今晚来我家", "想睡你", "过夜")
    FRIEND_ZONE_PHRASES = ("我听着", "你继续说", "慢慢说", "然后呢", "展开讲讲")
    PROGRESSION_PHRASES = ("见面", "周末", "我带你", "我来安排", "定一个", "回头", "下次", "记着", "靠我")
    INVITE_PHRASES = ("见面", "出来", "出门", "周末", "周六", "周日", "有空", "一起", "吃饭", "电影", "咖啡", "喝一杯", "我带你", "我来安排", "定一个")
    EMOTION_PULL_PHRASES = ("有点", "可爱", "记你", "别只", "继续", "我听着", "惦记", "先收下", "站你这边")
    EXPLICIT_INVITE_SIGNALS = ("见面", "见一下", "周末", "周六", "周日", "有空", "一起", "吃饭", "出来", "电影", "咖啡", "喝一杯", "找天", "约")
    LEADERSHIP_PHRASES = ("我来安排", "我带你", "你定时间", "定一个", "我陪你捋", "交给我", "我站你这边")
    REASSURANCE_PHRASES = ("放心", "我在", "站你这边", "别自己扛", "先缓", "先喘口气", "哄你")
    PLAYFUL_PHRASES = ("有点", "可爱", "酸", "查我岗", "记你一笔", "别光", "你猜")
    LOW_PRESSURE_PHRASES = ("不赶", "慢慢来", "轻松点", "你舒服", "先", "可以")

    def rank(
        self,
        candidates: Sequence[ReplyCandidate],
        *args: Any,
        relationship_state: Mapping[str, Any] | None = None,
        chat_history: Any = None,
        memory: Mapping[str, Any] | None = None,
    ) -> ReplyScore:
        """Rank candidates while accepting both old and new call styles."""
        if args:
            if len(args) >= 3:
                relationship_state = args[1] if isinstance(args[1], Mapping) else relationship_state
                chat_history = args[2]
                if len(args) >= 4 and isinstance(args[3], Mapping):
                    memory = args[3]
            elif len(args) >= 1 and isinstance(args[0], Mapping):
                relationship_state = args[0]
                if len(args) >= 2:
                    chat_history = args[1]
                if len(args) >= 3 and isinstance(args[2], Mapping):
                    memory = args[2]
            elif len(args) >= 2:
                chat_history = args[1]
                if len(args) >= 3 and isinstance(args[2], Mapping):
                    memory = args[2]

        if not candidates:
            fallback = ReplyCandidate(text="嗯？")
            return self.score(fallback, relationship_state or {}, chat_history or [], memory=memory)
        
        scores = [self.score(c, relationship_state or {}, chat_history or [], memory=memory) for c in candidates]
        return max(scores, key=lambda s: s.total_score)

    def score(
        self,
        candidate: ReplyCandidate,
        relationship_state: Mapping[str, Any],
        chat_history: Any,
        *,
        memory: Mapping[str, Any] | None = None,
    ) -> ReplyScore:
        text = candidate.text.strip().lower()
        length = len(text)
        profile = self._profile(memory)

        naturalness = self._natural_male_score(text)
        wechat_feel = self._wechat_feel_score(text, length)
        no_simping = self._no_simping_score(text)
        no_greasy = self._no_greasy_score(text)
        advance_speed = self._advance_speed_score(text, relationship_state, profile, chat_history)
        pressure = self._pressure_score(text, profile)
        emotional_value = self._emotional_value_score(text, chat_history)
        profile_fit = self._profile_fit_score(text, profile)

        total = (
            naturalness * 0.20 +
            wechat_feel * 0.16 +
            no_simping * 0.16 +
            no_greasy * 0.13 +
            advance_speed * 0.14 +
            pressure * 0.09 +
            emotional_value * 0.06 +
            profile_fit * 0.06
        )

        reason = (
            f"nat={naturalness:.1f} | wx={wechat_feel:.1f} | advance={advance_speed:.1f} "
            f"| press={pressure:.1f} | profile={profile_fit:.1f}"
        )

        return ReplyScore(
            candidate=candidate,
            naturalness=naturalness,
            wechat_feel=wechat_feel,
            no_simping=no_simping,
            no_greasy=no_greasy,
            advance_speed=advance_speed,
            pressure=pressure,
            emotional_value=emotional_value,
            profile_fit=profile_fit,
            total_score=max(0.0, min(100.0, total)),
            reason=reason,
        )

    def _natural_male_score(self, text: str) -> float:
        """是否像真实男生"""
        score = 75
        if len(text) > 45: 
            score -= 18
        if any(p in text for p in ["哈哈哈", "哈哈哈哈", "对对对"]):
            score -= 12
        if "…" in text or "嗯" in text or "哈" in text:
            score += 12
        return max(30, min(100, score))

    def _wechat_feel_score(self, text: str, length: int) -> float:
        """微信自然度"""
        score = 80
        if 6 <= length <= 32:
            score += 12
        if text.count("，") > 3 or text.count("。") > 2:
            score -= 15
        return max(40, min(100, score))

    def _no_simping_score(self, text: str) -> float:
        """不舔狗"""
        score = 85
        for phrase in self.SIMP_PHRASES:
            if phrase in text:
                score -= 35
        if "都听你的" in text or "只要你" in text:
            score -= 25
        return max(20, min(100, score))

    def _no_greasy_score(self, text: str) -> float:
        """不油腻"""
        score = 88
        for w in self.GREASY_WORDS:
            if w in text:
                score -= 40
        if "心动" in text or "女神" in text or "宝贝" in text:
            score -= 30
        return max(25, min(100, score))

    def _advance_speed_score(
        self,
        text: str,
        state: Mapping[str, Any],
        profile: Mapping[str, Any],
        chat_history: Any = None,
    ) -> float:
        """推进速度是否合适"""
        stage = str(state.get("stage", "L1"))
        score = 78
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        pace = float(profile.get("progression_pace", 1.0) or 1.0)
        favorability = float(state.get("favorability_score", 0) or 0)
        early_stage = stage in ("L1", "L2") or favorability < 35
        latest = self._latest_text(chat_history)
        explicit_invite_signal = any(w in latest for w in self.EXPLICIT_INVITE_SIGNALS)
        has_invite = any(w in text for w in self.INVITE_PHRASES)
        
        if stage in ("L1", "L2") and any(w in text for w in self.TOO_FAST_WORDS):
            score -= 45
        if any(w in text for w in self.TOO_FAST_WORDS) and "见面" not in text:
            score -= 20
        if has_invite and early_stage and not explicit_invite_signal:
            score -= 28
        elif any(w in text for w in self.PROGRESSION_PHRASES):
            score += 16 if stage in ("L3", "L4", "L5", "L6") else 4
            if boundary >= 70 or pace <= 0.85:
                score -= 8
        if early_stage and not explicit_invite_signal and any(w in text for w in self.EMOTION_PULL_PHRASES):
            score += 10
        if any(w in text for w in self.FRIEND_ZONE_PHRASES):
            score -= 6 if early_stage else 14
            
        return max(30, min(100, score))

    def _pressure_score(self, text: str, profile: Mapping[str, Any] | None = None) -> float:
        """压迫感控制"""
        score = 85
        profile = profile or {}
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        for w in self.PRESSURE_WORDS:
            if w in text:
                score -= 30
        if "必须" in text or "赶紧" in text or "现在就" in text:
            score -= 25
        if boundary >= 70 and any(w in text for w in ("别临时怂", "别光说", "当面说", "跟我算")):
            score -= 18
        if boundary >= 70 and any(w in text for w in self.LOW_PRESSURE_PHRASES):
            score += 8
        return max(20, min(100, score))

    def _emotional_value_score(self, text: str, chat_history: Any) -> float:
        """Score whether the reply acknowledges the current emotional context."""
        latest = self._latest_text(chat_history)
        score = 72
        emotional_context = any(
            word in latest
            for word in ("累", "难受", "委屈", "压力", "烦", "想哭", "吃醋", "想你", "抱抱", "哄我")
        )
        if emotional_context and any(word in text for word in self.REASSURANCE_PHRASES):
            score += 18
        if emotional_context and any(word in text for word in ("然后呢", "展开讲讲", "嗯？")):
            score -= 18
        if any(word in latest for word in ("见面", "一起", "周末", "有空")) and any(
            word in text for word in ("可以", "行", "定", "安排")
        ):
            score += 12
        return self._clamp(score)

    def _profile_fit_score(self, text: str, profile: Mapping[str, Any]) -> float:
        """Score how well a reply fits the learned per-person profile."""
        if not profile:
            return 70
        score = 72
        leadership = float(profile.get("leadership_preference", 50) or 50)
        reassurance = float(profile.get("reassurance_need", 50) or 50)
        playfulness = float(profile.get("playfulness", 50) or 50)
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)

        if leadership >= 65:
            score += 14 if any(word in text for word in self.LEADERSHIP_PHRASES) else -6
        if reassurance >= 65:
            score += 12 if any(word in text for word in self.REASSURANCE_PHRASES) else -6
        if playfulness >= 65:
            score += 10 if any(word in text for word in self.PLAYFUL_PHRASES) else 0
        if boundary >= 70:
            if any(word in text for word in self.LOW_PRESSURE_PHRASES):
                score += 12
            if any(word in text for word in ("别临时怂", "必须", "赶紧", "今晚", "过夜")):
                score -= 25
        try:
            favorability = float(profile.get("favorability_score", 0) or 0)
        except (TypeError, ValueError):
            favorability = 0
        if favorability < 35 and any(word in text for word in self.INVITE_PHRASES):
            score -= 8
        return self._clamp(score)

    @staticmethod
    def _profile(memory: Mapping[str, Any] | None) -> dict[str, Any]:
        """Read profile data from memory for rank-time personalization."""
        if not isinstance(memory, Mapping):
            return {}
        profile = memory.get("profile", {})
        return dict(profile) if isinstance(profile, Mapping) else {}

    @staticmethod
    def _latest_text(chat_history: Any) -> str:
        """Return the latest user-side text from a mixed history."""
        if not chat_history:
            return ""
        try:
            items = list(chat_history)
        except TypeError:
            return str(chat_history).lower()
        for item in reversed(items):
            if isinstance(item, str):
                return item.lower()
            if isinstance(item, Mapping):
                role = str(item.get("role", "user")).lower()
                if role not in {"assistant", "me", "boy", "我"}:
                    return str(item.get("content", item.get("text", ""))).lower()
        return ""

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, float(value)))


def _demo() -> None:
    ranker = ReplyRanker()
    best = ranker.rank([
        ReplyCandidate(text="过来，我抱抱你"),
        ReplyCandidate(text="我理解你的情绪，先缓一口气，我会一直陪着你哦宝贝"),
        ReplyCandidate(text="嗯，你继续说"),
    ])
    print(best.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
