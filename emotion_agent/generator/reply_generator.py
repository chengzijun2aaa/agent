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
        
        return self._dedupe(candidates)[: plan.candidate_count or 6]

    def _generate_with_llm(self, chat_history, plan: ReplyPlan, relationship_state, memory) -> list[ReplyCandidate]:
        prompt = self._build_prompt(chat_history, plan, relationship_state, memory)
        response = self.llm.generate(prompt, temperature=0.92, max_tokens=480)
        
        if not getattr(response, "success", False) or not response.content:
            return []

        candidates = []
        for line in response.content.splitlines():
            text = self._clean_line(line)
            if text and len(text.strip()) >= 3:
                candidates.append(ReplyCandidate(text=text, source="llm"))
        return candidates

    def _build_prompt(self, chat_history, plan: ReplyPlan, relationship_state, memory) -> str:
        stage = str(relationship_state.get("stage", "L3"))
        favorability = float(relationship_state.get("favorability_score", 0) or 0)
        history = self._format_history(chat_history[-10:])
        action = getattr(plan, "action_type", "推进")
        profile = self._profile(memory)
        profile_lines = self._format_profile(profile)

        return f"""
你是一个真实、松弛、会聊天的男人，正在微信和女生聊天。

要求：
- 回复要极短、松弛、自然，像随手打的微信
- 多用短句、口语、留白、甚至不完整句
- 不要解释、不要说教、不要高情商模板、不要“懂你”“我理解”
- 先像真人，再像高情商助手；先接她的话，再给态度和方向
- 主导感=稳定、清楚、有安排、有收场，不是命令、压迫或替她决定
- 可以有一点调侃和张力，但要贴合她的话，不油、不硬推
- 根据以下行动类型调整语气：

当前行动类型：{action}
核心目标：{plan.objective}
语气方向：{plan.tone}
关系阶段：{stage}
好感度：{favorability:.1f}/100
她的互动画像：
{profile_lines}

聊天记录（最近的）：
{history}

直接生成 6-8 条回复，每条一行，只输出纯文本，不要编号，不要引号。
可以带表情，但别太多。
        注意：不要只安慰或只问问题。合适时带一点关系方向，比如“我带你去缓缓”“见面再说”“这句我记着”。
        底线：不替对方表达同意，不用命令或压迫语气，不把脆弱情绪当成冒犯推进的理由。
""".strip()

    @staticmethod
    def _generate_with_rules(chat_history, plan: ReplyPlan, relationship_state, memory) -> list[ReplyCandidate]:
        latest = ReplyGenerator._latest_text(chat_history).lower()
        action = getattr(plan, "action_type", "推进")
        objective = getattr(plan, "objective", "")
        profile = ReplyGenerator._profile(memory)
        leadership = int(profile.get("leadership_preference", 50) or 50)
        reassurance = int(profile.get("reassurance_need", 50) or 50)
        playfulness = int(profile.get("playfulness", 50) or 50)
        boundary = int(profile.get("boundary_sensitivity", 50) or 50)
        pace = float(profile.get("progression_pace", 1.0) or 1.0)
        clear_lead = leadership >= 65
        needs_reassurance = reassurance >= 65
        playful = playfulness >= 65
        boundary_cautious = boundary >= 70 or pace <= 0.85

        normalized_latest = re.sub(r"\s+", "", latest)
        if normalized_latest in {"你好", "hi", "hello", "哈喽", "在吗"}:
            base = [
                "你好，刚看到",
                "在呢，怎么啦",
                "嗨，今天怎么样",
                "来了，找我呀",
                "刚忙完，你呢",
                "嗯，在",
            ]
            if playful:
                base = ["来了，今天这么乖先打招呼", "嗯，在，找我干嘛", *base]
        elif any(w in latest for w in ("猫", "狗", "宠物", "拆家", "布偶")):
            pet_label = ReplyGenerator._pet_label(memory)
            base = [
                f"{pet_label}今天又营业了是吧" if pet_label else "它今天又营业了是吧",
                "听着又气又想笑",
                "你现在是案发现场负责人",
                "它拆家，你善后",
                "给我看看现场",
                "这小家伙挺会折腾",
            ]
            if clear_lead:
                base.insert(2, "先拍照留证据，我看看它战绩")
        elif action == "接情绪推进":
            base = [
                "先别硬撑，回头我带你去缓缓",
                "今天先靠我这边一会儿",
                "你先说，晚点我哄你",
                "这波我记着，见面给你补回来",
                "别自己扛，我在你这边",
                "先喘口气，剩下的慢慢说",
            ]
            if needs_reassurance:
                base = [
                    "先别自己扛，今天我站你这边",
                    "你先缓口气，晚点我带你换换脑子",
                    "这事确实耗你，先靠我这边一会儿",
                    *base,
                ]
            if clear_lead:
                base.insert(0, "先停一下，喝口水，最烦那段丢给我")
        elif any(w in latest for w in ("加班", "老板", "工作", "项目", "催", "压力", "烦死", "累", "难受", "委屈", "想哭")):
            base = [
                "今天这波确实挺耗你",
                "先别硬撑，回头带你缓缓",
                "听着就烦，先站你这边",
                "你先说，晚点我哄你",
                "这时候别自己扛",
                "先喘口气，剩下的见面慢慢说",
            ]
            if clear_lead:
                base = [
                    "先别硬扛，晚点我带你去缓缓",
                    "你先把最烦那段丢给我",
                    "今晚先别内耗，剩下的我陪你捋",
                    *base,
                ]
            if boundary_cautious:
                base = [
                    "今天这波确实挺耗你，先缓一下",
                    "你先喘口气，我陪你把这股劲放下来",
                    *base,
                ]
        elif any(w in latest for w in ("见面", "见一下", "周末", "周六", "周日", "有空", "一起", "吃饭", "出来", "电影", "咖啡", "喝一杯", "找天")):
            base = [
                "可以，周末哪天",
                "行啊，吃什么",
                "那就定一个时间",
                "可以，我来安排",
                "别光说，定一下",
                "周末可以，我来定地方",
            ]
            if clear_lead:
                base = [
                    "可以，我来定地方，你定时间",
                    "行，周末我安排个轻松点的",
                    "那就定了，你把时间给我",
                    *base,
                ]
            if boundary_cautious:
                base = [
                    "可以，先定个轻松点的",
                    "行啊，找个你舒服的时间",
                    "可以，不赶，先吃个饭",
                    "周末哪天方便",
                ]
        elif any(w in latest for w in ("别的女生", "别的女人", "她是谁", "那个女生", "女生是谁", "和别人", "聊得开心", "是不是喜欢", "吃醋", "对她也这样", "没那么在意")):
            base = [
                "你这句有点酸啊",
                "没有你想的那样，放心点",
                "你是在查我岗吗",
                "我主要不是在回你么",
                "这锅我先不背",
                "你要听真话还是好听的",
            ]
            if needs_reassurance:
                base = [
                    "酸归酸，位置给你留着呢",
                    "放心点，重点不是别人",
                    "你这句我接住了，不躲",
                    *base,
                ]
            if playful:
                base.insert(0, "你这醋味有点明显啊")
        elif any(w in latest for w in ("想你", "抱抱", "哄我", "陪我", "委屈", "撒娇", "哼")):
            base = [
                "过来，先抱一下",
                "行，先哄你",
                "你这句有点可爱",
                "别委屈，跟我说",
                "嗯，我在",
                "你先靠会儿，别逞强",
            ]
            if boundary_cautious:
                base = [
                    "行，先哄你一下",
                    "你先靠会儿，别逞强",
                    "我在，先别自己闷着",
                    *base,
                ]
            elif clear_lead:
                base = [
                    "过来，先哄你三分钟",
                    "行，今天先归我哄",
                    *base,
                ]
        elif action == "轻暧昧推进":
            base = [
                "这话适合见面说",
                "你这样我会惦记的",
                "行，先记你一笔",
                "下次见面再跟我讲",
                "你继续，我听着，不过别太可爱",
                "这句我先收下",
            ]
            if clear_lead:
                base = [
                    "这话先记着，见面再跟你算",
                    "行，下次见面你当面说",
                    "别光撩，回头见面说",
                    *base,
                ]
            if boundary_cautious:
                base = [
                    "这句我先收下，不逗太过",
                    "行，先记着，慢慢来",
                    "你继续，我听着",
                ]
        elif action == "后撤":
            base = [
                "行，你先忙",
                "嗯嗯",
                "好",
                "收到",
                "那你忙",
            ]
        else:
            base = [
                "然后呢",
                "你继续说",
                "这句展开讲讲",
                "我听着",
                "刚看到，怎么了",
                "嗯？",
            ]
            if clear_lead:
                base = [
                    "这句展开，我听重点",
                    "说重点，我在",
                    "然后呢，别只丢半句",
                    *base,
                ]

        offset = ReplyGenerator._stable_offset(latest)
        rotated = base[offset:] + base[:offset]
        return [ReplyCandidate(text=t, source="rules", metadata={"profile_label": profile.get("label", "")}) for t in rotated]

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
        return text[:55].rstrip("，。！？")

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
        """Return the remembered interaction profile."""
        if not isinstance(memory, Mapping):
            return {}
        profile = memory.get("profile", {})
        return dict(profile) if isinstance(profile, Mapping) else {}

    @staticmethod
    def _format_profile(profile: Mapping[str, Any]) -> str:
        """Format profile data for the LLM prompt."""
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
        """Return a compact remembered pet label for rule replies."""
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
    plan = StrategyPlanner().plan(ConversationAnalysis(intent="撒娇", vulnerability=75, sexual_tension=60))
    replies = ReplyGenerator().generate(["今天好累，想你抱抱"], plan, {"stage": "L4"}, {})
    for r in replies:
        print(r.text)


if __name__ == "__main__":
    _demo()
