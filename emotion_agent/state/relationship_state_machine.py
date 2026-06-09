"""Relationship State Machine - relationship and favorability tracking - Refactored Version"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.utils.types import Message, SenderRole

ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message"
ChatHistory: TypeAlias = "Sequence[ChatHistoryItem]"


class RelationshipStage(str, Enum):
    L1 = "L1"  # 陌生
    L2 = "L2"  # 熟悉
    L3 = "L3"  # 高频吸引
    L4 = "L4"  # 暧昧
    L5 = "L5"  # 线下推进（必须有真实见面或顶级好感加持）
    L6 = "L6"  # 稳定亲密


class RelationshipState(BaseModel):
    """Relationship status with multi-dimensional scoring."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    stage: RelationshipStage = RelationshipStage.L1
    stage_label: str = "陌生"

    initiative: float = Field(default=0.0, ge=0.0, le=100.0)      # 主动性
    reply_quality: float = Field(default=0.0, ge=0.0, le=100.0)   # 回复质量
    intimacy_level: float = Field(default=0.0, ge=0.0, le=100.0)  # 私密度
    invitation_willingness: float = Field(default=0.0, ge=0.0, le=100.0)  # 邀约意愿
    emotional_dependence: float = Field(default=0.0, ge=0.0, le=100.0)   # 情绪依赖
    boundary_resistance: float = Field(default=35.0, ge=0.0, le=100.0)   # 边界抵抗（初始下调至更理性的35）

    favorability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    favorability_stage: str = "F0"
    favorability_label: str = "陌生观望"
    intimacy_boundary: str = "先保持轻松自然的聊天距离。"
    total_messages: int = Field(default=0)
    meeting_count: int = Field(default=0)  # 必须是真实的线下见面，不能被聊天数据无脑污染
    last_message_signature: str = ""
    processed_tail_signatures: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_evidence: list[str] = Field(default_factory=list)


