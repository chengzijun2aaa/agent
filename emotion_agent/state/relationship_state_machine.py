"""Relationship state machine for long-term emotional chat progression."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

from emotion_agent.utils.types import Message, SenderRole


ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message"
ChatHistory: TypeAlias = "Sequence[ChatHistoryItem]"


class RelationshipStage(str, Enum):
    """Discrete relationship stages used by the state machine."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"

    @property
    def label(self) -> str:
        """Return the Chinese display label for the stage."""
        return RELATIONSHIP_STAGE_LABELS[self]


RELATIONSHIP_STAGE_LABELS: dict[RelationshipStage, str] = {
    RelationshipStage.L1: "陌生",
    RelationshipStage.L2: "刚认识",
    RelationshipStage.L3: "熟悉",
    RelationshipStage.L4: "暧昧",
    RelationshipStage.L5: "约会后",
    RelationshipStage.L6: "恋爱",
}


STAGE_REPLY_STYLE: dict[RelationshipStage, str] = {
    RelationshipStage.L1: "礼貌、克制、低压，不假装亲密，多用开放式关心。",
    RelationshipStage.L2: "自然、轻松、友好，可以接话但不要过度热情。",
    RelationshipStage.L3: "熟悉、稳定、有记忆点，可以主动延展话题。",
    RelationshipStage.L4: "暧昧、俏皮、带一点在意和拉近感，但不过界。",
    RelationshipStage.L5: "亲近、有复盘感，可以提到见面后的细节和期待。",
    RelationshipStage.L6: "亲密、安心、明确在乎，表达陪伴和偏爱。",
}


FAVORABILITY_BANDS: tuple[tuple[float, str, str, str, str], ...] = (
    (
        90.0,
        "F6",
        "稳定亲密",
        "关系已经有较强稳定感，重点是持续尊重、稳定陪伴和明确表达。",
        "可以表达亲密期待，但仍要持续确认对方边界。",
    ),
    (
        80.0,
        "F5",
        "强亲密信号",
        "亲密可能性较高，可以更直接地表达在意，但不能把分数当成确定许可。",
        "共度良宵只能来自明确邀请和清醒同意，不能用评分替代。",
    ),
    (
        70.0,
        "F4",
        "亲密舒适较高",
        "可以观察线下距离和对方主动靠近，但节奏要慢、反馈要轻。",
        "身体触碰必须以对方主动反馈或明确同意为前提。",
    ),
    (
        60.0,
        "F3",
        "牵手试探区",
        "可以在合适线下氛围里轻微测试亲近感，先看眼神、距离和主动性。",
        "牵手也需要现场舒适反馈；迟疑、后退、沉默都当作不继续。",
    ),
    (
        50.0,
        "F2",
        "好感苗头",
        "适合增加分享、轻调侃和低压力邀约，不急着升级身体亲密。",
        "避免身体接触推进，先让互动更自然。",
    ),
    (
        30.0,
        "F1",
        "基本舒适",
        "对话有基本舒适感，适合继续建立熟悉和信任。",
        "保持社交距离，不做暧昧或身体推进。",
    ),
    (
        10.0,
        "F0.5",
        "初步接触",
        "已经有基础来往，但还需要更多稳定、轻松的互动。",
        "不要推进身体接触。",
    ),
    (
        0.0,
        "F0",
        "陌生观望",
        "先建立安全、自然、低压力的聊天舒适感。",
        "不要推进身体接触。",
    ),
)


class RelationshipSignal(BaseModel):
    """Signals extracted from one chat history update."""

    model_config = ConfigDict(extra="ignore")

    comfort_delta: float = 0.0
    trust_delta: float = 0.0
    attraction_delta: float = 0.0
    message_frequency_delta: float = 0.0
    meeting_count_delta: int = 0
    evidence: list[str] = Field(default_factory=list)


