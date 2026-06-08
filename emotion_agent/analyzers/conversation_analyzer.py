"""Conversation-level analyzer for recent WeChat chat history."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import json
import re
from typing import Any, Mapping, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.utils.types import AgentContext, Message, SenderRole


ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message | ChatMessage"
ChatHistory: TypeAlias = "Sequence[ChatHistoryItem]"


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str = Field(default=SenderRole.USER.value)
    content: str = Field(default="")


class ConversationAnalysis(BaseModel):
    """Structured conversation analysis used by planning and generation."""
    model_config = ConfigDict(extra="ignore")

    emotion: str = Field(default="neutral")
    intent: str = Field(default="分享生活")
    interest_score: int = Field(default=0, ge=0, le=100)
    relationship_stage: str = Field(default="L1")
    escalation_window: str = Field(default="low")  # low/medium/high
    user_raw_text: str = Field(default="")

    # Compatibility metrics used by existing planners.
    vulnerability: int = Field(default=0, ge=0, le=100)      # 情感脆弱度
    sexual_tension: int = Field(default=0, ge=0, le=100)    # 暧昧/亲近信号
    compliance: int = Field(default=0, ge=0, le=100)        # 配合度
    favor_release: int = Field(default=0, ge=0, le=100)     # 好感释放度


class ConversationAnalysisPromptTemplate:
    """Prompt template for LLM-first intent and relationship analysis."""

    SUPPORTED_INTENTS: tuple[str, ...] = (
        "分享生活", "撒娇", "调侃", "测试", "冷淡", "敷衍", "撤退",
        "吃醋", "抱怨", "邀约", "求安慰", "分享情绪", "工作压力",
        "性暗示", "服从测试", "框架挑战", "寻求支配", "释放好感"
    )

    INTENT_PROMPTS: Mapping[str, str] = {
        "分享生活": "主动分享日常、吃喝、行程、宠物、朋友或小事",
        "撒娇": "卖萌、哼、讨厌你、抱抱、想你、委屈求照顾",
        "调侃": "打趣、开玩笑、哈哈、逗你",
        "测试": "试探你是否在意、是否稳定、是否认真",
        "冷淡": "回复慢、短、哦嗯、降温、回避",
        "敷衍": "随便、行吧、哦、呵呵、晚点说",
        "撤退": "算了、不重要、没事、别聊了、先忙",
        "吃醋": "她是谁、别的女生、占有欲、酸",
        "抱怨": "吐槽、压力、委屈、烦、没人懂",
        "邀约": "见面、吃饭、出来、周末、有空吗",
        "求安慰": "哄我、抱抱、难受、陪我",
        "分享情绪": "开心/难过/焦虑/生气等情绪表达",
        "工作压力": "加班、老板、崩溃、硬撑",
        "性暗示": "洗澡、好热、睡觉、穿什么、坏、想你抱",
        "服从测试": "听你的、随便你、你决定、嗯嗯",
        "框架挑战": "凭什么、你坏、才不要、哼",
        "寻求支配": "你好坏、带我、管我、怎么办",
        "释放好感": "主动夸你、想你、关心你、给你特殊待遇",
    }

    STAGE_DESC: Mapping[str, str] = {
        "L1": "陌生/开场",
        "L2": "熟悉/破冰",
        "L3": "高频吸引",
        "L4": "暧昧",
        "L5": "线下推进",
        "L6": "稳定亲密"
    }

    def build(self, chat_history: Sequence[ChatMessage]) -> str:
        formatted_history = self._format_history(chat_history)
        intent_definitions = "\n".join(f"- {intent}: {desc}" for intent, desc in self.INTENT_PROMPTS.items())
        stage_definitions = "\n".join(f"- {stage}: {desc}" for stage, desc in self.STAGE_DESC.items())

        return (
            "你是一个精准的微信恋爱对话分析器。目标是判断对方情绪、意图、好感信号和适合的自然推进节奏。\n\n"
            "任务：对最近对话进行结构化分析\n"
            "1. emotion：当前核心情绪（sexual_interest / vulnerable / needy / playful / annoyed 等）\n"
            f"2. intent：必须从以下列表中选**最匹配的一个**：{list(self.INTENT_PROMPTS.keys())}\n"
            "3. interest_score：0-100（越高代表越愿意继续互动）\n"
            f"4. relationship_stage：严格使用 L1-L6\n"
            "5. escalation_window：low/medium/high（high=可以更明确表达好感或敲定见面，但仍需低压力）\n"
            "6. 输出 vulnerability、sexual_tension、compliance、favor_release 四个0-100分数\n"
            "注意：分析不要建议压迫、操控或跳过对方反馈。\n\n"
            f"意图详细说明：\n{intent_definitions}\n\n"
            f"阶段说明：\n{stage_definitions}\n\n"
            "输出**严格JSON**，不要任何解释、不要Markdown：\n"
            '{\n'
            '  "emotion": "", "intent": "", "interest_score": 0, "relationship_stage": "",\n'
            '  "escalation_window": "", "user_raw_text": "",\n'
            '  "vulnerability": 0, "sexual_tension": 0, "compliance": 0, "favor_release": 0\n'
            '}\n\n'
            f"最近聊天记录：\n{formatted_history}"
        )

    @staticmethod
    def _format_history(chat_history: Sequence[ChatMessage]) -> str:
        if not chat_history:
            return "(empty)"
        result = []
        for i, msg in enumerate(chat_history, 1):
            role = "男主" if msg.role in ("assistant", "me", "boy", "我") else "女生"
            result.append(f"{i}. {role}: {msg.content}")
        return "\n".join(result)


class ConversationAnalyzer(BaseAnalyzer):
    """LLM-first analyzer with rule fallback for WeChat-style chats."""

    def __init__(self, llm: Any | None = None, max_history: int = 20):
        self.llm = llm
        self.max_history = max_history
        self.prompt_template = ConversationAnalysisPromptTemplate()

    @property
    def name(self) -> str:
        return "conversation"

    def analyze(self, chat_history: ChatHistory | AgentContext) -> ConversationAnalysis:
        messages = self._normalize_history(chat_history)[-self.max_history:]

        if self.llm is not None:
            llm_result = self._analyze_with_llm(messages)
            if llm_result:
                return llm_result

        return self._analyze_with_rules(messages)

    # _analyze_with_llm、_parse_analysis_json 等方法保持原样（可复用之前版本）

    def _analyze_with_rules(self, chat_history: Sequence[ChatMessage]) -> ConversationAnalysis:
        """规则增强版 - 更细粒度"""
        user_messages = self._user_messages(chat_history)
        joined_text = "\n".join(m.content for m in user_messages).lower()
        latest = self._latest_user_text(chat_history).lower()

        intent_scores = self._score_intents(joined_text, latest)
        best_intent = max(intent_scores, key=intent_scores.get) if intent_scores else "分享生活"
        intent = best_intent if intent_scores.get(best_intent, 0) > 0 else "分享生活"

        interest_score = self._interest_score(user_messages, intent)
        vulnerability = self._calculate_vulnerability(joined_text, latest)
        sexual_tension = self._calculate_sexual_tension(joined_text, latest)
        compliance = self._calculate_compliance(joined_text, latest)
        favor_release = self._calculate_favor_release(joined_text, latest)

        return ConversationAnalysis(
            emotion=self._emotion(joined_text, intent),
            intent=intent,
            interest_score=interest_score,
            relationship_stage=self._relationship_stage(user_messages, intent, interest_score),
            escalation_window=self._escalation_window(vulnerability, sexual_tension, compliance, favor_release),
            user_raw_text=self._latest_user_text(chat_history),
            vulnerability=vulnerability,
            sexual_tension=sexual_tension,
            compliance=compliance,
            favor_release=favor_release,
        )

    def _score_intents(self, joined_text: str, latest: str) -> dict[str, int]:
        """Score supported intents with latest-message priority."""
        keywords_map: Mapping[str, tuple[str, ...]] = {
            "工作压力": ("加班", "老板", "同事", "工作", "项目", "催", "绩效", "会议", "客户", "烦死"),
            "邀约": ("见面", "吃饭", "出来", "周末", "有空", "一起", "看电影", "喝咖啡", "去哪"),
            "吃醋": ("别的女生", "别的女人", "她是谁", "和别人", "聊得开心", "是不是喜欢", "吃醋"),
            "求安慰": ("哄我", "抱抱", "陪我", "安慰", "难受", "想哭", "委屈"),
            "抱怨": ("烦", "无语", "吐槽", "气死", "受不了", "崩溃", "破防"),
            "分享情绪": ("开心", "难过", "焦虑", "生气", "失落", "emo", "不开心"),
            "冷淡": ("忙", "没空", "再说", "晚点", "不想说", "不知道"),
            "敷衍": ("哦", "嗯", "行吧", "呵呵", "随便", "都行"),
            "撤退": ("算了", "没事", "不重要", "不聊了", "先忙", "不用回"),
            "调侃": ("哈哈", "逗你", "开玩笑", "你猜", "笨", "坏"),
            "测试": ("你是不是", "会不会", "在不在意", "如果我", "你敢", "凭什么"),
            "撒娇": ("想你", "抱抱", "哼", "讨厌你", "委屈", "撒娇", "不管"),
            "性暗示": ("洗澡", "好热", "睡觉", "穿什么", "色", "坏坏"),
            "服从测试": ("听你的", "随便你", "你决定", "你说了算", "都听你"),
            "框架挑战": ("凭什么", "才不要", "你管我", "你坏", "我偏不"),
            "寻求支配": ("带我", "管我", "怎么办", "你安排", "听你的"),
            "释放好感": ("你真好", "只有你", "特别", "关心你", "想你", "等你"),
            "分享生活": ("今天", "刚刚", "吃了", "猫", "狗", "朋友", "家里", "路上", "买了"),
        }
        scores: dict[str, int] = {intent: 0 for intent in keywords_map}
        for intent, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in latest:
                    scores[intent] += 18
                elif keyword in joined_text:
                    scores[intent] += 6

        short_latest = re.sub(r"\s+", "", latest)
        if short_latest in {"你好", "hi", "hello", "哈喽", "在吗"}:
            scores["分享生活"] += 20
            for intent in ("撒娇", "调侃", "释放好感"):
                scores[intent] = 0
        if len(short_latest) <= 2 and short_latest in {"嗯", "哦", "好", "行"}:
            scores["敷衍"] += 25
        return scores

    @staticmethod
    def _calculate_vulnerability(text: str, latest: str) -> int:
        words = ["累", "难受", "委屈", "崩溃", "压力", "没人懂", "想哭"]
        return min(sum(25 for w in words if w in text or w in latest), 100)

    @staticmethod
    def _calculate_sexual_tension(text: str, latest: str) -> int:
        words = ["想你", "抱抱", "洗澡", "好热", "睡觉", "坏", "色", "讨厌你"]
        return min(sum(25 for w in words if w in text or w in latest), 100)

    @staticmethod
    def _calculate_compliance(text: str, latest: str) -> int:
        words = ["听你的", "随便你", "你决定", "嗯嗯", "好吧", "可以吗"]
        return min(sum(30 for w in words if w in text or w in latest), 100)

    @staticmethod
    def _calculate_favor_release(text: str, latest: str) -> int:
        words = ["想你", "你真好", "只有你", "特别", "关心你"]
        return min(sum(28 for w in words if w in text or w in latest), 100)

    def _escalation_window(self, vuln: int, sex: int, comp: int, favor: int) -> str:
        total = vuln + sex + comp + favor
        if total >= 220 or sex >= 70:
            return "high"
        elif total >= 140:
            return "medium"
        return "low"

    # 其他方法（_normalize_history, _latest_user_text 等）保持之前版本即可

    def _analyze_with_llm(self, chat_history: Sequence[ChatMessage]) -> ConversationAnalysis | None:
        """Analyze with the configured LLM provider when available."""
        if self.llm is None:
            return None
        try:
            prompt = self.prompt_template.build(chat_history)
            response = self.llm.analyze(prompt, temperature=0.2, max_tokens=500)
            content = str(getattr(response, "content", "") or "")
            if not getattr(response, "success", False) or not content:
                return None
            return self._parse_analysis_json(content, chat_history)
        except Exception:
            return None

    def _parse_analysis_json(
        self,
        content: str,
        chat_history: Sequence[ChatMessage],
    ) -> ConversationAnalysis | None:
        """Parse a JSON analysis payload from an LLM response."""
        try:
            match = re.search(r"\{.*\}", content, flags=re.S)
            payload = json.loads(match.group(0) if match else content)
            payload.setdefault("user_raw_text", self._latest_user_text(chat_history))
            return ConversationAnalysis.model_validate(payload)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    @staticmethod
    def _user_messages(chat_history: Sequence[ChatMessage]) -> list[ChatMessage]:
        """Return messages sent by the other person."""
        return [
            message
            for message in chat_history
            if str(message.role).lower() not in {"assistant", "me", "boy", "我"}
        ]

    @staticmethod
    def _latest_user_text(chat_history: Sequence[ChatMessage]) -> str:
        """Return the latest text sent by the other person."""
        for message in reversed(chat_history):
            if str(message.role).lower() not in {"assistant", "me", "boy", "我"}:
                return message.content
        return ""

    @staticmethod
    def _interest_score(user_messages: Sequence[ChatMessage], intent: str) -> int:
        """Estimate interest from message length, questions, and intent."""
        if not user_messages:
            return 0
        joined = "\n".join(message.content for message in user_messages)
        avg_len = sum(len(message.content) for message in user_messages) / len(user_messages)
        question_bonus = min(sum(message.content.count("？") + message.content.count("?") for message in user_messages) * 8, 24)
        intent_bonus = {
            "邀约": 30,
            "释放好感": 28,
            "撒娇": 22,
            "吃醋": 18,
            "求安慰": 15,
            "分享情绪": 12,
            "分享生活": 10,
            "调侃": 10,
            "测试": 8,
            "冷淡": -15,
            "敷衍": -20,
            "撤退": -28,
        }.get(intent, 5)
        length_bonus = min(avg_len * 1.2, 32)
        warmth_bonus = 10 if any(word in joined for word in ("哈哈", "想你", "谢谢", "开心", "周末", "一起")) else 0
        return int(max(0, min(100, 25 + question_bonus + intent_bonus + length_bonus + warmth_bonus)))

    @staticmethod
    def _emotion(text: str, intent: str) -> str:
        """Infer a coarse emotion label."""
        if any(word in text for word in ("累", "难受", "委屈", "崩溃", "想哭", "压力")):
            return "vulnerable"
        if intent in {"撒娇", "调侃", "释放好感"}:
            return "playful"
        if intent in {"冷淡", "敷衍", "撤退"}:
            return "guarded"
        if intent == "吃醋":
            return "jealous"
        return "neutral"

    @staticmethod
    def _relationship_stage(user_messages: Sequence[ChatMessage], intent: str, interest_score: int) -> str:
        """Infer a rough relationship stage from recent chat signals."""
        count = len(user_messages)
        if interest_score >= 80 and intent in {"释放好感", "邀约", "撒娇"}:
            return "L4"
        if interest_score >= 65 or count >= 8:
            return "L3"
        if interest_score >= 35 or count >= 2:
            return "L2"
        return "L1"

    @staticmethod
    def _normalize_history(chat_history: ChatHistory | AgentContext) -> list[ChatMessage]:
        if isinstance(chat_history, AgentContext):
            items = [*chat_history.recent_messages, chat_history.current_message]
        else:
            items = chat_history
        return [ConversationAnalyzer._normalize_item(item) for item in items]

    @staticmethod
    def _normalize_item(item: ChatHistoryItem) -> ChatMessage:
        if isinstance(item, ChatMessage):
            return item
        if isinstance(item, Message):
            return ChatMessage(role=item.role.value, content=item.content)
        if isinstance(item, str):
            return ChatMessage(role=SenderRole.USER.value, content=item)
        role = item.get("role", SenderRole.USER.value)
        content = item.get("content", item.get("text", ""))
        return ChatMessage(role=role, content=content)


def _demo() -> None:
    analyzer = ConversationAnalyzer()
    analysis = analyzer.analyze(["今天好累，想你抱抱我，哼～"])
    print(analysis.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