class RelationshipStateMachine:
    """Track favorability natively and process transitions with sociological sanity."""

    def __init__(self, initial_state: RelationshipState | dict | None = None):
        if isinstance(initial_state, dict):
            self.state = RelationshipState.model_validate(initial_state)
        elif isinstance(initial_state, RelationshipState):
            self.state = initial_state
        else:
            self.state = RelationshipState()

    def update_state(self, chat_history: ChatHistory, profile: Mapping[str, Any] | None = None) -> RelationshipState:
        """核心更新逻辑 - 引入记忆阻尼和平滑过滤器"""
        messages = self._normalize_history(chat_history)
        new_messages = self._new_messages(messages)
        profile = profile or {}

        if not new_messages:
            # 没有新消息时，维持原状，仅更新同步标签，防止系统轮询时分数自动雪崩
            self._sync_favorability_label()
            return self.state

        signal = self._extract_multi_dimension_signal(new_messages)
        pace = self._profile_pace(profile)

        # 核心改进 1：大幅调高旧分记忆权重（0.85 -> 0.95），确保关系具有高价值的沉稳延续性，拒绝原地崩溃
        self.state.initiative = self._clamp(self.state.initiative * 0.96 + signal.get("initiative", 0) * pace)
        self.state.reply_quality = self._clamp(self.state.reply_quality * 0.94 + signal.get("reply_quality", 0))
        self.state.intimacy_level = self._clamp(self.state.intimacy_level * 0.95 + signal.get("intimacy", 0) * pace)
        self.state.invitation_willingness = self._clamp(self.state.invitation_willingness * 0.95 + signal.get("invitation", 0) * pace)
        self.state.emotional_dependence = self._clamp(self.state.emotional_dependence * 0.96 + signal.get("dependence", 0) * pace)
        
        # 优化边界抵抗降低速率（当没有抗拒时，以更快且丝滑的效率回归舒适区）
        self.state.boundary_resistance = self._clamp(self.state.boundary_resistance - signal.get("boundary_reduce", 0))

        self.state.total_messages += int(signal.get("message_count", 0))
        
        # 核心改进 2：解耦口头邀约意愿与实际见面。meeting_count 的增量只能由显性的业务层埋点传入，不从聊天文本里盲目意淫
        if "meeting_delta" in profile:
            self.state.meeting_count += int(profile["meeting_delta"] or 0)

        # 计算综合好感度 + 阶段
        self.state.favorability_score = self._calculate_favorability(profile)
        calculated_stage = self._calculate_stage()
        
        # 稳定拦截处理
        self.state.stage = self._stabilize_stage(calculated_stage, signal)
        self.state.stage_label = self._get_stage_label(self.state.stage)
        self._sync_favorability_label()

        self.state.last_evidence = self._dedupe(signal.get("evidence", []) + self.state.last_evidence)[-8:]
        self.state.last_updated = datetime.now(timezone.utc)
        self._remember_processed_tail(messages)

        return self.state

    def _extract_multi_dimension_signal(self, messages: list[dict]) -> dict:
        """多维度女性信号精确提取提取器"""
        user_messages = [m for m in messages if self._is_user_role(m.get("role", "user"))]
        if not user_messages:
            return {"boundary_reduce": 3.0, "message_count": 0, "evidence": []}

        joined = "\n".join(m["content"].lower() for m in user_messages)
        latest = user_messages[-1]["content"].lower() if user_messages else ""

        evidence = []

        # 主动性检测
        initiative = 0.0
        if any(k in latest for k in ["想你", "在干嘛", "找你", "你呢", "突然想到你", "怎么不回", "干嘛呢", "朋友圈"]):
            initiative = 35.0
            evidence.append("主动开启话题/延续互动")
        elif len(user_messages) >= 2 and any(("？" in m["content"] or "?" in m["content"]) for m in user_messages[-2:]):
            initiative = 18.0

        # 回复质量检测（平滑字数加成，单句超长给高质量认证）
        avg_len = sum(len(m["content"]) for m in user_messages) / len(user_messages)
        reply_quality = min(avg_len * 2.5 + sum(22 for m in user_messages if len(m['content']) > 20), 45.0)

        # 私密度分享检测
        intimacy = 0.0
        if any(k in joined for k in ["告诉你", "秘密", "心事", "以前", "家里", "害怕", "只有你懂", "小时候", "其实我"]):
            intimacy = 40.0
            evidence.append("深度私密自我暴露")

        # 邀约意愿检测
        invitation = 0.0
        if any(k in joined for k in ["见面", "见一下", "一起", "周末", "出来", "吃饭", "喝一杯", "咖啡", "有空", "要不要", "约"]):
            invitation = 45.0
            evidence.append("释放显性线上邀约窗口")

        # 情绪依赖检测
        dependence = 0.0
        if any(k in joined for k in ["想你", "抱抱", "难受", "委屈", "没人懂", "只有你", "哄我", "烦死", "想哭", "陪我"]):
            dependence = 45.0
            evidence.append("高情绪依赖倾诉")

        # 边界抵抗与舒适度平滑
        boundary_reduce = 4.0  # 常规顺畅聊天时，每轮自然下降4点抵抗力
        if any(k in joined for k in ["别这样", "太快", "有压力", "别闹", "保持距离", "不舒服", "太急", "慢一点", "换个话题"]):
            boundary_reduce = -25.0  # 负负得正，抵抗力飙升25点
            evidence.append("触发边界抗拒")

        return {
            "initiative": initiative,
            "reply_quality": reply_quality,
            "intimacy": intimacy,
            "invitation": invitation,
            "dependence": dependence,
            "boundary_reduce": boundary_reduce,
            "evidence": evidence,
            "message_count": len(user_messages),
        }

    def _calculate_favorability(self, profile: Mapping[str, Any] | None = None) -> float:
        """综合好感度矩阵公式"""
        profile = profile or {}
        # 精准配比各维度权重
        score = (
            self.state.initiative * 0.20 +
            self.state.reply_quality * 0.10 +
            self.state.intimacy_level * 0.20 +
            self.state.invitation_willingness * 0.25 +
            self.state.emotional_dependence * 0.15 +
            (100.0 - self.state.boundary_resistance) * 0.10
        )
        
        # 溢出红利触发器（必须达到高分段才有额外奖励）
        if self.state.invitation_willingness >= 65: score += 6.0
        if self.state.emotional_dependence >= 65: score += 4.0
        if self.state.initiative >= 50: score += 4.0

        score *= self._profile_pace(profile)
        return self._clamp(score)

    def _calculate_stage(self) -> RelationshipStage:
        """核心改进 3：引入极其严苛的【阶段晋升锁】"""
        f = self.state.favorability_score
        meetings = self.state.meeting_count

        # L6 锁：必须有稳定亲密好感，且信息基础充沛
        if f >= 82 and self.state.emotional_dependence >= 65 and self.state.total_messages >= 30:
            return RelationshipStage.L6
            
        # L5 锁（线下推进）：具有决定性的一级锁死！
        # 如果【从来没见过面】且【对方邀约意愿没有产生极端偏爱爆表】，系统绝对禁止切入L5，死死按在L4暧昧区，防AI误判产生轻浮越界动作
        if (meetings >= 1 and f >= 68) or (f >= 78 and self.state.invitation_willingness >= 70):
            return RelationshipStage.L5
            
        # L4 锁（暧昧拉扯）
        if f >= 52 and (self.state.intimacy_level >= 45 or self.state.emotional_dependence >= 50):
            return RelationshipStage.L4
            
        # L3 锁（高频吸引）
        if f >= 28 and (self.state.initiative >= 25 or self.state.invitation_willingness >= 35):
            return RelationshipStage.L3
            
        # L2 锁（熟悉）
        if f >= 14 or self.state.total_messages >= 3:
            return RelationshipStage.L2
            
        return RelationshipStage.L1

    def _stabilize_stage(self, calculated_stage: RelationshipStage, signal: Mapping[str, Any]) -> RelationshipStage:
        """防止噪音引发的阶段蹦极，仅在存在抵抗时允许降级"""
        current = self.state.stage
        current_value = self._stage_rank(current)
        calculated_value = self._stage_rank(calculated_stage)
        has_resistance = "触发边界抗拒" in signal.get("evidence", [])

        if has_resistance:
            return calculated_stage  # 如果对方抗拒，无条件接受降级，进行战略后撤
        if calculated_value >= current_value:
            return calculated_stage  # 顺利升级
        # 缓冲平滑：无抗拒情况下，单次波动如果只跌落1个档位，则冻结状态，防止女方口头冷淡直接毁掉整条链路
        if current_value - calculated_value == 1:
            return current
        return calculated_stage

    @staticmethod
    def _stage_rank(stage: RelationshipStage) -> int:
        return {
            RelationshipStage.L1: 1,
            RelationshipStage.L2: 2,
            RelationshipStage.L3: 3,
            RelationshipStage.L4: 4,
            RelationshipStage.L5: 5,
            RelationshipStage.L6: 6,
        }[stage]

    def _sync_favorability_label(self) -> None:
        score = self.state.favorability_score
        if score >= 88:
            stage, label, boundary = "F6", "稳定亲密", "可表达明确期待，仍要尊重对方当下反馈。"
        elif score >= 75:
            stage, label, boundary = "F5", "强亲密信号", "亲密期待可以更直接，但不能替代明确同意。"
        elif score >= 62:
            stage, label, boundary = "F4", "亲密舒适较高", "可以拉近语气和距离，继续观察主动反馈。"
        elif score >= 48:
            stage, label, boundary = "F3", "可轻微推进", "适合低压力邀约或现场轻微亲近测试。"
        elif score >= 30:
            stage, label, boundary = "F2", "好感苗头", "适合增加分享、轻调侃和稳定互动。"
        elif score >= 12:
            stage, label, boundary = "F1", "初步接触", "先建立熟悉感，不急着升级。"
        else:
            stage, label, boundary = "F0", "陌生观望", "先保持轻松自然的聊天距离。"
        self.state.favorability_stage = stage
        self.state.favorability_label = label
        self.state.intimacy_boundary = boundary

    @staticmethod
    def _get_stage_label(stage: RelationshipStage) -> str:
        labels = {
            RelationshipStage.L1: "陌生",
            RelationshipStage.L2: "熟悉",
            RelationshipStage.L3: "吸引",
            RelationshipStage.L4: "暧昧",
            RelationshipStage.L5: "线下推进",
            RelationshipStage.L6: "稳定亲密",
        }
        return labels.get(stage, "未知")

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def _profile_pace(profile: Mapping[str, Any] | None) -> float:
        if not profile:
            return 1.0
        try:
            pace = float(profile.get("progression_pace", 1.0) or 1.0)
        except (TypeError, ValueError):
            pace = 1.0
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        if boundary >= 75:
            pace = min(pace, 0.82)
        leadership = float(profile.get("leadership_preference", 50) or 50)
        if leadership >= 75:
            pace = max(pace, 1.12)
        return max(0.5, min(1.5, pace))

    @staticmethod
    def _normalize_history(chat_history: ChatHistory) -> list[dict]:
        normalized = []
        for item in chat_history:
            if isinstance(item, Message):
                normalized.append({"role": item.role.value, "content": item.content})
            elif isinstance(item, str):
                normalized.append({"role": "user", "content": item})
            else:
                normalized.append({
                    "role": str(item.get("role", "user")),
                    "content": str(item.get("content", ""))
                })
        return normalized

    def _new_messages(self, messages: list[dict]) -> list[dict]:
        if not messages:
            return []
        signatures = [self._message_signature(message) for message in messages]
        tail = list(self.state.processed_tail_signatures or [])
        if not tail:
            return messages[-15:]

        max_overlap = min(len(tail), len(signatures))
        for overlap in range(max_overlap, 0, -1):
            expected = tail[-overlap:]
            for index in range(0, len(signatures) - overlap + 1):
                if signatures[index:index + overlap] == expected:
                    return messages[index + overlap:]

        if self.state.last_message_signature and self.state.last_message_signature in signatures:
            index = signatures.index(self.state.last_message_signature)
            return messages[index + 1:]

        return messages[-1:] if self.state.total_messages else messages[-15:]

    def _remember_processed_tail(self, messages: list[dict]) -> None:
        signatures = [self._message_signature(message) for message in messages[-8:]]
        self.state.processed_tail_signatures = signatures
        self.state.last_message_signature = signatures[-1] if signatures else ""

    @staticmethod
    def _message_signature(message: Mapping[str, Any]) -> str:
        raw = f"{message.get('role', '')}\0{message.get('content', '')}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_user_role(role: str) -> bool:
        return str(role).lower() not in {"assistant", "me", "boy", "我"}

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen = set()
        return [v for v in values if not (v in seen or seen.add(v))]

    def export_state(self) -> dict:
        return {
            "stage": self.state.stage.value,
            "stage_label": self.state.stage_label,
            "favorability_score": round(self.state.favorability_score, 1),
            "favorability_stage": self.state.favorability_stage,
            "favorability_label": self.state.favorability_label,
            "favorability_baseline": 0,
            "favorability_ceiling": 100,
            "intimacy_boundary": self.state.intimacy_boundary,
            "initiative": round(self.state.initiative, 1),
            "reply_quality": round(self.state.reply_quality, 1),
            "intimacy_level": round(self.state.intimacy_level, 1),
            "invitation_willingness": round(self.state.invitation_willingness, 1),
            "emotional_dependence": round(self.state.emotional_dependence, 1),
            "boundary_resistance": round(self.state.boundary_resistance, 1),
            "total_messages": self.state.total_messages,
            "meeting_count": self.state.meeting_count,
            "last_message_signature": self.state.last_message_signature,
            "processed_tail_signatures": self.state.processed_tail_signatures,
            "last_evidence": self.state.last_evidence,
        }


def _demo() -> None:
    machine = RelationshipStateMachine()
    # 轮次 1：测试常规情绪拉扯与邀约释出
    machine.update_state(["今天好累，想你抱抱", "你什么时候有空呀"])
    print("轮次 1 结算（正常暧昧）:", machine.state.stage, f"得分: {machine.state.favorability_score}")
    
    # 轮次 2：测试新机制下的稳定性。当女生下一轮只回了一个平淡的“好呀”，原系统分数会瞬间暴跌导致降级，重构后稳定保持在 L4
    machine.update_state(["好呀"])
    print("轮次 2 结算（平淡回应，稳定不跌）:", machine.state.stage, f"得分: {machine.state.favorability_score}")


if __name__ == "__main__":
    _demo()