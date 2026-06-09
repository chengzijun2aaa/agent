"""Risk detector for conversational pacing and boundary control."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence, TypeAlias
from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.utils.types import Message, SenderRole

ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message"


class RiskReport(BaseModel):
    """Risk report used by strategy planning."""

    model_config = ConfigDict(extra="ignore")

    risk_level: str = Field(default="low")  # low/medium/high progression caution
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    strategy_instruction: str = ""
    vulnerability: int = Field(default=0, ge=0, le=100)
    sexual_openness: int = Field(default=0, ge=0, le=100)
    compliance: int = Field(default=0, ge=0, le=100)
    escalation_potential: int = Field(default=0, ge=0, le=100)
    boundary_sensitivity: int = Field(default=50, ge=0, le=100)


class ConquestOpportunityDetector:
    """Detect boundary risk and low-pressure interaction opportunities."""

    VULNERABILITY_KEYWORDS = ("难受", "想哭", "委屈", "累", "压力", "没人懂", "崩溃", "emo", "孤独", "空虚")
    CLOSENESS_SIGNALS = ("想你", "抱抱", "晚安呀", "贴贴", "亲亲", "想见你")
    ENGAGEMENT_SIGNALS = ("跟你说", "想跟你说", "好呀", "可以呀", "嗯嗯", "你觉得", "一起")
    RESONANCE_SIGNALS = ("想见你", "一起", "见面", "周末", "有空", "聊得来")
    BOUNDARY_SIGNALS = (
        "有点压力", "太快", "不舒服", "先别", "别这样", "保持距离", "慢一点",
        "最近没空", "不想说", "换个话题", "别聊这个", "算了"
    )

    def detect(
        self,
        chat_history: Sequence[ChatHistoryItem],
        profile: Mapping[str, Any] | None = None,
    ) -> RiskReport:
        if not chat_history:
            return RiskReport()

        # 初始化四维核心矩阵的加权总分
        raw_vuln, raw_close, raw_engage, raw_resonance, raw_boundary = 0.0, 0.0, 0.0, 0.0, 0.0
        all_hits: list[str] = []

        # 深度重构 1：时间衰减与角色隔离
        # 倒序遍历聊天记录，越接近当前的对话权重越高；同时使用严格衰减系数
        reversed_history = list(reversed(chat_history))
        
        for turn_idx, item in enumerate(reversed_history):
            role = self._resolve_role(item)
            # 只分析对方释放的实时信号，避免把自己的话当成对方反馈。
            if role == "me":
                continue

            text = self._content(item).lower()
            if not text:
                continue

            # 计算当前轮次的时间衰减系数 (第0轮即最新一轮权重为 1.0，之后呈指数衰减)
            time_decay = math.exp(-0.4 * turn_idx)
            if time_decay < 0.15:  # 过于久远的历史直接截断，不干扰当下决策
                break

            # 提取当前单轮命中的关键词（去重，防止单句内刷词作弊）
            vuln_hits = set(k for k in self.VULNERABILITY_KEYWORDS if k in text)
            close_hits = set(k for k in self.CLOSENESS_SIGNALS if k in text)
            engage_hits = set(k for k in self.ENGAGEMENT_SIGNALS if k in text)
            resonance_hits = set(k for k in self.RESONANCE_SIGNALS if k in text)
            boundary_hits = set(k for k in self.BOUNDARY_SIGNALS if k in text)

            # 动态收集触发原因，用于 Planner 日志审计
            all_hits.extend(list(vuln_hits | close_hits | engage_hits | resonance_hits | boundary_hits))

            # 深度重构 2：平滑加权算法，单轮命中多个同类词时收益递减（使用饱阶对数平滑）
            raw_vuln += (len(vuln_hits) * 30 if len(vuln_hits) <= 1 else 30 + (len(vuln_hits) - 1) * 10) * time_decay
            raw_close += (len(close_hits) * 30 if len(close_hits) <= 1 else 30 + (len(close_hits) - 1) * 10) * time_decay
            raw_engage += (len(engage_hits) * 25 if len(engage_hits) <= 1 else 25 + (len(engage_hits) - 1) * 10) * time_decay
            raw_resonance += (len(resonance_hits) * 35 if len(resonance_hits) <= 1 else 35 + (len(resonance_hits) - 1) * 12) * time_decay
            raw_boundary += (len(boundary_hits) * 45 if len(boundary_hits) <= 1 else 45 + (len(boundary_hits) - 1) * 18) * time_decay

        # 归一化限制在 [0, 100] 区间内
        vulnerability = min(int(raw_vuln), 100)
        sexual_openness = min(int(raw_close), 100)
        compliance = min(int(raw_engage), 100)
        inferred_boundary = min(int(50 + raw_boundary), 100)
        profile_boundary = self._profile_boundary_sensitivity(profile)
        boundary_sensitivity = max(inferred_boundary, profile_boundary)
        
        # 共鸣契机来自明确互动、亲近表达和对方主动释放的见面/话题窗口。
        # 脆弱度高时应该倾向于提供安全舒适感，而非直接推进。
        base_escalation = raw_resonance + (raw_close * 0.35) + (raw_engage * 0.35)
        if vulnerability >= 70:
            base_escalation *= 0.5
        escalation = min(int(base_escalation), 100)

        if boundary_sensitivity >= 70:
            level = "high"
            instruction = "BACK_OFF: 对方表现出回避情绪，接下来的回复必须完全顺从、退回安全社交距离，不提任何要求。"
            blocked = True
        elif escalation >= 70 or sexual_openness >= 75:
            level = "high"
            instruction = "对方互动窗口较明显。可以保持轻松、低压力地回应，不要突然加速。"
            blocked = False
        elif vulnerability >= 65:
            level = "medium"
            instruction = "对方处于情绪脆弱期。先接住情绪，少讲道理，不提要求，提供安全舒适感。"
            blocked = False
        elif compliance >= 50 or sexual_openness >= 45:
            level = "medium"
            instruction = "对方互动意愿良好。适合轻松接话，加入一点具体回应或轻微调侃。"
            blocked = False
        else:
            level = "low"
            instruction = "常规互动状态。保持轻松接话，不连续追问，不急着推进。"
            blocked = False

        return RiskReport(
            risk_level=level,
            blocked=blocked,
            reasons=self._dedupe(all_hits),
            strategy_instruction=instruction,
            vulnerability=vulnerability,
            sexual_openness=sexual_openness,
            compliance=compliance,
            escalation_potential=escalation,
            boundary_sensitivity=boundary_sensitivity,
        )

    @staticmethod
    def _content(item: ChatHistoryItem) -> str:
        if isinstance(item, Message):
            return item.content
        if isinstance(item, str):
            return item
        return str(item.get("content", item.get("text", item.get("message", ""))))

    @staticmethod
    def _resolve_role(item: ChatHistoryItem) -> str:
        """识别发送方身份，严防男方自我对话指标污染"""
        if isinstance(item, Message):
            role_str = str(item.role)
        elif isinstance(item, Mapping):
            role_str = str(item.get("role", item.get("sender", "user")))
        else:
            return "user"  # 纯字符串默认当成女方发的信息处理
            
        if role_str in {"assistant", "me", "boy", "sender_me"}:
            return "me"
        return "user"

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for v in values:
            if v and v not in seen:
                seen.add(v)
                result.append(v)
        return result

    @staticmethod
    def _profile_boundary_sensitivity(profile: Mapping[str, Any] | None) -> int:
        if not isinstance(profile, Mapping):
            return 50
        raw_profile = profile.get("profile", profile)
        if not isinstance(raw_profile, Mapping):
            return 50
        try:
            return int(raw_profile.get("boundary_sensitivity", 50) or 50)
        except (TypeError, ValueError):
            return 50


# 兼容老版接口
RiskDetector = ConquestOpportunityDetector


def _demo() -> None:
    """运行复杂的时序与多角色混合测试"""
    detector = RiskDetector()
    
    # 模拟真实聊天流：前两轮女生疯狂倒苦水，但最后一轮已经被男方安抚好，回了一句带有轻微顺从和试探的“好吧”
    test_history = [
        {"role": "user", "content": "今天在公司受委屈了，压力大得想哭，真的快崩溃了"},
        {"role": "assistant", "content": "先把最烦的那段丢给我，我替你接着。"},
        {"role": "user", "content": "好吧 听你的 🌝"}
    ]
    
    report = detector.detect(test_history)
    print("重构后的风险检测报告：")
    import json
    print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _demo()
