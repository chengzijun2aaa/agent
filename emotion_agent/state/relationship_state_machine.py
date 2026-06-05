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


class RelationshipSignal(BaseModel):
    """Signals extracted from one chat history update."""

    model_config = ConfigDict(extra="ignore")

    comfort_delta: float = 0.0
    trust_delta: float = 0.0
    attraction_delta: float = 0.0
    message_frequency_delta: float = 0.0
    meeting_count_delta: int = 0
    evidence: list[str] = Field(default_factory=list)


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

    def __init__(self, initial_state: RelationshipState | Mapping[str, Any] | None = None) -> None:
        """Create a state machine with an optional existing state snapshot."""
        self.state = (
            RelationshipState.model_validate(initial_state)
            if initial_state is not None and not isinstance(initial_state, RelationshipState)
            else initial_state or RelationshipState()
        )
        self.state.sync_label()

    def update_state(self, chat_history: ChatHistory) -> RelationshipState:
        """Update relationship state from chat records and return the new state."""
        messages = self._normalize_history(chat_history)
        signal = self._extract_signal(messages)

        self.state.comfort_score = self._clamp(self.state.comfort_score + signal.comfort_delta)
        self.state.trust_score = self._clamp(self.state.trust_score + signal.trust_delta)
        self.state.attraction_score = self._clamp(self.state.attraction_score + signal.attraction_delta)
        self.state.message_frequency = self._clamp(
            max(self.state.message_frequency * 0.85, 0.0) + signal.message_frequency_delta
        )
        self.state.meeting_count += signal.meeting_count_delta
        self.state.total_messages += len(messages)
        self.state.stage = self.calculate_stage()
        self.state.sync_label()
        self.state.last_evidence = signal.evidence[-12:]
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
        if self.state.total_messages >= 4 or frequency >= 10 or max(comfort, trust, attraction) >= 12:
            return RelationshipStage.L2
        return RelationshipStage.L1

    def export_state(self) -> dict[str, Any]:
        """Export a JSON-serializable state snapshot for prompts or storage."""
        self.state.sync_label()
        return {
            "stage": self.state.stage.value,
            "stage_label": self.state.stage_label,
            "comfort_score": round(self.state.comfort_score, 2),
            "trust_score": round(self.state.trust_score, 2),
            "attraction_score": round(self.state.attraction_score, 2),
            "message_frequency": round(self.state.message_frequency, 2),
            "meeting_count": self.state.meeting_count,
            "total_messages": self.state.total_messages,
            "reply_style": STAGE_REPLY_STYLE[self.state.stage],
            "updated_at": self.state.updated_at.isoformat(),
            "last_evidence": list(self.state.last_evidence),
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
        joined_text = "\n".join(message["content"] for message in messages)
        evidence: list[str] = []
        message_count = len(messages)
        question_count = sum(message["content"].count("?") + message["content"].count("？") for message in messages)
        avg_len = sum(len(message["content"]) for message in messages) / message_count if message_count else 0.0

        comfort_hits = self._keyword_hits(joined_text, self.COMFORT_KEYWORDS)
        trust_hits = self._keyword_hits(joined_text, self.TRUST_KEYWORDS)
        attraction_hits = self._keyword_hits(joined_text, self.ATTRACTION_KEYWORDS)
        meeting_hits = self._keyword_hits(joined_text, self.MEETING_KEYWORDS)
        love_hits = self._keyword_hits(joined_text, self.LOVE_KEYWORDS)

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

        positive_frequency = min(message_count * 3.0 + question_count * 2.0, 22.0)
        length_bonus = 5.0 if avg_len >= 12 else 0.0
        cold_penalty = self._coldness_penalty(messages)

        return RelationshipSignal(
            comfort_delta=len(comfort_hits) * 4.0 + length_bonus - cold_penalty,
            trust_delta=len(trust_hits) * 5.0 + max(question_count - 1, 0) * 1.2,
            attraction_delta=len(attraction_hits) * 6.0 + len(love_hits) * 12.0 + len(meeting_hits) * 4.0,
            message_frequency_delta=max(positive_frequency - cold_penalty, 0.0),
            meeting_count_delta=1 if meeting_hits and any("见" in hit or "约会" in hit for hit in meeting_hits) else 0,
            evidence=evidence,
        )

    def _has_love_signal(self) -> bool:
        """Return whether recent evidence contains an explicit love relationship signal."""
        return any(item.startswith("love:") for item in self.state.last_evidence)

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
            if content in cold_words or len(content) <= 2:
                cold_count += 1
        return min(cold_count * 3.0, 15.0)

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
