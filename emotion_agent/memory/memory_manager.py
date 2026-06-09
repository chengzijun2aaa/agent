"""Persistent structured memory manager for user profile facts."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CURRENT_MEMORY_VERSION = 3


class MemoryFact(BaseModel):
    """One normalized memory value with provenance metadata."""

    model_config = ConfigDict(extra="ignore")

    value: str = Field(default="", description="Normalized fact value.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Extraction confidence.")
    evidence: str = Field(default="", description="Source text that produced this fact.")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("value", "evidence", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        """Normalize text fields to stripped strings."""
        if value is None:
            return ""
        return str(value).strip()


class FemaleProfile(BaseModel):
    """Long-lived interaction profile for one woman.

    The profile is not a label for the person. It is a compact operating model
    for the assistant: how fast to progress, how direct to be, and what kind of
    emotional feedback tends to land well with this specific conversation.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    label: str = "平衡观察型"
    communication_style: str = "balanced"
    progression_pace: float = Field(default=1.0, ge=0.6, le=1.4)
    leadership_preference: int = Field(default=50, ge=0, le=100)
    reassurance_need: int = Field(default=50, ge=0, le=100)
    playfulness: int = Field(default=50, ge=0, le=100)
    sensitivity: int = Field(default=50, ge=0, le=100)
    boundary_sensitivity: int = Field(default=50, ge=0, le=100)
    preferred_feedback: list[str] = Field(default_factory=list)
    avoided_moves: list[str] = Field(default_factory=list)
    last_signals: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def summary(self) -> dict[str, Any]:
        """Return a compact profile for planning, generation, and UI debug panels."""
        return {
            "label": self.label,
            "communication_style": self.communication_style,
            "progression_pace": round(self.progression_pace, 2),
            "leadership_preference": self.leadership_preference,
            "reassurance_need": self.reassurance_need,
            "playfulness": self.playfulness,
            "sensitivity": self.sensitivity,
            "boundary_sensitivity": self.boundary_sensitivity,
            "preferred_feedback": list(self.preferred_feedback),
            "avoided_moves": list(self.avoided_moves),
            "last_signals": list(self.last_signals),
        }