class FavorabilityStageInfo(BaseModel):
    """Human-readable favorability band with consent-safe intimacy guidance."""

    model_config = ConfigDict(extra="ignore")

    score: float = Field(default=0.0, ge=0.0, le=100.0)
    stage: str = "F0"
    label: str = "陌生观望"
    guidance: str = "先建立安全、自然、低压力的聊天舒适感。"
    intimacy_boundary: str = "不要推进身体接触。"
    consent_note: str = "好感度只是聊天信号估计，不等于同意；任何身体接触都必须看对方当下明确、清醒、自愿的反馈。"


class RelationshipState(BaseModel):
    """Validated relationship state snapshot."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    stage: RelationshipStage = RelationshipStage.L1
    stage_label: str = RELATIONSHIP_STAGE_LABELS[RelationshipStage.L1]
    comfort_score: float = Field(default=0.0, ge=0.0, le=100.0)
    trust_score: float = Field(default=0.0, ge=0.0, le=100.0)
    attraction_score: float = Field(default=0.0, ge=0.0, le=100.0)
    message_frequency: float = Field(default=0.0, ge=0.0, le=100.0)
    meeting_count: int = Field(default=0, ge=0)
    total_messages: int = Field(default=0, ge=0)
    favorability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    favorability_stage: str = "F0"
    favorability_label: str = "陌生观望"
    favorability_guidance: str = "先建立安全、自然、低压力的聊天舒适感。"
    intimacy_boundary: str = "不要推进身体接触。"
    consent_note: str = "好感度只是聊天信号估计，不等于同意；任何身体接触都必须看对方当下明确、清醒、自愿的反馈。"
    last_message_signature: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_evidence: list[str] = Field(default_factory=list)

    @field_validator("stage", mode="before")
    @classmethod
    def normalize_stage(cls, value: object) -> RelationshipStage:
        """Normalize stage inputs from enum, code, or Chinese label."""
        if isinstance(value, RelationshipStage):
            return value
        text = str(value).strip()
        for stage, label in RELATIONSHIP_STAGE_LABELS.items():
            if text in {stage.value, label}:
                return stage
        return RelationshipStage.L1

    def sync_label(self) -> None:
        """Synchronize display label with the current stage enum."""
        self.stage_label = self.stage.label


class RelationshipStateMachine:
    """Updates and exports relationship state from chat history signals."""

    COMFORT_KEYWORDS: tuple[str, ...] = (
        "抱抱",
        "安慰",
        "陪我",
        "谢谢你",
        "你懂我",
        "和你说",
        "开心",
        "难过",
        "委屈",
        "累",
        "压力",
    )
    TRUST_KEYWORDS: tuple[str, ...] = (
        "告诉你",
        "只和你说",
        "秘密",
        "心事",
        "家里",
        "以前",
        "害怕",
        "真实",
        "认真",
    )
    ATTRACTION_KEYWORDS: tuple[str, ...] = (
        "想你",
        "喜欢你",
        "可爱",
        "你真好",
        "晚安",
        "早安",
        "等你",
        "吃醋",
        "你在干嘛",
        "想见你",
    )
    MEETING_KEYWORDS: tuple[str, ...] = (
        "见面",
        "约会",
        "一起吃饭",
        "看电影",
        "出来玩",
        "下次见",
        "今天见到你",
        "刚见完",
    )
    LOVE_KEYWORDS: tuple[str, ...] = (
        "在一起",
        "男朋友",
        "女朋友",
        "对象",
        "恋爱",
        "爱你",
        "我们官宣",
    )
    BOUNDARY_KEYWORDS: tuple[str, ...] = (
        "别这样",
        "别闹",
        "不要这样",
        "不想聊",
        "有点尴尬",
        "太快了",
        "有压力",
        "保持距离",
    )

    def __init__(self, initial_state: RelationshipState | Mapping[str, Any] | None = None) -> None:
        """Create a state machine with an optional existing state snapshot."""
        self.state = (
            RelationshipState.model_validate(initial_state)
            if initial_state is not None and not isinstance(initial_state, RelationshipState)
            else initial_state or RelationshipState()
        )
        self.state.sync_label()
        self._sync_favorability()

    def update_state(self, chat_history: ChatHistory) -> RelationshipState:
        """Update relationship state from chat records and return the new state."""
        messages = self._normalize_history(chat_history)
        new_messages = self._new_messages_since_last(messages)
        signal = self._extract_signal(new_messages)

        self.state.comfort_score = self._clamp(self.state.comfort_score + signal.comfort_delta)
        self.state.trust_score = self._clamp(self.state.trust_score + signal.trust_delta)
        self.state.attraction_score = self._clamp(self.state.attraction_score + signal.attraction_delta)
        self.state.message_frequency = self._clamp(
            max(self.state.message_frequency * 0.85, 0.0) + signal.message_frequency_delta
        )
        self.state.meeting_count += signal.meeting_count_delta
        self.state.total_messages += sum(1 for message in new_messages if self._is_counterpart_message(message))
        self.state.stage = self.calculate_stage()
        self.state.sync_label()
        self.state.last_evidence = signal.evidence[-12:]
        self._sync_favorability()
        if messages:
            self.state.last_message_signature = self._message_signature(messages[-1])
        self.state.updated_at = datetime.now(timezone.utc)
        return self.state

    def calculate_stage(self) -> RelationshipStage:
        """Calculate the relationship stage from current scores and counters."""
        comfort = self.state.comfort_score
        trust = self.state.trust_score
        attraction = self.state.attraction_score
        frequency = self.state.message_frequency
        meetings = self.state.meeting_count

        if trust >= 82 and attraction >= 82 and comfort >= 75 and self._has_love_signal():
            return RelationshipStage.L6
        if meetings >= 1 and attraction >= 62 and comfort >= 55:
            return RelationshipStage.L5
        if attraction >= 55 and trust >= 42 and comfort >= 42 and frequency >= 35:
            return RelationshipStage.L4
        if comfort >= 32 and trust >= 26 and frequency >= 22:
            return RelationshipStage.L3
        if self.state.total_messages >= 2 or frequency >= 10 or max(comfort, trust, attraction) >= 12:
            return RelationshipStage.L2
        return RelationshipStage.L1

    def calculate_favorability_score(self) -> float:
        """Estimate favorability on a 0-100 scale from relationship signals.

        The score is a decision-support signal for chat strategy. It must not
        be treated as consent or as a promise that physical intimacy is welcome.
        """
        base_score = (
            self.state.comfort_score * 0.30
            + self.state.trust_score * 0.25
            + self.state.attraction_score * 0.30
            + self.state.message_frequency * 0.10
            + min(self.state.meeting_count * 5.0, 10.0)
        )
        stage_floor = {
            RelationshipStage.L1: 0.0,
            RelationshipStage.L2: 15.0,
            RelationshipStage.L3: 35.0,
            RelationshipStage.L4: 55.0,
            RelationshipStage.L5: 65.0,
            RelationshipStage.L6: 85.0,
        }[self.state.stage]
        score = max(base_score, stage_floor)
        if self._has_recent_evidence("cold:"):
            score -= 8.0
        if self._has_recent_evidence("boundary:"):
            score -= 15.0
        if self.state.trust_score < 25 and self.state.comfort_score < 30:
            score = min(score, 49.0)
        return self._clamp(score)

    def calculate_favorability_stage(self, score: float | None = None) -> FavorabilityStageInfo:
        """Return the favorability band and boundary guidance for a score."""
        value = self._clamp(self.state.favorability_score if score is None else score)
        for floor, stage, label, guidance, boundary in FAVORABILITY_BANDS:
            if value >= floor:
                return FavorabilityStageInfo(
                    score=round(value, 1),
                    stage=stage,
                    label=label,
                    guidance=guidance,
                    intimacy_boundary=boundary,
                )
        return FavorabilityStageInfo(score=round(value, 1))

    def export_state(self) -> dict[str, Any]:
        """Export a JSON-serializable state snapshot for prompts or storage."""
        self.state.sync_label()
        self._sync_favorability()
        return {
            "stage": self.state.stage.value,
            "stage_label": self.state.stage_label,
            "comfort_score": round(self.state.comfort_score, 2),
            "trust_score": round(self.state.trust_score, 2),
            "attraction_score": round(self.state.attraction_score, 2),
            "message_frequency": round(self.state.message_frequency, 2),
            "meeting_count": self.state.meeting_count,
            "total_messages": self.state.total_messages,
            "favorability_score": round(self.state.favorability_score, 1),
            "favorability_stage": self.state.favorability_stage,
            "favorability_label": self.state.favorability_label,
            "favorability_guidance": self.state.favorability_guidance,
            "intimacy_boundary": self.state.intimacy_boundary,
            "consent_note": self.state.consent_note,
            "reply_style": STAGE_REPLY_STYLE[self.state.stage],
            "updated_at": self.state.updated_at.isoformat(),
            "last_evidence": list(self.state.last_evidence),
            "last_message_signature": self.state.last_message_signature,
        }

    def build_reply_context(self, user_message: str) -> dict[str, str]:
        """Build stage-aware reply context for a downstream response generator."""
        self.state.sync_label()
        return {
            "user_message": user_message,
            "relationship_stage": f"{self.state.stage.value} {self.state.stage_label}",
            "reply_style": STAGE_REPLY_STYLE[self.state.stage],
            "stage_instruction": self._stage_instruction(user_message),
        }

    def _extract_signal(self, messages: Sequence[dict[str, str]]) -> RelationshipSignal:
        """Extract relationship deltas from normalized chat records."""
        counterpart_messages = [message for message in messages if self._is_counterpart_message(message)]
        if not counterpart_messages:
            return RelationshipSignal()

        joined_text = "\n".join(message["content"] for message in counterpart_messages)
        evidence: list[str] = []
        message_count = len(counterpart_messages)
        question_count = sum(message["content"].count("?") + message["content"].count("？") for message in counterpart_messages)
        avg_len = sum(len(message["content"]) for message in counterpart_messages) / message_count if message_count else 0.0

        comfort_hits = self._keyword_hits(joined_text, self.COMFORT_KEYWORDS)
        trust_hits = self._keyword_hits(joined_text, self.TRUST_KEYWORDS)
        attraction_hits = self._keyword_hits(joined_text, self.ATTRACTION_KEYWORDS)
        meeting_hits = self._keyword_hits(joined_text, self.MEETING_KEYWORDS)
        love_hits = self._keyword_hits(joined_text, self.LOVE_KEYWORDS)
        boundary_hits = self._keyword_hits(joined_text, self.BOUNDARY_KEYWORDS)

        if comfort_hits:
            evidence.append(f"comfort:{','.join(comfort_hits)}")
        if trust_hits:
            evidence.append(f"trust:{','.join(trust_hits)}")
        if attraction_hits:
            evidence.append(f"attraction:{','.join(attraction_hits)}")
        if meeting_hits:
            evidence.append(f"meeting:{','.join(meeting_hits)}")
        if love_hits:
            evidence.append(f"love:{','.join(love_hits)}")
        if boundary_hits:
            evidence.append(f"boundary:{','.join(boundary_hits)}")

        positive_frequency = min(message_count * 3.0 + question_count * 2.0, 22.0)
        length_bonus = 5.0 if avg_len >= 12 else 0.0
        cold_penalty = self._coldness_penalty(counterpart_messages)
        if cold_penalty:
            evidence.append("cold:short_or_low_effort_reply")
        boundary_penalty = len(boundary_hits) * 5.0

        return RelationshipSignal(
            comfort_delta=len(comfort_hits) * 4.0 + length_bonus - cold_penalty - boundary_penalty,
            trust_delta=len(trust_hits) * 5.0 + max(question_count - 1, 0) * 1.2 - len(boundary_hits) * 3.0,
            attraction_delta=len(attraction_hits) * 6.0 + len(love_hits) * 12.0 + len(meeting_hits) * 8.0 - boundary_penalty,
            message_frequency_delta=max(positive_frequency - cold_penalty, 0.0),
            meeting_count_delta=(
                1
                if meeting_hits and any(word in hit for hit in meeting_hits for word in ("见", "约会", "吃饭", "电影"))
                else 0
            ),
            evidence=evidence,
        )

    def _has_love_signal(self) -> bool:
        """Return whether recent evidence contains an explicit love relationship signal."""
        return any(item.startswith("love:") for item in self.state.last_evidence)

    def _has_recent_evidence(self, prefix: str) -> bool:
        """Return whether recent evidence contains an item with the given prefix."""
        return any(item.startswith(prefix) for item in self.state.last_evidence)

    def _sync_favorability(self) -> None:
        """Synchronize favorability score and readable stage fields."""
        score = self.calculate_favorability_score()
        info = self.calculate_favorability_stage(score)
        self.state.favorability_score = info.score
        self.state.favorability_stage = info.stage
        self.state.favorability_label = info.label
        self.state.favorability_guidance = info.guidance
        self.state.intimacy_boundary = info.intimacy_boundary
        self.state.consent_note = info.consent_note

    @staticmethod
    def _keyword_hits(text: str, keywords: Sequence[str]) -> list[str]:
        """Return keywords found in text while preserving keyword order."""
        return [keyword for keyword in keywords if keyword.lower() in text.lower()]

    @staticmethod
    def _coldness_penalty(messages: Sequence[dict[str, str]]) -> float:
        """Estimate relationship cooling from short low-effort replies."""
        cold_words = {"嗯", "哦", "好", "行", "随便", "再说", "忙", "没事"}
        recent = messages[-6:]
        cold_count = 0
        for message in recent:
            content = message["content"].strip()
            normalized = re.sub(r"\s+", "", content.lower())
            if normalized in {"你好", "hi", "hello", "哈喽", "在吗"}:
                continue
            if content in cold_words or len(content) <= 2:
                cold_count += 1
        return min(cold_count * 3.0, 15.0)

    @staticmethod
    def _is_counterpart_message(message: Mapping[str, str]) -> bool:
        """Return whether a message is from the person being analyzed."""
        role = str(message.get("role", "")).lower()
        return role in {"user", "girl", "she", "her", "female", "target"}

    def _new_messages_since_last(self, messages: Sequence[dict[str, str]]) -> list[dict[str, str]]:
        """Return only messages that have not already affected the state."""
        if not messages:
            return []
        last_signature = self.state.last_message_signature
        if not last_signature and self.state.total_messages > 0:
            return list(messages[-1:])
        if not last_signature:
            return list(messages)
        for index, message in enumerate(messages):
            if self._message_signature(message) == last_signature:
                return list(messages[index + 1 :])
        return list(messages)

    @staticmethod
    def _message_signature(message: Mapping[str, str]) -> str:
        """Build a stable lightweight signature for one normalized message."""
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()
        return f"{role}:{len(content)}:{content[-32:]}"

    @staticmethod
    def _stage_instruction(user_message: str) -> str:
        """Return a compact instruction showing how stage should affect replies."""
        return (
            "同一句用户消息也必须随关系阶段变化。"
            f"当前用户消息：{user_message}"
        )

    @staticmethod
    def _normalize_history(chat_history: ChatHistory) -> list[dict[str, str]]:
        """Normalize raw chat records into role-content dictionaries."""
        normalized: list[dict[str, str]] = []
        for item in chat_history:
            if isinstance(item, Message):
                normalized.append({"role": item.role.value, "content": item.content})
            elif isinstance(item, str):
                normalized.append({"role": SenderRole.USER.value, "content": item})
            else:
                role = str(item.get("role", item.get("sender", SenderRole.USER.value)))
                content = str(item.get("content", item.get("text", item.get("message", ""))))
                normalized.append({"role": role, "content": content.strip()})
        return [message for message in normalized if message["content"]]

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp numeric scores into the 0-100 range."""
        return max(0.0, min(100.0, float(value)))


def _demo() -> None:
    """Run a small module smoke test."""
    l1 = RelationshipStateMachine()
    l4 = RelationshipStateMachine(
        {
            "comfort_score": 58,
            "trust_score": 50,
            "attraction_score": 68,
            "message_frequency": 45,
        }
    )
    l4.state.stage = l4.calculate_stage()
    l4.state.sync_label()
    print(l1.build_reply_context("你在干嘛"))
    print(l4.build_reply_context("你在干嘛"))


if __name__ == "__main__":
    _demo()
