"""Risk detector for romantic progression and boundary control - Refactored Version"""

from __future__ import annotations

import math
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
    """Detect romantic progression risk and windows based on strict female sub-signals."""

    VULNERABILITY_KEYWORDS = ("难受", "想哭", "委屈", "累", "压力", "没人懂", "崩溃", "emo", "孤独", "空虚")
    SEXUAL_SIGNALS = ("想你", "抱抱", "晚安", "睡觉", "洗澡", "穿什么", "好热", "无聊", "坏", "色", "讨厌你")
    COMPLIANCE_SIGNALS = ("听你的", "好吧", "嗯嗯", "你说", "随便你", "看你", "都可以")
    HIGH_ESCALATION = ("想见你", "一起", "见面", "来我家", "你好坏", "讨厌", "哼")

    def detect(self, chat_history: Sequence[ChatHistoryItem]) -> RiskReport:
        if not chat_history:
            return RiskReport()

        # 初始化四维核心矩阵的加权总分
        raw_vuln, raw_sex, raw_comp, raw_esc = 0.0, 0.0, 0.0, 0.0
        all_hits: list[str] = []

        # 深度重构 1：时间衰减与角色隔离
        # 倒序遍历聊天记录，越接近当前的对话权重越高；同时使用严格衰减系数
        reversed_history = list(reversed(chat_history))
        
        for turn_idx, item in enumerate(reversed_history):
            role = self._resolve_role(item)
            # 高价值核心：只分析对方（女生）释放的潜意识信号，男方自己的话绝不纳入计数
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
            sex_hits = set(k for k in self.SEXUAL_SIGNALS if k in text)
            comp_hits = set(k for k in self.COMPLIANCE_SIGNALS if k in text)
            esc_hits = set(k for k in self.HIGH_ESCALATION if k in text)

            # 动态收集触发原因，用于 Planner 日志审计
            all_hits.extend(list(vuln_hits | sex_hits | comp_hits | esc_hits))

            # 深度重构 2：平滑加权算法，单轮命中多个同类词时收益递减（使用饱阶对数平滑）
            raw_vuln += (len(vuln_hits) * 30 if len(vuln_hits) <= 1 else 30 + (len(vuln_hits) - 1) * 10) * time_decay
            raw_sex += (len(sex_hits) * 35 if len(sex_hits) <= 1 else 35 + (len(sex_hits) - 1) * 12) * time_decay
            raw_comp += (len(comp_hits) * 25 if len(comp_hits) <= 1 else 25 + (len(comp_hits) - 1) * 10) * time_decay
            raw_esc += (len(esc_hits) * 40 if len(esc_hits) <= 1 else 40 + (len(esc_hits) - 1) * 15) * time_decay

        # 归一化限制在 [0, 100] 区间内
        vulnerability = min(int(raw_vuln), 100)
        sexual_openness = min(int(raw_sex), 100)
        compliance = min(int(raw_comp), 100)
        
        # 深度重构 3：解耦错位的升级潜力。真正的高价值窗口来自 窗口释放(sex) 与 顺从(comp) 的叠加
        # 脆弱度（vuln）高时应该倾向于稳框架和筑巢提供舒适感，而非直接激进升级
        base_escalation = raw_esc + (raw_sex * 0.4) + (raw_comp * 0.3)
        # 如果脆弱度极高(>=70)，强行对升级窗口做 50% 的防趁虚而入降温压制，维持正人君子的框架感
        if vulnerability >= 70:
            base_escalation *= 0.5
        escalation = min(int(base_escalation), 100)

        # 深度重构 4：重置具有带领感和策略防御性的三级核心指令
        if escalation >= 70 or sexual_openness >= 75:
            level = "high"
            instruction = "女生窗口完全放大。可以大跨步建立男女高张力框架，抛出具有绝对带领感的模糊邀约或关系越轨试探。"
        elif vulnerability >= 65:
            level = "medium"
            instruction = "她正处于情绪脆弱期。男方需展示强大的情绪黑洞承载力，稳住内核不讲道理、不越界跪舔，提供安全舒适感。"
        elif compliance >= 50 or sexual_openness >= 45:
            level = "medium"
            instruction = "对方顺从度良好，互动有良性回馈。适合加入情绪推拉，在调侃中植入轻微偏爱，自然测试升温空间。"
        else:
            level = "low"
            instruction = "常规互动状态。保持高姿态轻松接话，切忌无病呻吟的纯安慰与连续追问，用高价值生活侧面建立吸引。"

        return RiskReport(
            risk_level=level,
            blocked=False,
            reasons=self._dedupe(all_hits),
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
    print("重构后的高价值检测报告：")
    import json
    print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _demo()