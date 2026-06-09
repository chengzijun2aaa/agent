"""Reply Generator - short, natural WeChat-style replies."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.strategy.strategy_planner import ReplyPlan


class ReplyCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str
    source: str = "rules"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplyGenerator:
    """Generate concise relationship-aware reply candidates."""

    INVITE_PHRASES = (
        "见面", "出来", "出门", "周末", "周六", "周日", "有空", "一起",
        "吃饭", "电影", "咖啡", "喝一杯", "我带你", "我来安排", "定一个",
        "定时间", "定地方", "找天", "下次见",
    )
    EXPLICIT_INVITE_SIGNALS = (
        "见面", "见一下", "周末", "周六", "周日", "有空", "一起",
        "吃饭", "出来", "电影", "咖啡", "喝一杯", "找天", "约",
    )

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    def generate(
        self,
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> list[ReplyCandidate]:
        candidates: list[ReplyCandidate] = []
        if self.llm is not None:
            candidates = self._generate_with_llm(chat_history, plan, relationship_state, memory)
        
        if len(candidates) < 4:
            candidates.extend(self._generate_with_rules(chat_history, plan, relationship_state, memory))

        deduped = self._dedupe(candidates)
        capped = self._cap_early_invites(deduped, chat_history, relationship_state, plan)
        return capped[: plan.candidate_count or 6]

    def _generate_with_llm(self, chat_history, plan: ReplyPlan, relationship_state, memory) -> list[ReplyCandidate]:
        prompt = self._build_prompt(chat_history, plan, relationship_state, memory)
        try:
            response = self.llm.generate(prompt, temperature=0.8, max_tokens=480, presence_penalty=0.55)
        except TypeError:
            response = self.llm.generate(prompt, temperature=0.8, max_tokens=480)
        
        if not getattr(response, "success", False) or not response.content:
            return []

        candidates = []
        for line in response.content.splitlines():
            text = self._clean_line(line)
            if text and len(text.strip()) >= 2:  # 放宽限制到2个字，兼容“去啊”“哈喽”等微信短打
                candidates.append(ReplyCandidate(text=text, source="llm"))
        return candidates

    def _build_prompt(self, chat_history, plan: ReplyPlan, relationship_state, memory) -> str:
        stage = str(relationship_state.get("stage", "L3"))
        favorability = float(relationship_state.get("favorability_score", 0) or 0)
        history = self._format_history(chat_history[-10:])
        action = getattr(plan, "action_type", "推进")
        profile = self._profile(memory)
        profile_lines = self._format_profile(profile)
        early_stage = self._is_early_stage(relationship_state)
        invite_signal = self._has_explicit_invite_signal(chat_history)
        invite_rule = (
            "当前是前期：不要频繁邀约。6-8条里最多2条出现“见面/出来/周末”，其余做情绪推拉、轻调侃、留口子。"
            if early_stage and not invite_signal
            else "如果她已经主动释放见面窗口，可以自然落到具体安排，但仍然保持低压力。"
        )

        expression_intent = self._expression_intent(self._latest_text(chat_history), action)
        personality = self._personality_package(profile)

        # 核心优化：让模型先围绕表达动机和动态性格包生成，再输出自然短句。
        return f"""
你是一个真实、松弛、边界感稳定的成年人，正在微信和女生聊天。

【微信打字核心规范】：
1. 简短但有信息：字数控制在 4-18 字以内。短句必须带态度、接梗或情绪承接，不能只有“嗯”“行”“好吧”。
2. 杜绝书面标点：绝不输出标准的句号（。）、叹号（！）、逗号（，）。
3. 允许微信特色断句：长句用空格代替逗号。允许在末尾带个轻松的语气问号（？），或者少量微信自带表情（如 🌚, 😅, 😎）。
4. 绝不说教、连环追问、刻意迎合或自证。先接住话，再给态度。
5. 保持低压力和高舒适度：平等、自然、松弛、有边界。
- {invite_rule}

表达动机：{expression_intent}
动态性格包：{personality}
当前行动类型：{action}
核心目标：{plan.objective}
语气方向：{plan.tone}
关系阶段：{stage}
好感度：{favorability:.1f}/100
她的互动画像：
{profile_lines}

聊天记录（最近的）：
{history}

