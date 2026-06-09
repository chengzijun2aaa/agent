from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.generator.reply_generator import ReplyCandidate


class ReplyScore(BaseModel):
    """增强版评分数据模型"""
    model_config = ConfigDict(extra="ignore")

    candidate: ReplyCandidate
    naturalness: float = Field(ge=0.0, le=100.0)      # 真实男性感
    wechat_feel: float = Field(ge=0.0, le=100.0)     # 微信自然度
    no_simping: float = Field(ge=0.0, le=100.0)      # 不讨好 / 不舔
    no_greasy: float = Field(ge=0.0, le=100.0)       # 不油腻
    information_entropy: float = Field(default=0.0, ge=0.0, le=100.0)  # 短句信息量
    advance_speed: float = Field(ge=0.0, le=100.0)   # 推进节奏是否合适
    pressure: float = Field(ge=0.0, le=100.0)        # 压迫感（独立作为减分惩罚项）
    emotional_value: float = Field(default=0.0, ge=0.0, le=100.0)
    profile_fit: float = Field(default=0.0, ge=0.0, le=100.0)
    total_score: float = Field(ge=0.0, le=100.0)
    reason: str = ""


class ReplyRanker:
    """Rank replies by naturalness, usefulness, comfort, and pacing."""

    # 1. 抽离权重配置，方便后续热更新或微调
    WEIGHTS = {
        "naturalness": 0.18,
        "wechat_feel": 0.14,
        "information_entropy": 0.18,
        "no_simping": 0.18,
        "no_greasy": 0.15,
        "advance_speed": 0.10,
        "emotional_value": 0.05,
        "profile_fit": 0.04,
        "pressure_penalty": 0.15,
    }

    PERSONALITY_MATRICES = {
        "boundary_sensitive": {
            "naturalness": 0.17,
            "wechat_feel": 0.14,
            "information_entropy": 0.16,
            "no_simping": 0.16,
            "no_greasy": 0.14,
            "advance_speed": 0.08,
            "emotional_value": 0.05,
            "profile_fit": 0.05,
            "pressure_penalty": 0.24,
        },
        "reassurance_need": {
            "naturalness": 0.16,
            "wechat_feel": 0.12,
            "information_entropy": 0.16,
            "no_simping": 0.14,
            "no_greasy": 0.13,
            "advance_speed": 0.08,
            "emotional_value": 0.14,
            "profile_fit": 0.05,
            "pressure_penalty": 0.18,
        },
        "playful": {
            "naturalness": 0.20,
            "wechat_feel": 0.16,
            "information_entropy": 0.18,
            "no_simping": 0.16,
            "no_greasy": 0.15,
            "advance_speed": 0.10,
            "emotional_value": 0.05,
            "profile_fit": 0.05,
            "pressure_penalty": 0.14,
        },
        "clear": {
            "naturalness": 0.18,
            "wechat_feel": 0.13,
            "information_entropy": 0.17,
            "no_simping": 0.16,
            "no_greasy": 0.14,
            "advance_speed": 0.14,
            "emotional_value": 0.05,
            "profile_fit": 0.05,
            "pressure_penalty": 0.16,
        },
    }

    # 2. 原始词库定义
    GREASY_WORDS = ("宝贝", "亲爱的", "小仙女", "女神", "心肝", "老婆", "老公", "么么", "啵啵", "想死你了", "心动")
    SIMP_PHRASES = ("我都听你的", "你说怎样就怎样", "只要你开心", "我无条件", "我全都给你", "随便你", "都听你", "你开心就好")
    PRESSURE_WORDS = ("必须", "赶紧", "别矫情", "你应该", "听话", "现在就要", "不许", "快点", "别临时怂", "现在就")
    TOO_FAST_WORDS = ("爱你", "在一起", "做我女朋友", "今晚来我家", "想睡你", "过夜", "去开房")
    FRIEND_ZONE_PHRASES = ("我听着", "你继续说", "慢慢说", "然后呢", "展开讲讲")
    PROGRESSION_PHRASES = ("见面", "周末", "我带你", "我来安排", "定一个", "回头", "下次", "记着", "靠我")
    INVITE_PHRASES = ("见面", "出来", "出门", "周末", "周六", "周日", "有空", "一起", "吃饭", "电影", "咖啡", "喝一杯", "我带你", "我来安排", "定一个")
    EMOTION_PULL_PHRASES = ("有点", "可爱", "记你", "别只", "继续", "惦记", "先收下", "站你这边")
    EXPLICIT_INVITE_SIGNALS = ("见面", "见一下", "周末", "周六", "周日", "有空", "一起", "吃饭", "出来", "电影", "咖啡", "喝一杯", "找天", "约")
    LEADERSHIP_PHRASES = ("我来安排", "我带你", "你定时间", "定一个", "我陪你捋", "交交给", "我站你这边")
    REASSURANCE_PHRASES = ("放心", "我在", "站你这边", "别自己扛", "先缓", "先喘口气", "哄你")
    PLAYFUL_PHRASES = ("有点", "可爱", "酸", "查我岗", "记你一笔", "别光", "你猜")
    LOW_PRESSURE_PHRASES = ("不赶", "慢慢来", "轻松点", "你舒服", "先", "可以")
    
    # 针对高边界感女生的特定高危词
    HIGH_BOUNDARY_RISK = ("别临时怂", "必须", "赶紧", "今晚", "过夜")

    def __init__(self) -> None:
        # 3. 初始化时预编译正则表达式，将 O(N) 循环匹配转化为高效的正则匹配
        self._regex_greasy = re.compile("|".join(map(re.escape, self.GREASY_WORDS)))
        self._regex_simp = re.compile("|".join(map(re.escape, self.SIMP_PHRASES)))
        self._regex_simp_extra = re.compile("都听你的|只要你|我全都|随便你|你开心就好")
        self._regex_pressure = re.compile("|".join(map(re.escape, self.PRESSURE_WORDS)))
        self._regex_high_boundary = re.compile("|".join(map(re.escape, self.HIGH_BOUNDARY_RISK)))
        self._regex_low_pressure = re.compile("|".join(map(re.escape, self.LOW_PRESSURE_PHRASES)))

    def rank(
        self,
        candidates: Sequence[ReplyCandidate],
        *args: Any,
        relationship_state: Mapping[str, Any] | None = None,
        chat_history: Any = None,
        memory: Mapping[str, Any] | None = None,
    ) -> ReplyScore:
        """兼容新旧调用风格的入口"""
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
        information_entropy = self._information_entropy_score(text, chat_history)
        advance_speed = self._advance_speed_score(text, relationship_state, profile, chat_history)
        pressure = self._pressure_score(text, profile)
        emotional_value = self._emotional_value_score(text, chat_history)
        profile_fit = self._profile_fit_score(text, profile)

        # 4. 采用动态权重池计算，结构更清晰
        w = self._weights_for_profile(profile)
        total = (
            naturalness * w["naturalness"] +
            wechat_feel * w["wechat_feel"] +
            information_entropy * w["information_entropy"] +
            no_simping * w["no_simping"] +
            no_greasy * w["no_greasy"] +
            advance_speed * w["advance_speed"] +
            emotional_value * w["emotional_value"] +
            profile_fit * w["profile_fit"] -
            (pressure * w["pressure_penalty"])  # 强压迫感作为纯扣分项
        )
        if information_entropy < 25:
            total -= 18.0
        if naturalness < 50 and information_entropy < 40:
            total -= 12.0

        reason = (
            f"nat={naturalness:.1f} | wx={wechat_feel:.1f} | info={information_entropy:.1f} | nosimp={no_simping:.1f} "
            f"| nogreasy={no_greasy:.1f} | advance={advance_speed:.1f} | press_penalty=-{pressure * w['pressure_penalty']:.1f}"
        )

        return ReplyScore(
            candidate=candidate,
            naturalness=naturalness,
            wechat_feel=wechat_feel,
            no_simping=no_simping,
            no_greasy=no_greasy,
            information_entropy=information_entropy,
            advance_speed=advance_speed,
            pressure=pressure,
            emotional_value=emotional_value,
            profile_fit=profile_fit,
            total_score=max(0.0, min(100.0, total)),
            reason=reason,
        )

    def _natural_male_score(self, text: str) -> float:
        """Natural short-message tone without rewarding empty replies."""
        score = 85.0
        length = len(text)

        if length < 3:
            score -= 30.0
        if length > 40:
            score -= 20.0
        if text in ("行吧", "好吧", "不知道", "哈哈哈", "我都行", "嗯", "哦", "行", "好", "收到"):
            score -= 25.0
        if "哈哈哈" in text or "哈组合" in text or "对对对" in text:
            score -= 10.0
        
        # 语气词合理加分
        tokens = ("…", "嗯", "哈", "行", "噢")
        bonus = sum(4.0 for t in tokens if t in text)
        return max(10.0, min(100.0, score + min(8.0, bonus)))

    def _wechat_feel_score(self, text: str, length: int) -> float:
        """微信原生没有密集标点"""
        score = 85.0
        if 4 <= length <= 25:
            score += 10.0
        
        punc_count = text.count("，") + text.count("。") + text.count("！")
        if punc_count > 2:
            score -= (punc_count * 6.0)
            
        return max(30.0, min(100.0, score))

    def _information_entropy_score(self, text: str, chat_history: Any) -> float:
        """Reward short replies that still carry attitude, callback, or emotion."""
        compact = re.sub(r"\s+", "", text)
        latest = self._latest_text(chat_history)
        score = 62.0

        if len(compact) < 3:
            score -= 45.0
        if compact in {"嗯", "哦", "好", "行", "收到", "哈哈", "呵呵", "还好吧", "不知道", "随便"}:
            score -= 45.0
        if compact in {"嗯呢", "好滴", "行吧", "好吧"}:
            score -= 28.0

        attitude_markers = (
            "先", "别", "可以", "放心", "站你", "听着", "接住", "有点", "可爱",
            "酸", "记你", "继续", "怎么说", "哪天", "时间", "地方", "舒服", "不急"
        )
        if any(marker in text for marker in attitude_markers):
            score += 22.0

        latest_keywords = [
            word
            for word in ("累", "烦", "猫", "狗", "周末", "见面", "吃饭", "想你", "抱抱", "压力", "酸", "忙")
            if word in latest
        ]
        if latest_keywords and any(word in text for word in latest_keywords):
            score += 16.0

        if 4 <= len(compact) <= 18:
            score += 10.0
        if len(set(compact)) <= 2 and len(compact) >= 3:
            score -= 18.0

        return max(0.0, min(100.0, score))

    def _no_simping_score(self, text: str) -> float:
        """不舔狗框架 - 使用预编译正则大幅提升检索速度"""
        score = 100.0
        if self._regex_simp.search(text):
            score -= 45.0
        if self._regex_simp_extra.search(text):
            score -= 35.0
        return max(10.0, min(100.0, score))

    def _no_greasy_score(self, text: str) -> float:
        """杜绝刻板油腻称呼"""
        score = 100.0
        if self._regex_greasy.search(text):
            score -= 50.0
        return max(20.0, min(100.0, score))

    def _advance_speed_score(
        self,
        text: str,
        state: Mapping[str, Any],
        profile: Mapping[str, Any],
        chat_history: Any = None,
    ) -> float:
        """推进节奏判定"""
        stage = str(state.get("stage", state.get("relationship_stage", "L1")))
        score = 80.0
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        favorability = float(state.get("favorability_score", state.get("favorability", 0)) or 0)
        
        early_stage = stage in ("L1", "L2") or favorability < 35
        latest = self._latest_text(chat_history)
        explicit_invite_signal = any(w in latest for w in self.EXPLICIT_INVITE_SIGNALS)
        
        # 早期未释放信号盲目邀约
        if early_stage and not explicit_invite_signal and any(w in text for w in self.INVITE_PHRASES):
            score -= 40.0
        if any(w in text for w in self.TOO_FAST_WORDS):
            score -= 45.0
        if any(w in text for w in self.PROGRESSION_PHRASES):
            score += 15.0 if stage in ("L3", "L4", "L5", "L6") else -15.0
            if boundary >= 70:
                score -= 15.0
        if early_stage and any(w in text for w in self.EMOTION_PULL_PHRASES):
            score += 12.0
        if stage in ("L1", "L2") and any(w in text for w in self.FRIEND_ZONE_PHRASES):
            score -= 10.0
            
        return max(20.0, min(100.0, score))

    def _pressure_score(self, text: str, profile: Mapping[str, Any] | None = None) -> float:
        """计算强势压迫感（返回的分数越高，最后扣分越多）"""
        score = 0.0
        profile = profile or {}
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        
        # 利用正则查找压迫性词汇个数
        matches = self._regex_pressure.findall(text)
        score += len(matches) * 35.0
        
        # 针对高边界敏感女生的阶梯惩罚
        if boundary >= 70:
            if self._regex_high_boundary.search(text):
                score += 30.0
            if self._regex_low_pressure.search(text):
                score -= 15.0  # 具备降压属性可以相互抵消
                
        return max(0.0, min(100.0, score))

    def _emotional_value_score(self, text: str, chat_history: Any) -> float:
        """情绪稳定器"""
        latest = self._latest_text(chat_history)
        score = 70.0
        emotional_context = any(
            word in latest
            for word in ("累", "难受", "委屈", "压力", "烦", "想哭", "吃醋", "想你", "抱抱", "哄我")
        )
        if emotional_context:
            if any(word in text for word in self.REASSURANCE_PHRASES):
                score += 20.0
            if any(word in text for word in ("然后呢", "展开讲讲", "嗯？", "怎么了")):
                score -= 10.0
        return max(0.0, min(100.0, score))

    def _profile_fit_score(self, text: str, profile: Mapping[str, Any]) -> float:
        """契合女方人设偏好"""
        if not profile:
            return 70.0
        score = 70.0
        leadership = float(profile.get("leadership_preference", 50) or 50)
        reassurance = float(profile.get("reassurance_need", 50) or 50)
        playfulness = float(profile.get("playfulness", 50) or 50)
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)

        if leadership >= 65 and any(word in text for word in self.LEADERSHIP_PHRASES):
            score += 15.0
        if reassurance >= 65 and any(word in text for word in self.REASSURANCE_PHRASES):
            score += 12.0
        if playfulness >= 65 and any(word in text for word in self.PLAYFUL_PHRASES):
            score += 12.0
        if boundary >= 70:
            if self._regex_low_pressure.search(text):
                score += 10.0
            if self._regex_high_boundary.search(text):
                score -= 30.0
        return max(0.0, min(100.0, score))

    def _weights_for_profile(self, profile: Mapping[str, Any]) -> Mapping[str, float]:
        """Select a scoring matrix from the current dynamic profile."""
        if not profile:
            return self.WEIGHTS
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        reassurance = float(profile.get("reassurance_need", 50) or 50)
        playfulness = float(profile.get("playfulness", 50) or 50)
        leadership = float(profile.get("leadership_preference", 50) or 50)
        if boundary >= 70:
            return self.PERSONALITY_MATRICES["boundary_sensitive"]
        if reassurance >= 68:
            return self.PERSONALITY_MATRICES["reassurance_need"]
        if playfulness >= 65:
            return self.PERSONALITY_MATRICES["playful"]
        if leadership >= 65:
            return self.PERSONALITY_MATRICES["clear"]
        return self.WEIGHTS

    @staticmethod
    def _profile(memory: Mapping[str, Any] | None) -> dict[str, Any]:
        if not isinstance(memory, Mapping):
            return {}
        profile = memory.get("profile", {})
        return dict(profile) if isinstance(profile, Mapping) else {}

    @staticmethod
    def _latest_text(chat_history: Any) -> str:
        """扁平化重构的多类型兼容解析器"""
        if not chat_history:
            return ""
        if isinstance(chat_history, str):
            return chat_history.lower()
            
        try:
            # 统一转成列表逆序查找
            for item in reversed(list(chat_history)):
                if isinstance(item, str):
                    return item.lower()
                
                role, content = "", ""
                # 优雅抽取属性或字典
                if hasattr(item, "role") and hasattr(item, "content"):
                    role = str(getattr(item, "role", "user")).lower()
                    content = str(getattr(item, "content", "")).lower()
                elif isinstance(item, Mapping):
                    role = str(item.get("role", "user")).lower()
                    content = str(item.get("content", item.get("text", ""))).lower()
                
                # 过滤男方或系统侧，精准锁定女方上一句原始锚点
                if role and role not in {"assistant", "me", "boy", "我", "user_confirmed"}:
                    return content
        except Exception:
            return ""
        return ""


def _demo() -> None:
    ranker = ReplyRanker()
    best = ranker.rank([
        ReplyCandidate(text="先缓一口气，别自己扛，晚上带你吃点好吃的。"),
        ReplyCandidate(text="你赶紧跟我说，必须听我的现在就出来见面！"), 
        ReplyCandidate(text="宝贝我都听你的，只要你开心我无条件答应你一切要求。"), 
    ])
    print(best.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