class ConfidenceWin(BaseModel):
    """One small communication win recorded for user confidence building."""

    model_config = ConfigDict(extra="ignore")

    skill: str = Field(default="", description="Skill category practiced in this turn.")
    detail: str = Field(default="", description="Human-readable description of the win.")
    evidence: str = Field(default="", description="Reply text or behavior that produced the win.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("skill", "detail", "evidence", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        """Normalize text fields to stripped strings."""
        if value is None:
            return ""
        return str(value).strip()


class ConfidenceMemory(BaseModel):
    """Long-lived confidence building record for the person using the assistant."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    total_turns: int = Field(default=0, ge=0)
    total_wins: int = Field(default=0, ge=0)
    current_streak: int = Field(default=0, ge=0)
    strengths: list[str] = Field(default_factory=list)
    recent_wins: list[ConfidenceWin] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def summary(self) -> dict[str, Any]:
        """Return a compact confidence report for UI and coaching."""
        return {
            "total_turns": self.total_turns,
            "total_wins": self.total_wins,
            "current_streak": self.current_streak,
            "strengths": list(self.strengths),
            "recent_wins": [win.model_dump(mode="json") for win in self.recent_wins[:6]],
        }


class PetMemory(BaseModel):
    """Structured pet memory."""

    model_config = ConfigDict(extra="ignore")

    species: str = Field(default="", description="Pet species, such as cat or dog.")
    breed: str = Field(default="", description="Pet breed, such as ragdoll.")
    name: str = Field(default="", description="Pet name if known.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: str = Field(default="")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("species", "breed", "name", "evidence", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        """Normalize text fields to stripped strings."""
        if value is None:
            return ""
        return str(value).strip()

    @property
    def display(self) -> str:
        """Return a compact human-readable pet description."""
        species = "" if self.species and self.breed.endswith(self.species) else self.species
        return "".join(part for part in (self.name, self.breed, species) if part)


class MemoryExtraction(BaseModel):
    """Facts extracted from one message or a batch of messages."""

    model_config = ConfigDict(extra="ignore")

    name: MemoryFact | None = None
    age: MemoryFact | None = None
    occupation: MemoryFact | None = None
    city: MemoryFact | None = None
    pets: list[PetMemory] = Field(default_factory=list)
    interests: list[MemoryFact] = Field(default_factory=list)
    birthday: MemoryFact | None = None
    dietary_habits: list[MemoryFact] = Field(default_factory=list)
    travel_experiences: list[MemoryFact] = Field(default_factory=list)
    important_events: list[MemoryFact] = Field(default_factory=list)

    def is_empty(self) -> bool:
        """Return whether no useful fact was extracted."""
        scalar_empty = all(
            item is None
            for item in (self.name, self.age, self.occupation, self.city, self.birthday)
        )
        list_empty = not any(
            (self.pets, self.interests, self.dietary_habits, self.travel_experiences, self.important_events)
        )
        return scalar_empty and list_empty


class UserMemory(BaseModel):
    """Long-lived memory fields for one user."""

    model_config = ConfigDict(extra="ignore")

    name: MemoryFact | None = None
    age: MemoryFact | None = None
    occupation: MemoryFact | None = None
    city: MemoryFact | None = None
    pets: list[PetMemory] = Field(default_factory=list)
    interests: list[MemoryFact] = Field(default_factory=list)
    birthday: MemoryFact | None = None
    dietary_habits: list[MemoryFact] = Field(default_factory=list)
    travel_experiences: list[MemoryFact] = Field(default_factory=list)
    important_events: list[MemoryFact] = Field(default_factory=list)
    profile: FemaleProfile = Field(default_factory=FemaleProfile)
    confidence: ConfidenceMemory = Field(default_factory=ConfidenceMemory)

    def summary(self) -> dict[str, Any]:
        """Return a compact dictionary for prompt injection or debugging."""
        return {
            "name": self.name.value if self.name else "",
            "age": self.age.value if self.age else "",
            "occupation": self.occupation.value if self.occupation else "",
            "city": self.city.value if self.city else "",
            "pets": [pet.model_dump(mode="json") for pet in self.pets],
            "interests": [item.value for item in self.interests],
            "birthday": self.birthday.value if self.birthday else "",
            "dietary_habits": [item.value for item in self.dietary_habits],
            "travel_experiences": [item.value for item in self.travel_experiences],
            "important_events": [item.value for item in self.important_events],
            "profile": self.profile.summary(),
            "confidence": self.confidence.summary(),
        }


class MemoryStore(BaseModel):
    """Versioned persistent memory document."""

    model_config = ConfigDict(extra="ignore")

    version: int = CURRENT_MEMORY_VERSION
    user: UserMemory = Field(default_factory=UserMemory)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def upgrade_version(cls, data: object) -> object:
        """Upgrade older memory document shapes before validation."""
        if not isinstance(data, dict):
            return data
        if not data:
            return data
        version = int(data.get("version", 0) or 0)
        if version < 1:
            upgraded = {
                "version": CURRENT_MEMORY_VERSION,
                "user": data.get("user", data.get("profile", {})),
            }
            if data.get("created_at"):
                upgraded["created_at"] = data["created_at"]
            if data.get("updated_at"):
                upgraded["updated_at"] = data["updated_at"]
            return upgraded
        if version < 2:
            upgraded = dict(data)
            user = dict(upgraded.get("user", {}))
            user.setdefault("profile", FemaleProfile().model_dump(mode="json"))
            upgraded["user"] = user
            upgraded["version"] = CURRENT_MEMORY_VERSION
            return upgraded
        if version < 3:
            upgraded = dict(data)
            user = dict(upgraded.get("user", {}))
            user.setdefault("confidence", ConfidenceMemory().model_dump(mode="json"))
            upgraded["user"] = user
            upgraded["version"] = CURRENT_MEMORY_VERSION
            return upgraded
        return data

    @model_validator(mode="after")
    def stamp_current_version(self) -> "MemoryStore":
        """Ensure validated stores use the current schema version."""
        self.version = CURRENT_MEMORY_VERSION
        return self


class MemorySearchResult(BaseModel):
    """One searchable memory hit."""

    key: str
    value: str
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: str = ""


class MemoryManager:
    """Extracts, validates, merges, saves, loads, and searches user memory."""

    PET_BREEDS: Mapping[str, str] = {
        "布偶": "猫",
        "布偶猫": "猫",
        "英短": "猫",
        "美短": "猫",
        "橘猫": "猫",
        "狸花": "猫",
        "金毛": "狗",
        "柯基": "狗",
        "柴犬": "狗",
        "萨摩耶": "狗",
        "泰迪": "狗",
    }

    INTEREST_HINTS: tuple[str, ...] = (
        "喜欢",
        "爱",
        "迷上",
        "感兴趣",
        "最近在学",
        "平时会",
    )

    def __init__(self, memory_path: str | Path = "memory.json") -> None:
        """Create a memory manager backed by a JSON file."""
        self.memory_path = Path(memory_path)
        self.memory = self.load_memory()

    def extract_memory(self, text_or_messages: str | Sequence[str | Mapping[str, Any]]) -> MemoryExtraction:
        """Extract structured memory facts from text or chat messages."""
        text = self._coerce_user_text(text_or_messages)
        extraction = MemoryExtraction()

        extraction.name = self._extract_name(text)
        extraction.age = self._extract_age(text)
        extraction.occupation = self._extract_occupation(text)
        extraction.city = self._extract_city(text)
        extraction.pets = self._extract_pets(text)
        extraction.interests = self._extract_interests(text)
        extraction.birthday = self._extract_birthday(text)
        extraction.dietary_habits = self._extract_dietary_habits(text)
        extraction.travel_experiences = self._extract_travel_experiences(text)
        extraction.important_events = self._extract_important_events(text)
        return extraction

    def update_memory(
        self,
        text_or_memory: str | Sequence[str | Mapping[str, Any]] | MemoryExtraction | Mapping[str, Any],
        *,
        learn_profile: bool = True,
    ) -> MemoryStore:
        """Extract and merge new facts, then save the updated memory document."""
        profile_text = ""
        if learn_profile and (
            isinstance(text_or_memory, str) or not isinstance(text_or_memory, (MemoryExtraction, Mapping))
        ):
            profile_text = self._coerce_user_text(text_or_memory)
        extraction = self._coerce_extraction(text_or_memory)
        self._merge_extraction(extraction)
        if profile_text:
            self._update_profile_from_text(profile_text)
        self.memory.updated_at = datetime.now(timezone.utc)
        self.save_memory(self.memory)
        return self.memory

    def update_profile(
        self,
        text_or_messages: str | Sequence[str | Mapping[str, Any]],
        *,
        analysis: Mapping[str, Any] | None = None,
        relationship_state: Mapping[str, Any] | None = None,
    ) -> FemaleProfile:
        """Update and persist the per-person interaction profile."""
        text = self._coerce_user_text(text_or_messages)
        self._update_profile_from_text(text, analysis=analysis, relationship_state=relationship_state)
        self.memory.updated_at = datetime.now(timezone.utc)
        self.save_memory(self.memory)
        return self.memory.user.profile

    def load_memory(self) -> MemoryStore:
        """Load memory from disk, creating a new validated store when missing."""
        if not self.memory_path.exists():
            memory = MemoryStore()
            self.save_memory(memory)
            return memory

        try:
            raw = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            memory = MemoryStore()
            self.save_memory(memory)
            return memory

        memory = MemoryStore.model_validate(raw)
        if memory.version != CURRENT_MEMORY_VERSION:
            memory.version = CURRENT_MEMORY_VERSION
            self.save_memory(memory)
        return memory

    def save_memory(self, memory: MemoryStore | None = None) -> None:
        """Persist the current memory document as validated JSON."""
        resolved = memory or self.memory
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(
            resolved.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def search_memory(self, query: str) -> list[MemorySearchResult]:
        """Search memory values by key, value, or evidence text."""
        query_text = query.strip().lower()
        if not query_text:
            return []

        results: list[MemorySearchResult] = []
        for key, value, evidence in self._iter_memory_values():
            haystack = f"{key} {value} {evidence}".lower()
            if query_text in haystack:
                results.append(MemorySearchResult(key=key, value=value, score=1.0, evidence=evidence))
        return results

    def _coerce_extraction(
        self,
        text_or_memory: str | Sequence[str | Mapping[str, Any]] | MemoryExtraction | Mapping[str, Any],
    ) -> MemoryExtraction:
        """Convert supported update inputs into ``MemoryExtraction``."""
        if isinstance(text_or_memory, MemoryExtraction):
            return text_or_memory
        if isinstance(text_or_memory, Mapping):
            return MemoryExtraction.model_validate(text_or_memory)
        return self.extract_memory(text_or_memory)

    def _merge_extraction(self, extraction: MemoryExtraction) -> None:
        """Merge extracted facts into the current memory with validation."""
        user = self.memory.user
        user.name = self._choose_fact(user.name, extraction.name)
        user.age = self._choose_fact(user.age, extraction.age)
        user.occupation = self._choose_fact(user.occupation, extraction.occupation)
        user.city = self._choose_fact(user.city, extraction.city)
        user.birthday = self._choose_fact(user.birthday, extraction.birthday)

        user.pets = self._merge_pets(user.pets, extraction.pets)
        user.interests = self._merge_fact_list(user.interests, extraction.interests)
        user.dietary_habits = self._merge_fact_list(user.dietary_habits, extraction.dietary_habits)
        user.travel_experiences = self._merge_fact_list(user.travel_experiences, extraction.travel_experiences)
        user.important_events = self._merge_fact_list(user.important_events, extraction.important_events)

    def _update_profile_from_text(
        self,
        text: str,
        *,
        analysis: Mapping[str, Any] | None = None,
        relationship_state: Mapping[str, Any] | None = None,
    ) -> None:
        """Learn interaction preferences from recent chat text."""
        if not text.strip():
            return

        profile = self.memory.user.profile
        lower = text.lower()
        signals: list[str] = []

        if any(word in lower for word in ("哈哈", "笑死", "逗你", "开玩笑", "你猜", "笨", "坏", "哼")):
            profile.playfulness = self._nudge_int(profile.playfulness, 12)
            profile.communication_style = "playful"
            profile.preferred_feedback = self._append_unique(profile.preferred_feedback, "轻调侃")
            signals.append("调侃接受度高")

        if any(word in lower for word in ("累", "难受", "委屈", "压力", "烦死", "想哭", "崩溃", "没人懂")):
            profile.reassurance_need = self._nudge_int(profile.reassurance_need, 14)
            profile.sensitivity = self._nudge_int(profile.sensitivity, 8)
            profile.preferred_feedback = self._append_unique(profile.preferred_feedback, "先安抚再安排")
            signals.append("需要先被接住")

        if any(word in lower for word in ("你安排", "你决定", "听你的", "都可以", "随便你", "看你", "你说了算", "你来定", "看你安排")):
            profile.leadership_preference = self._nudge_int(profile.leadership_preference, 14)
            profile.progression_pace = self._nudge_float(profile.progression_pace, 0.06)
            profile.preferred_feedback = self._append_unique(profile.preferred_feedback, "清晰安排")
            signals.append("接受清晰带领")

        if any(word in lower for word in ("见面", "见一下", "一起", "周末", "周六", "周日", "有空", "出来", "吃饭", "咖啡", "电影", "喝一杯", "找天")):
            profile.leadership_preference = self._nudge_int(profile.leadership_preference, 8)
            profile.progression_pace = self._nudge_float(profile.progression_pace, 0.08)
            profile.preferred_feedback = self._append_unique(profile.preferred_feedback, "具体邀约")
            signals.append("邀约窗口")

        if any(word in lower for word in ("别这样", "太快", "有压力", "别闹", "保持距离", "不舒服", "先别聊", "太急", "慢一点", "有点过")):
            profile.boundary_sensitivity = self._nudge_int(profile.boundary_sensitivity, 16)
            profile.sensitivity = self._nudge_int(profile.sensitivity, 10)
            profile.progression_pace = self._nudge_float(profile.progression_pace, -0.12)
            profile.avoided_moves = self._append_unique(profile.avoided_moves, "快速推进")
            signals.append("边界敏感")

        if any(word in lower for word in ("别的女生", "别的女人", "她是谁", "吃醋", "是不是喜欢", "聊得开心")):
            profile.reassurance_need = self._nudge_int(profile.reassurance_need, 10)
            profile.preferred_feedback = self._append_unique(profile.preferred_feedback, "稳定确定感")
            signals.append("需要确定感")

        if any(word in lower for word in ("哦", "嗯", "随便", "晚点说", "再说", "没空", "不想说")):
            profile.sensitivity = self._nudge_int(profile.sensitivity, 8)
            profile.progression_pace = self._nudge_float(profile.progression_pace, -0.05)
            profile.avoided_moves = self._append_unique(profile.avoided_moves, "连续追问")
            signals.append("低能量或冷淡")

        if analysis:
            intent = str(analysis.get("intent", ""))
            if intent in {"邀约", "释放好感", "撒娇"}:
                profile.progression_pace = self._nudge_float(profile.progression_pace, 0.05)
            if intent in {"冷淡", "敷衍", "撤退"}:
                profile.progression_pace = self._nudge_float(profile.progression_pace, -0.06)

        if relationship_state:
            favorability = float(relationship_state.get("favorability_score", 0) or 0)
            if favorability >= 40:
                profile.leadership_preference = self._nudge_int(profile.leadership_preference, 4)

        profile.last_signals = (signals + profile.last_signals)[:10]
        profile.label = self._profile_label(profile)
        profile.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _profile_label(profile: FemaleProfile) -> str:
        """Return a readable profile label from current score bands."""
        if profile.boundary_sensitivity >= 70 or profile.progression_pace <= 0.82:
            return "慢热边界型"
        if profile.reassurance_need >= 70:
            return "情绪安抚型"
        if profile.playfulness >= 68:
            return "轻松调侃型"
        if profile.leadership_preference >= 68:
            return "清晰带领型"
        return "平衡观察型"

    @staticmethod
    def _append_unique(values: list[str], value: str, *, limit: int = 8) -> list[str]:
        """Append a value once while preserving recent preference order."""
        result = [item for item in values if item != value]
        result.insert(0, value)
        return result[:limit]

    @staticmethod
    def _nudge_int(value: int, delta: int) -> int:
        """Move an integer score while keeping it inside 0-100."""
        return max(0, min(100, int(value) + delta))

    @staticmethod
    def _nudge_float(value: float, delta: float) -> float:
        """Move progression pace while keeping it inside the model bounds."""
        return max(0.6, min(1.4, float(value) + delta))

    @staticmethod
    def _choose_fact(current: MemoryFact | None, incoming: MemoryFact | None) -> MemoryFact | None:
        """Choose the better scalar fact during automatic merging."""
        if incoming is None or not incoming.value:
            return current
        if current is None or not current.value:
            return incoming
        if incoming.confidence >= current.confidence or incoming.value != current.value:
            return incoming
        return current

    def _merge_fact_list(self, current: list[MemoryFact], incoming: list[MemoryFact]) -> list[MemoryFact]:
        """Merge fact lists by normalized value."""
        merged: dict[str, MemoryFact] = {self._norm(fact.value): fact for fact in current if fact.value}
        for fact in incoming:
            key = self._norm(fact.value)
            if not key:
                continue
            existing = merged.get(key)
            merged[key] = self._choose_fact(existing, fact) or fact
        return list(merged.values())

    def _merge_pets(self, current: list[PetMemory], incoming: list[PetMemory]) -> list[PetMemory]:
        """Merge pet memories while preserving breed/species learned earlier."""
        merged = list(current)
        for pet in incoming:
            match = self._find_matching_pet(merged, pet)
            if match is None:
                merged.append(pet)
                continue
            if pet.species and not match.species:
                match.species = pet.species
            if pet.breed and not match.breed:
                match.breed = pet.breed
            if pet.name and not match.name:
                match.name = pet.name
            if pet.evidence:
                match.evidence = pet.evidence
            match.confidence = max(match.confidence, pet.confidence)
            match.updated_at = datetime.now(timezone.utc)
        return merged

    @staticmethod
    def _find_matching_pet(current: list[PetMemory], incoming: PetMemory) -> PetMemory | None:
        """Find an existing pet memory likely describing the same pet."""
        for pet in current:
            if incoming.name and pet.name == incoming.name:
                return pet
            if incoming.breed and pet.breed == incoming.breed:
                return pet
            if incoming.species and pet.species == incoming.species and not incoming.breed and not incoming.name:
                return pet
        return None

    def _extract_name(self, text: str) -> MemoryFact | None:
        """Extract user's name from explicit self-introduction."""
        patterns = (r"我叫([\u4e00-\u9fa5A-Za-z]{1,12})", r"我的名字叫([\u4e00-\u9fa5A-Za-z]{1,12})")
        return self._first_match_fact(text, patterns, confidence=0.9)

    def _extract_age(self, text: str) -> MemoryFact | None:
        """Extract age from explicit age statements."""
        match = re.search(r"我(?:今年)?(\d{1,3})岁", text)
        if not match:
            return None
        return MemoryFact(value=match.group(1), confidence=0.9, evidence=text)

    def _extract_occupation(self, text: str) -> MemoryFact | None:
        """Extract occupation from common self-description patterns."""
        patterns = (
            r"我是(?:一名|一个)?([\u4e00-\u9fa5A-Za-z]{2,20})(?:，|。|,|\.|$)",
            r"我在做([\u4e00-\u9fa5A-Za-z]{2,20})(?:，|。|,|\.|$)",
            r"我的工作是([\u4e00-\u9fa5A-Za-z]{2,20})(?:，|。|,|\.|$)",
        )
        return self._first_match_fact(text, patterns, confidence=0.75)

    def _extract_city(self, text: str) -> MemoryFact | None:
        """Extract city from residence statements."""
        patterns = (
            r"我住在([\u4e00-\u9fa5A-Za-z]{2,20})",
            r"我在([\u4e00-\u9fa5A-Za-z]{2,20})(?:生活|工作|上班)",
            r"人在([\u4e00-\u9fa5A-Za-z]{2,20})",
        )
        return self._first_match_fact(text, patterns, confidence=0.8)

    def _extract_pets(self, text: str) -> list[PetMemory]:
        """Extract pet memories including cat/dog species and known breeds."""
        pets: list[PetMemory] = []
        matched_breeds: list[str] = []
        for breed, species in sorted(self.PET_BREEDS.items(), key=lambda item: len(item[0]), reverse=True):
            if any(breed in matched or matched in breed for matched in matched_breeds):
                continue
            if breed in text:
                matched_breeds.append(breed)
                pets.append(PetMemory(species=species, breed=breed, confidence=0.9, evidence=text))

        if any(keyword in text for keyword in ("我家猫", "猫今天", "猫又", "猫猫", "主子")):
            pets.append(PetMemory(species="猫", confidence=0.75, evidence=text))
        if any(keyword in text for keyword in ("我家狗", "狗今天", "狗又", "狗狗")):
            pets.append(PetMemory(species="狗", confidence=0.75, evidence=text))

        name_match = re.search(r"我家(?:猫|狗|宠物)(?:叫|名字叫)([\u4e00-\u9fa5A-Za-z]{1,12})", text)
        if name_match:
            species = "猫" if "猫" in name_match.group(0) else "狗" if "狗" in name_match.group(0) else ""
            pets.append(PetMemory(species=species, name=name_match.group(1), confidence=0.9, evidence=text))
        return self._merge_pets([], pets)

    def _extract_interests(self, text: str) -> list[MemoryFact]:
        """Extract interests from like/love/learning statements."""
        interests: list[MemoryFact] = []
        for hint in self.INTEREST_HINTS:
            pattern = rf"{hint}([\u4e00-\u9fa5A-Za-z0-9、，, ]{{1,30}})"
            for match in re.finditer(pattern, text):
                value = self._clean_phrase(match.group(1))
                if value:
                    interests.append(MemoryFact(value=value, confidence=0.7, evidence=text))
        return self._dedupe_facts(interests)

    def _extract_birthday(self, text: str) -> MemoryFact | None:
        """Extract birthday from date-like birthday statements."""
        patterns = (
            r"我生日(?:是|在)?(\d{1,2}月\d{1,2}[日号]?)",
            r"我的生日(?:是|在)?(\d{1,2}月\d{1,2}[日号]?)",
            r"生日(?:是|在)?(\d{1,2}[/-]\d{1,2})",
        )
        return self._first_match_fact(text, patterns, confidence=0.9)

    def _extract_dietary_habits(self, text: str) -> list[MemoryFact]:
        """Extract dietary habits and preferences."""
        habits: list[MemoryFact] = []
        keywords = ("不吃辣", "爱吃辣", "喜欢甜食", "不吃香菜", "素食", "减脂餐", "咖啡", "奶茶", "海鲜过敏")
        for keyword in keywords:
            if keyword in text:
                habits.append(MemoryFact(value=keyword, confidence=0.85, evidence=text))
        return habits

    def _extract_travel_experiences(self, text: str) -> list[MemoryFact]:
        """Extract travel experiences from visited/traveled statements."""
        experiences: list[MemoryFact] = []
        patterns = (
            r"去过([\u4e00-\u9fa5A-Za-z、，, ]{2,40})",
            r"旅行去了([\u4e00-\u9fa5A-Za-z、，, ]{2,40})",
            r"旅游去了([\u4e00-\u9fa5A-Za-z、，, ]{2,40})",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                value = self._clean_phrase(match.group(1))
                if value:
                    experiences.append(MemoryFact(value=value, confidence=0.75, evidence=text))
        return self._dedupe_facts(experiences)

    def _extract_important_events(self, text: str) -> list[MemoryFact]:
        """Extract important personal events."""
        events: list[MemoryFact] = []
        event_keywords = ("毕业", "入职", "离职", "搬家", "分手", "恋爱", "升职", "考试", "面试", "结婚")
        for keyword in event_keywords:
            if keyword in text:
                events.append(MemoryFact(value=self._sentence_around(text, keyword), confidence=0.75, evidence=text))
        return self._dedupe_facts(events)

    def _first_match_fact(self, text: str, patterns: Sequence[str], *, confidence: float) -> MemoryFact | None:
        """Return the first regex capture as a memory fact."""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return MemoryFact(value=self._clean_phrase(match.group(1)), confidence=confidence, evidence=text)
        return None

    @staticmethod
    def _clean_phrase(value: str) -> str:
        """Trim punctuation and filler from an extracted phrase."""
        return value.strip(" ，,。.!！?？;；：:、\n\t")

    @staticmethod
    def _sentence_around(text: str, keyword: str) -> str:
        """Return a compact sentence containing an important event keyword."""
        for sentence in re.split(r"[。！？!?；;\n]", text):
            if keyword in sentence:
                return sentence.strip()
        return keyword

    @staticmethod
    def _dedupe_facts(facts: list[MemoryFact]) -> list[MemoryFact]:
        """Remove duplicate fact values while preserving order."""
        seen: set[str] = set()
        result: list[MemoryFact] = []
        for fact in facts:
            key = MemoryManager._norm(fact.value)
            if key and key not in seen:
                seen.add(key)
                result.append(fact)
        return result

    @staticmethod
    def _coerce_text(text_or_messages: str | Sequence[str | Mapping[str, Any]]) -> str:
        """Convert raw text or message records into a single text block."""
        if isinstance(text_or_messages, str):
            return text_or_messages
        parts: list[str] = []
        for item in text_or_messages:
            if isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item.get("content", item.get("text", item.get("message", "")))))
        return "\n".join(part for part in parts if part)

    @staticmethod
    def _coerce_user_text(text_or_messages: str | Sequence[str | Mapping[str, Any]]) -> str:
        """Convert only the other person's messages into a single text block."""
        if isinstance(text_or_messages, str):
            return text_or_messages
        parts: list[str] = []
        for item in text_or_messages:
            if isinstance(item, str):
                parts.append(item)
                continue
            role = str(item.get("role", "user")).lower()
            if role in {"assistant", "me", "boy", "我"}:
                continue
            parts.append(str(item.get("content", item.get("text", item.get("message", "")))))
        return "\n".join(part for part in parts if part)

    @staticmethod
    def _norm(value: str) -> str:
        """Normalize a value for deduplication and search matching."""
        return re.sub(r"\s+", "", value).lower()

    def _iter_memory_values(self) -> list[tuple[str, str, str]]:
        """Flatten memory into searchable key-value-evidence tuples."""
        user = self.memory.user
        rows: list[tuple[str, str, str]] = []
        for key in ("name", "age", "occupation", "city", "birthday"):
            fact = getattr(user, key)
            if fact is not None and fact.value:
                rows.append((key, fact.value, fact.evidence))
        for index, pet in enumerate(user.pets):
            value = pet.display or pet.species or pet.breed or pet.name
            if value:
                rows.append((f"pets[{index}]", value, pet.evidence))
        for key in ("interests", "dietary_habits", "travel_experiences", "important_events"):
            for index, fact in enumerate(getattr(user, key)):
                if fact.value:
                    rows.append((f"{key}[{index}]", fact.value, fact.evidence))
        return rows


def _demo() -> None:
    """Run a small module smoke test."""
    demo_path = Path("memory_demo.json")
    manager = MemoryManager(memory_path=demo_path)
    manager.update_memory("我养了一只布偶猫")
    manager.update_memory("我家猫今天又拆家了")
    print(manager.memory.user.summary())
    demo_path.unlink(missing_ok=True)


if __name__ == "__main__":
    _demo()