先在心里判断 Intent，再按动态性格包改写成不同句式。直接生成 6-8 条候选回复，每条独立成行。
只输出纯文本，坚决不要编号，不要引号，不要复读同一种句型。
""".strip()

    @staticmethod
    def _generate_with_rules(chat_history, plan: ReplyPlan, relationship_state, memory) -> list[ReplyCandidate]:
        latest = ReplyGenerator._latest_text(chat_history).lower()
        action = getattr(plan, "action_type", "推进")
        profile = ReplyGenerator._profile(memory)
        clear_lead = int(profile.get("leadership_preference", 50) or 50) >= 65

        expression_intent = ReplyGenerator._expression_intent(latest, action)
        personality = ReplyGenerator._personality_package(profile)
        base = ReplyGenerator._intent_variants(
            expression_intent,
            latest=latest,
            memory=memory,
            clear_lead=clear_lead,
        )
        base = ReplyGenerator._season_variants(base, personality, profile)

        offset = ReplyGenerator._stable_offset(f"{latest}|{action}|{personality}")
        rotated = base[offset:] + base[:offset]
        return [
            ReplyCandidate(
                text=t,
                source="rules",
                metadata={"expression_intent": expression_intent, "personality": personality},
            )
            for t in rotated
        ]

    # 以下所有方法完美兼容并修缮细节
    @classmethod
    def _cap_early_invites(
        cls,
        candidates: Sequence[ReplyCandidate],
        chat_history: Sequence,
        relationship_state: Mapping[str, Any],
        plan: ReplyPlan,
    ) -> list[ReplyCandidate]:
        if not cls._is_early_stage(relationship_state) or cls._has_explicit_invite_signal(chat_history):
            return list(candidates)

        candidate_count = plan.candidate_count or 6
        limit = max(1, min(2, int(round(candidate_count * 0.25))))
        invite_count = 0
        result: list[ReplyCandidate] = []

        for candidate in candidates:
            if cls._is_invite_text(candidate.text):
                if invite_count < limit:
                    result.append(candidate)
                    invite_count += 1
            else:
                result.append(candidate)

        for fallback in cls._early_pull_fallbacks(chat_history):
            if len(result) >= candidate_count:
                break
            key = re.sub(r"\W+", "", fallback.text.lower())
            if not any(re.sub(r"\W+", "", item.text.lower()) == key for item in result):
                result.append(fallback)

        return result[:candidate_count]

    @classmethod
    def _early_pull_fallbacks(cls, chat_history: Sequence) -> list[ReplyCandidate]:
        latest = cls._latest_text(chat_history)
        if any(w in latest for w in ("累", "烦", "难受", "委屈", "压力", "想哭")):
            texts = ["这波确实挺耗你", "先别硬撑 丢给我两句", "听着就烦 先站你这边", "你这状态我先接住了"]
        elif any(w in latest for w in ("猫", "狗", "宠物", "拆家")):
            texts = ["它今天又营业了是吧", "你现在是案发现场负责人", "听着又气又想笑", "给我看看现场"]
        else:
            texts = ["你这话有点意思", "别只丢半句 继续", "这句我先记你一笔", "你这个语气有点可爱", "行 你继续我听着", "你这样我会惦记一下"]
        return [ReplyCandidate(text=text, source="early_pull_fallback") for text in texts]

    @staticmethod
    def _expression_intent(latest: str, action: str) -> str:
        """Map the current plan and latest text to a reply motive."""
        if action == "边界回应" or any(w in latest for w in ("有点压力", "太快", "先别", "不舒服", "别这样")):
            return "BoundaryBackoff"
        if action == "接情绪" or any(w in latest for w in ("累", "烦", "难受", "委屈", "压力", "想哭")):
            return "Reassurance"
        if action == "邀约推进" or any(w in latest for w in ("见面", "周末", "有空", "一起", "吃饭")):
            return "LowPressureInvite"
        if action in ("轻暧昧拉扯", "暧昧拉扯", "轻暧昧") or any(w in latest for w in ("想你", "抱抱", "亲亲", "贴贴")):
            return "PlayfulWarmth"
        if action in {"稳定回应", "框架应对"} or any(w in latest for w in ("别的女生", "她是谁", "吃醋", "你是不是")):
            return "SteadyReassurance"
        if action == "后撤" or any(w in latest for w in ("忙", "没空", "再说", "不想说", "先忙")):
            return "SoftExit"
        if any(w in latest for w in ("猫", "狗", "宠物", "拆家", "布偶")):
            return "LifeCallback"
        normalized_latest = re.sub(r"\s+", "", latest)
        if normalized_latest in {"你好", "hi", "hello", "哈喽", "在吗"}:
            return "Opening"
        return "CuriousCallback"

    @staticmethod
    def _personality_package(profile: Mapping[str, Any]) -> str:
        """Choose a lightweight style package from the dynamic profile."""
        boundary = int(profile.get("boundary_sensitivity", 50) or 50)
        reassurance = int(profile.get("reassurance_need", 50) or 50)
        playfulness = int(profile.get("playfulness", 50) or 50)
        leadership = int(profile.get("leadership_preference", 50) or 50)
        if boundary >= 68:
            return "克制型：少追问 低压力 偏职场"
        if reassurance >= 68:
            return "温暖型：先接情绪 给稳定感"
        if playfulness >= 65:
            return "轻松型：带一点调侃和接梗"
        if leadership >= 65:
            return "清晰型：短句明确 但不压迫"
        return "平衡型：自然接话 轻微留口子"

    @staticmethod
    def _intent_variants(
        expression_intent: str,
        *,
        latest: str,
        memory: Mapping[str, Any],
        clear_lead: bool,
    ) -> list[str]:
        """Return candidate variants for one expression motive."""
        if expression_intent == "BoundaryBackoff":
            return ["好 先不聊这个", "可以 你先舒服点", "收到 我退一步", "嗯 不给你压力", "好 这个先放着", "你先按自己节奏来"]
        if expression_intent == "Opening":
            return ["刚看到", "在呢 怎么啦", "嗨 今天怎么样", "来了 找我呀", "刚忙完 你呢", "嗯 在的"]
        if expression_intent == "LifeCallback":
            pet_label = ReplyGenerator._pet_label(memory)
            return [
                f"{pet_label}今天又营业了是吧" if pet_label else "它今天又营业了是吧",
                "听着又气又想笑",
                "你现在是案发现场负责人",
                "它拆家 你善后",
                "给我看看现场",
                "这小家伙挺会折腾",
            ]
        if expression_intent == "Reassurance":
            base = ["先喘口气", "这波确实挺烦的", "别自己硬扛", "我听着 你慢慢说", "先站你这边", "把最烦那段丢给我"]
            return ["先别硬扛 把最烦那段丢给我", *base] if clear_lead else base
        if expression_intent == "PlayfulWarmth":
            return ["你这句有点意思", "别只丢半句 继续", "这语气有点可爱", "你这样我会惦记一下", "行 继续保持", "又开始偷偷撩我"]
        if expression_intent == "LowPressureInvite":
            return ["可以 周末哪天", "可以 先约轻松点", "那就找个顺路的", "你定时间 我定地方", "行 先不整复杂", "可以 看你哪天舒服"]
        if expression_intent == "SteadyReassurance":
            return ["你这句有点酸啊", "放心 没你想的那样", "这锅我先不背", "你要听真话吗", "我知道你在意啥", "别自己脑补太多"]
        if expression_intent == "SoftExit":
            return ["好 你先忙", "嗯 先不打扰你", "行 晚点再说", "收到 你先处理", "好 先这样", "你先按你的来"]
        return ["这句有点意思", "嗯？怎么说", "你继续 我听着", "别只丢半句", "刚看到 怎么了", "这话我得听后续"]

    @staticmethod
    def _season_variants(texts: list[str], personality: str, profile: Mapping[str, Any]) -> list[str]:
        """Apply small style seasoning without turning replies into templates."""
        if personality.startswith("克制型"):
            extras = ["先不急", "这个慢慢来", "你先舒服点"]
        elif personality.startswith("温暖型"):
            extras = ["我先接住", "别自己扛", "先站你这边"]
        elif personality.startswith("轻松型"):
            extras = ["有点可爱", "这句记下了", "你还挺会"]
        elif personality.startswith("清晰型"):
            extras = ["我来定一个轻的", "先别整复杂", "你定时间就行"]
        else:
            extras = ["继续", "怎么说", "我听着"]

        result = [*texts]
        for extra in extras:
            if extra not in result:
                result.append(extra)
        return result

    @classmethod
    def _is_invite_text(cls, text: str) -> bool:
        normalized = str(text).lower()
        return any(phrase in normalized for phrase in cls.INVITE_PHRASES)

    @classmethod
    def _has_explicit_invite_signal(cls, chat_history: Sequence) -> bool:
        latest = cls._latest_text(chat_history).lower()
        return any(phrase in latest for phrase in cls.EXPLICIT_INVITE_SIGNALS)

    @staticmethod
    def _is_early_stage(relationship_state: Mapping[str, Any]) -> bool:
        stage = str(relationship_state.get("stage", "L1"))
        try:
            favorability = float(relationship_state.get("favorability_score", 0) or 0)
        except (TypeError, ValueError):
            favorability = 0.0
        return stage in {"L1", "L2"} or favorability < 35

    @staticmethod
    def _format_history(chat_history: Sequence) -> str:
        lines = []
        for item in chat_history[-10:]:
            if isinstance(item, str):
                lines.append(f"她：{item}")
            else:
                role = str(item.get("role", "user"))
                speaker = "我" if role in {"assistant", "me", "boy"} else "她"
                content = str(item.get("content", ""))
                lines.append(f"{speaker}：{content}")
        return "\n".join(lines)

    @staticmethod
    def _clean_line(line: str) -> str:
        text = re.sub(r"^\s*[-*\d.、）)]+\s*", "", line).strip()
        text = text.strip("\"'“”")
        text = re.sub(r"\s+", " ", text)
        
        # 核心优化：只剔除句末死板的书面标点（。和，），保留极其重要的语气标点（？和！）
        text = re.sub(r"[。，,.]+$", "", text)
        return text[:55].strip()

    @staticmethod
    def _dedupe(candidates: Sequence[ReplyCandidate]) -> list[ReplyCandidate]:
        seen = set()
        result = []
        for c in candidates:
            key = re.sub(r"\W+", "", c.text.lower())
            if c.text.strip() and key not in seen:
                seen.add(key)
                result.append(c)
        return result

    @staticmethod
    def _stable_offset(value: str) -> int:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
        return int(digest[:2], 16) % 6

    @staticmethod
    def _latest_text(chat_history: Sequence) -> str:
        if not chat_history:
            return ""
        latest = chat_history[-1]
        if isinstance(latest, str):
            return latest
        return str(latest.get("content", latest.get("text", "")))

    @staticmethod
    def _profile(memory: Mapping[str, Any] | None) -> dict[str, Any]:
        if not isinstance(memory, Mapping):
            return {}
        profile = memory.get("profile", {})
        return dict(profile) if isinstance(profile, Mapping) else {}

    @staticmethod
    def _format_profile(profile: Mapping[str, Any]) -> str:
        if not profile:
            return "- 暂无画像，先观察反馈"
        preferred = profile.get("preferred_feedback", [])
        avoided = profile.get("avoided_moves", [])
        return "\n".join(
            [
                f"- 类型: {profile.get('label', '平衡观察型')}",
                f"- 推进节奏: {profile.get('progression_pace', 1.0)}",
                f"- 接受带领: {profile.get('leadership_preference', 50)}",
                f"- 需要确定感: {profile.get('reassurance_need', 50)}",
                f"- 调侃接受度: {profile.get('playfulness', 50)}",
                f"- 边界敏感度: {profile.get('boundary_sensitivity', 50)}",
                f"- 优先反馈: {', '.join(preferred[:3]) if isinstance(preferred, list) and preferred else '观察'}",
                f"- 避免动作: {', '.join(avoided[:3]) if isinstance(avoided, list) and avoided else '无'}",
            ]
        )

    @staticmethod
    def _pet_label(memory: Mapping[str, Any] | None) -> str:
        if not isinstance(memory, Mapping):
            return ""
        pets = memory.get("pets", [])
        if not isinstance(pets, list) or not pets:
            return ""
        pet = pets[0]
        if not isinstance(pet, Mapping):
            return ""
        return str(pet.get("breed") or pet.get("name") or pet.get("species") or "").strip()


def _demo() -> None:
    from emotion_agent.strategy.strategy_planner import StrategyPlanner, ConversationAnalysis
    # 模拟输入高脆弱度+高性张力环境下的回复生成
    plan = StrategyPlanner().plan(ConversationAnalysis(intent="撒娇", vulnerability=75, sexual_tension=60))
    replies = ReplyGenerator().generate(["今天好累，想你抱抱"], plan, {"stage": "L4"}, {})
    for r in replies:
        print(f"[{r.source}] -> {r.text}")


if __name__ == "__main__":
    _demo()
