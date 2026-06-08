"""Relationship State Machine - relationship and favorability tracking."""

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
    L5 = "L5"  # 线下推进
    L6 = "L6"  # 稳定亲密


class RelationshipState(BaseModel):
    """Relationship status with multi-dimensional scoring."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    stage: RelationshipStage = RelationshipStage.L1
    stage_label: str = "陌生"

    # ==================== 新增核心维度 ====================
    initiative: float = Field(default=0.0, ge=0.0, le=100.0)      # 主动性（她主动找你）
    reply_quality: float = Field(default=0.0, ge=0.0, le=100.0)  # 回复质量（字数、情绪投入）
    intimacy_level: float = Field(default=0.0, ge=0.0, le=100.0) # 私密度（分享深度）
    invitation_willingness: float = Field(default=0.0, ge=0.0, le=100.0)  # 邀约意愿
    emotional_dependence: float = Field(default=0.0, ge=0.0, le=100.0)   # 情绪依赖
    boundary_resistance: float = Field(default=50.0, ge=0.0, le=100.0)   # 边界抵抗（越低越好）

    favorability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    favorability_stage: str = "F0"
    favorability_label: str = "陌生观望"
    intimacy_boundary: str = "先保持轻松自然的聊天距离。"
    total_messages: int = Field(default=0)
    meeting_count: int = Field(default=0)
    last_message_signature: str = ""
    processed_tail_signatures: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_evidence: list[str] = Field(default_factory=list)


class RelationshipStateMachine:
    """Track favorability from 0 and convert signals into relationship stages."""

    def __init__(self, initial_state: RelationshipState | dict | None = None):
        self.state = RelationshipState.model_validate(initial_state) if initial_state else RelationshipState()

    def update_state(self, chat_history: ChatHistory, profile: Mapping[str, Any] | None = None) -> RelationshipState:
        """核心更新逻辑"""
        messages = self._normalize_history(chat_history)
        new_messages = self._new_messages(messages)
        profile = profile or {}

        signal = self._extract_multi_dimension_signal(new_messages)
        pace = self._profile_pace(profile)

        # 更新各维度
        self.state.initiative = self._clamp(self.state.initiative * 0.92 + signal.get("initiative", 0) * pace)
        self.state.reply_quality = self._clamp(self.state.reply_quality * 0.9 + signal.get("reply_quality", 0))
        self.state.intimacy_level = self._clamp(self.state.intimacy_level * 0.88 + signal.get("intimacy", 0) * pace)
        self.state.invitation_willingness = self._clamp(self.state.invitation_willingness * 0.85 + signal.get("invitation", 0) * pace)
        self.state.emotional_dependence = self._clamp(self.state.emotional_dependence * 0.9 + signal.get("dependence", 0) * pace)
        self.state.boundary_resistance = self._clamp(self.state.boundary_resistance - signal.get("boundary_reduce", 0))

        self.state.total_messages += int(signal.get("message_count", 0))
        self.state.meeting_count += signal.get("meeting_delta", 0)

        # 计算综合好感度 + 阶段
        self.state.favorability_score = self._calculate_favorability(profile)
        calculated_stage = self._calculate_stage()
        self.state.stage = self._stabilize_stage(calculated_stage, signal)
        self.state.stage_label = self._get_stage_label(self.state.stage)
        self._sync_favorability_label()

        self.state.last_evidence = signal.get("evidence", [])[-10:]
        self.state.last_updated = datetime.now(timezone.utc)
        self._remember_processed_tail(messages)

        return self.state

    def _extract_multi_dimension_signal(self, messages: list[dict]) -> dict:
        """多维度信号提取"""
        if not messages:
            return {}

        user_messages = [m for m in messages if self._is_user_role(m.get("role", "user"))]
        if not user_messages:
            return {}

        joined = "\n".join(m["content"].lower() for m in user_messages)
        latest = user_messages[-1]["content"].lower() if user_messages else ""

        evidence = []

        # 主动性
        initiative = 0
        if any(k in latest for k in ["想你", "在干嘛", "找你", "你呢", "突然想到你", "怎么不回", "干嘛呢"]):
            initiative = 45
            evidence.append("高主动性")
        elif len(user_messages) >= 2 and any(("？" in m["content"] or "?" in m["content"]) for m in user_messages[-3:]):
            initiative = 25

        # 回复质量
        reply_quality = min(len(joined) * 0.9 + sum(1 for m in user_messages if len(m["content"]) > 15) * 12, 100)

        # 私密度
        intimacy = 0
        if any(k in joined for k in ["告诉你", "秘密", "心事", "以前", "家里", "害怕", "只有你懂"]):
            intimacy = 55
            evidence.append("高私密度分享")

        # 邀约意愿
        invitation = 0
        if any(k in joined for k in ["见面", "一起", "周末", "有空", "出来", "吃饭", "要不要", "下次", "约"]):
            invitation = 60
            evidence.append("强邀约信号")

        # 情绪依赖
        dependence = 0
        if any(k in joined for k in ["想你", "抱抱", "难受", "委屈", "没人懂", "只有你", "哄我", "烦死", "想哭", "陪我"]):
            dependence = 65
            evidence.append("情绪依赖")

        # 边界抵抗
        boundary_reduce = 0
        if any(k in joined for k in ["别这样", "太快", "有压力", "别闹", "保持距离"]):
            boundary_reduce = -30
            evidence.append("边界抵抗")
        else:
            boundary_reduce = 8  # 自然降低抵抗

        return {
            "initiative": initiative,
            "reply_quality": reply_quality,
            "intimacy": intimacy,
            "invitation": invitation,
            "dependence": dependence,
            "boundary_reduce": boundary_reduce,
            "evidence": evidence,
            "meeting_delta": 1 if "见面" in joined or "约" in joined else 0,
            "message_count": len(user_messages),
        }

    def _calculate_favorability(self, profile: Mapping[str, Any] | None = None) -> float:
        """综合好感度计算"""
        profile = profile or {}
        score = (
            self.state.initiative * 0.18 +
            self.state.reply_quality * 0.12 +
            self.state.intimacy_level * 0.18 +
            self.state.invitation_willingness * 0.24 +
            self.state.emotional_dependence * 0.18 +
            (100 - self.state.boundary_resistance) * 0.08
        )
        if self.state.invitation_willingness >= 55:
            score += 9
        if self.state.emotional_dependence >= 55:
            score += 6
        if self.state.initiative >= 35:
            score += 6
        if self.state.total_messages >= 4:
            score += 5
        if self.state.meeting_count >= 1:
            score += 4
        score *= self._profile_pace(profile)
        return self._clamp(score)

    def _calculate_stage(self) -> RelationshipStage:
        f = self.state.favorability_score
        if f >= 85 and self.state.emotional_dependence >= 70 and self.state.total_messages >= 8:
            return RelationshipStage.L6
        if f >= 70 and self.state.invitation_willingness >= 55 and self.state.total_messages >= 5:
            return RelationshipStage.L5
        if f >= 55 and (
            self.state.intimacy_level >= 50
            or self.state.emotional_dependence >= 60
            or self.state.invitation_willingness >= 65
        ):
            return RelationshipStage.L4
        if f >= 25 and self.state.invitation_willingness >= 55 and self.state.total_messages >= 2:
            return RelationshipStage.L3
        if f >= 32 and (self.state.initiative >= 35 or self.state.emotional_dependence >= 55):
            return RelationshipStage.L3
        if f >= 18 or self.state.invitation_willingness >= 45 or self.state.total_messages >= 2:
            return RelationshipStage.L2
        return RelationshipStage.L1

    def _stabilize_stage(self, calculated_stage: RelationshipStage, signal: Mapping[str, Any]) -> RelationshipStage:
        """Avoid noisy stage drops unless there is clear resistance."""
        current = self.state.stage
        current_value = self._stage_rank(current)
        calculated_value = self._stage_rank(calculated_stage)
        has_resistance = "边界抵抗" in signal.get("evidence", [])

        if has_resistance:
            return calculated_stage
        if calculated_value >= current_value:
            return calculated_stage
        if current_value <= self._stage_rank(RelationshipStage.L3):
            return current
        if current_value - calculated_value == 1:
            return current
        return calculated_stage

    @staticmethod
    def _stage_rank(stage: RelationshipStage) -> int:
        """Return a numeric rank for relationship stages."""
        return {
            RelationshipStage.L1: 1,
            RelationshipStage.L2: 2,
            RelationshipStage.L3: 3,
            RelationshipStage.L4: 4,
            RelationshipStage.L5: 5,
            RelationshipStage.L6: 6,
        }[stage]

    def _sync_favorability_label(self) -> None:
        """Synchronize score band fields used by the web UI."""
        score = self.state.favorability_score
        if score >= 90:
            stage, label, boundary = "F6", "稳定亲密", "可表达明确期待，仍要尊重对方当下反馈。"
        elif score >= 80:
            stage, label, boundary = "F5", "强亲密信号", "亲密期待可以更直接，但不能替代明确同意。"
        elif score >= 70:
            stage, label, boundary = "F4", "亲密舒适较高", "可以拉近语气和距离，继续观察主动反馈。"
        elif score >= 60:
            stage, label, boundary = "F3", "可轻微推进", "适合低压力邀约或现场轻微亲近测试。"
        elif score >= 40:
            stage, label, boundary = "F2", "好感苗头", "适合增加分享、轻调侃和稳定互动。"
        elif score >= 15:
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
        """Return a bounded progression multiplier from the per-person profile."""
        if not profile:
            return 1.0
        try:
            pace = float(profile.get("progression_pace", 1.0) or 1.0)
        except (TypeError, ValueError):
            pace = 1.0
        boundary = float(profile.get("boundary_sensitivity", 50) or 50)
        if boundary >= 75:
            pace = min(pace, 0.85)
        leadership = float(profile.get("leadership_preference", 50) or 50)
        if leadership >= 75:
            pace = max(pace, 1.08)
        return max(0.6, min(1.4, pace))

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
        """Return messages that have not been scored yet.

        The web server passes a rolling history window on every turn. A small
        signature tail prevents old messages from being counted again.
        """
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
        """Persist a small processed tail for rolling-window de-duplication."""
        signatures = [self._message_signature(message) for message in messages[-8:]]
        self.state.processed_tail_signatures = signatures
        self.state.last_message_signature = signatures[-1] if signatures else ""

    @staticmethod
    def _message_signature(message: Mapping[str, Any]) -> str:
        """Create a stable signature for one normalized message."""
        raw = f"{message.get('role', '')}\0{message.get('content', '')}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_user_role(role: str) -> bool:
        """Return whether a role belongs to the other person."""
        return str(role).lower() not in {"assistant", "me", "boy", "我"}

    def export_state(self) -> dict:
        """导出给策略/生成器使用"""
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
    machine.update_state(["今天好累，想你抱抱", "你什么时候有空呀"])
    print(machine.export_state())


if __name__ == "__main__":
    _demo()
