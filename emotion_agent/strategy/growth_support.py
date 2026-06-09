"""Growth support helpers for coaching, opportunity, offline prep, and confidence."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.conversation_analyzer import ConversationAnalysis
from emotion_agent.analyzers.risk_detector import RiskReport
from emotion_agent.memory.memory_manager import ConfidenceMemory, ConfidenceWin
from emotion_agent.ranker.reply_ranker import ReplyScore
from emotion_agent.strategy.strategy_planner import ReplyPlan


class SocialCoachingReport(BaseModel):
    """Explanation that teaches the user why a reply works."""

    model_config = ConfigDict(extra="ignore")

    why_this_reply: str = ""
    send_note: str = ""
    learning_points: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    practice_tip: str = ""


class OpportunityReport(BaseModel):
    """Current opportunity judgment for the next relationship move."""

    model_config = ConfigDict(extra="ignore")

    action: str = "继续聊"
    confidence: int = Field(default=50, ge=0, le=100)
    reason: str = ""
    next_step: str = ""
    timing: str = ""
    should_stop: bool = False


class OfflineDatePlan(BaseModel):
    """Offline preparation plan for low-pressure in-person interaction."""

    model_config = ConfigDict(extra="ignore")

    readiness: str = "暂不急"
    preparation: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    cold_rescue: list[str] = Field(default_factory=list)
    closing_lines: list[str] = Field(default_factory=list)


class ConfidenceReport(BaseModel):
    """Confidence-building feedback for the user."""

    model_config = ConfigDict(extra="ignore")

    wins: list[str] = Field(default_factory=list)
    total_turns: int = 0
    total_wins: int = 0
    current_streak: int = 0
    strengths: list[str] = Field(default_factory=list)
    next_micro_action: str = ""
    encouragement: str = ""


class GrowthSupportResult(BaseModel):
    """Combined growth support output returned by the reply pipeline."""

    model_config = ConfigDict(extra="ignore")

    social_coach: SocialCoachingReport = Field(default_factory=SocialCoachingReport)
    opportunity: OpportunityReport = Field(default_factory=OpportunityReport)
    offline_assist: OfflineDatePlan = Field(default_factory=OfflineDatePlan)
    confidence: ConfidenceReport = Field(default_factory=ConfidenceReport)


class SocialCoach:
    """Explain replies in a way that helps the user learn the pattern."""

    def explain(
        self,
        *,
        final_reply: str,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
        risk: RiskReport,
        plan: ReplyPlan,
        opportunity: OpportunityReport,
    ) -> SocialCoachingReport:
        """Return a concise coaching explanation for the selected reply."""
        intent = analysis.intent
        stage = str(relationship_state.get("stage", "L1"))
        profile = self._profile(memory)
        learning_points: list[str] = []

        if intent in {"工作压力", "求安慰", "抱怨", "分享情绪"}:
            learning_points.append("先接情绪，再给一点方向，比直接讲道理更容易被接住。")
        if opportunity.action == "邀约":
            learning_points.append("对方给出窗口时，回复要具体一点，时间或安排至少落一个。")
        if opportunity.action in {"降温", "收住"}:
            learning_points.append("她降温时先稳住自己，少追问，给空间反而更体面。")
        if int(profile.get("leadership_preference", 50) or 50) >= 65:
            learning_points.append("她更能接受清晰安排，你可以给选择和收场，但别替她做决定。")
        if int(profile.get("boundary_sensitivity", 50) or 50) >= 65:
            learning_points.append("她对节奏更敏感，推进时用低压力选择题。")

        if not learning_points:
            learning_points.append("这句重点是短、自然、接住她的话，不把聊天变成面试。")

        avoid = ["连续追问", "长篇解释", "用模板化的“我理解你”"]
        if risk.risk_level != "low":
            avoid.append("在她脆弱时强行推进")
        if opportunity.should_stop:
            avoid.append("为了找话题硬聊")

        return SocialCoachingReport(
            why_this_reply=self._why_reply(final_reply, intent, opportunity.action, stage),
            send_note=self._send_note(final_reply, opportunity),
            learning_points=self._dedupe(learning_points),
            avoid=self._dedupe(avoid),
            practice_tip=self._practice_tip(intent=intent, action=opportunity.action, plan=plan),
        )

    @staticmethod
    def _why_reply(reply: str, intent: str, action: str, stage: str) -> str:
        """Build a short explanation for why the reply was selected."""
        if action == "邀约":
            return "这句把她给的机会落到了具体安排上，有推进感，也不显得急。"
        if action == "安抚":
            return "这句先站到她这边，再保留后续互动空间，避免变成说教。"
        if action in {"降温", "收住"}:
            return "这句降低需求感，让对方有空间，同时保住你的节奏。"
        if "安排" in reply or "定" in reply:
            return "这句有清晰带领感，适合当前阶段给一点方向。"
        return f"这句适合 {stage} 阶段：短、自然，先接住“{intent}”而不是急着表现。"

    @staticmethod
    def _send_note(reply: str, opportunity: OpportunityReport) -> str:
        """Tell the user how to send the reply."""
        if opportunity.action in {"降温", "收住"}:
            return "发完先别补第二句，等她回。"
        if len(reply) <= 12:
            return "可以直接发，别再额外解释。"
        return "可以原样发，语气保持轻松，不要连续追加。"

    @staticmethod
    def _practice_tip(*, intent: str, action: str, plan: ReplyPlan) -> str:
        """Return one small learning exercise."""
        if action == "邀约":
            return "练习：以后遇到邀约窗口，尝试用“时间 + 安排”回复。"
        if intent in {"工作压力", "求安慰", "抱怨"}:
            return "练习：先复述她最烦的一点，再给一句站队。"
        if action in {"降温", "收住"}:
            return "练习：对方冷时，把回复压到一句，不解释不追问。"
        return f"练习：记住本轮策略，{plan.action_type} 时先短句接话。"

    @staticmethod
    def _profile(memory: Mapping[str, Any]) -> dict[str, Any]:
        profile = memory.get("profile", {}) if isinstance(memory, Mapping) else {}
        return dict(profile) if isinstance(profile, Mapping) else {}

    @staticmethod
    def _dedupe(values: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = str(value).strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result


class OpportunityDetector:
    """Detect whether to continue, cool down, invite, comfort, or stop."""

    def detect(
        self,
        *,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
        risk: RiskReport,
        plan: ReplyPlan,
    ) -> OpportunityReport:
        """Return the best next action for the user."""
        intent = analysis.intent
        favorability = float(relationship_state.get("favorability_score", 0) or 0)
        invitation = float(relationship_state.get("invitation_willingness", 0) or 0)
        boundary = float(self._profile(memory).get("boundary_sensitivity", 50) or 50)

        if intent in {"冷淡", "敷衍", "撤退"} or boundary >= 75:
            return OpportunityReport(
                action="收住",
                confidence=82,
                reason="她现在反馈偏低或边界感更强，继续追问会显得急。",
                next_step="发一句短回复后等待，不追加解释。",
                timing="等她重新抛话题，或隔一段时间再自然开启。",
                should_stop=True,
            )

        if risk.vulnerability >= 70 or intent in {"工作压力", "求安慰", "抱怨", "分享情绪"}:
            return OpportunityReport(
                action="安抚",
                confidence=78,
                reason="她现在更需要先被接住，直接推进容易失焦。",
                next_step="先站队和安抚，再轻轻给一个后续陪伴钩子。",
                timing="等她情绪落下来后，再考虑邀约或转轻松话题。",
            )

        if intent == "邀约" or invitation >= 55 or ("推进" in plan.action_type and favorability >= 30):
            confidence = 86 if intent == "邀约" else 70
            return OpportunityReport(
                action="邀约",
                confidence=confidence,
                reason="对方已经给出见面或继续互动窗口，适合把话落到具体安排。",
                next_step="给一个低压力选择：时间、地点、活动三选一落地。",
                timing="这轮就可以推进，别拖成空聊。",
            )

        if favorability >= 35 or analysis.interest_score >= 60:
            return OpportunityReport(
                action="继续聊",
                confidence=72,
                reason="互动质量还可以，适合继续轻松接话并保留一点方向。",
                next_step="接她的话题，加一句态度，再留一个容易回复的口子。",
                timing="连续两三轮顺畅后，再看是否转邀约。",
            )

        return OpportunityReport(
            action="继续聊",
            confidence=60,
            reason="当前还在观察期，先建立熟悉感，不急着推进。",
            next_step="短句接话，减少查岗式问题。",
            timing="等她主动分享更多细节再推进。",
        )

    @staticmethod
    def _profile(memory: Mapping[str, Any]) -> dict[str, Any]:
        profile = memory.get("profile", {}) if isinstance(memory, Mapping) else {}
        return dict(profile) if isinstance(profile, Mapping) else {}


class OfflineDateAssistant:
    """Prepare the user for low-pressure offline interaction."""

    def prepare(
        self,
        *,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
        opportunity: OpportunityReport,
    ) -> OfflineDatePlan:
        """Build a practical offline date preparation plan."""
        favorability = float(relationship_state.get("favorability_score", 0) or 0)
        stage = str(relationship_state.get("stage", "L1"))
        ready = opportunity.action == "邀约" or favorability >= 40 or stage in {"L3", "L4", "L5", "L6"}
        topics = self._topics_from_memory(memory)

        if not ready:
            return OfflineDatePlan(
                readiness="暂不急",
                preparation=["先把线上聊天聊顺，不急着约。", "多记住她的生活细节，后面邀约才自然。"],
                topics=topics,
                cold_rescue=["刚才那个我有点好奇，你再讲讲。", "换个轻松点的，你今天最顺的一件事是什么？"],
                closing_lines=["你先忙，回头再聊。", "行，今天先到这，别太晚睡。"],
            )

        return OfflineDatePlan(
            readiness="可以准备",
            preparation=[
                "选低压力场景：咖啡、简餐、散步，不要一上来安排太满。",
                "提前想好一个备选地点，避免临时慌。",
                "见面目标不是表现完美，是让她觉得轻松、安全、好相处。",
            ],
            topics=topics,
            cold_rescue=[
                "我刚才有点卡壳，但你这个我是真想听。",
                "换个轻松的，你最近有什么小快乐？",
                "这个话题先记着，等会儿我再问你。",
            ],
            closing_lines=[
                "今天见你挺舒服的，下次换我安排个轻松点的。",
                "你到家跟我说一声。",
                "今天先这样，别太晚休息。",
            ],
        )

    @staticmethod
    def _topics_from_memory(memory: Mapping[str, Any]) -> list[str]:
        """Build topic suggestions from remembered facts."""
        topics: list[str] = []
        pets = memory.get("pets", []) if isinstance(memory, Mapping) else []
        if isinstance(pets, list) and pets:
            pet = pets[0] if isinstance(pets[0], Mapping) else {}
            label = str(pet.get("breed") or pet.get("species") or pet.get("name") or "宠物")
            topics.append(f"聊她的{label}，让她讲近况。")
        interests = memory.get("interests", []) if isinstance(memory, Mapping) else []
        if isinstance(interests, list):
            topics.extend(f"顺着她的兴趣聊：{item}" for item in interests[:2])
        dietary = memory.get("dietary_habits", []) if isinstance(memory, Mapping) else []
        if isinstance(dietary, list) and dietary:
            topics.append(f"点餐时照顾她的饮食习惯：{dietary[0]}")
        if not topics:
            topics = ["最近让她开心的小事。", "她平时放松的方式。", "她最近想去但还没去的地方。"]
        return topics[:4]


class ConfidenceTracker:
    """Record small wins so the user learns instead of depending on the app."""

    def update(
        self,
        confidence_memory: ConfidenceMemory,
        *,
        final_reply: str,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        opportunity: OpportunityReport,
        ranked: ReplyScore,
        risk: RiskReport,
    ) -> ConfidenceReport:
        """Update persistent confidence memory and return a user-facing report."""
        wins = self._wins(
            final_reply=final_reply,
            analysis=analysis,
            opportunity=opportunity,
            ranked=ranked,
            risk=risk,
        )
        confidence_memory.total_turns += 1
        if wins:
            confidence_memory.total_wins += len(wins)
            confidence_memory.current_streak += 1
        else:
            confidence_memory.current_streak = 0

        for win in wins:
            confidence_memory.recent_wins.insert(
                0,
                ConfidenceWin(
                    skill=self._skill_for_win(win),
                    detail=win,
                    evidence=final_reply,
                    created_at=datetime.now(timezone.utc),
                ),
            )
        confidence_memory.recent_wins = confidence_memory.recent_wins[:12]
        confidence_memory.strengths = self._merge_strengths(confidence_memory.strengths, wins)
        confidence_memory.updated_at = datetime.now(timezone.utc)

        return ConfidenceReport(
            wins=wins,
            total_turns=confidence_memory.total_turns,
            total_wins=confidence_memory.total_wins,
            current_streak=confidence_memory.current_streak,
            strengths=list(confidence_memory.strengths),
            next_micro_action=self._next_micro_action(analysis.intent, opportunity.action, relationship_state),
            encouragement=self._encouragement(wins, confidence_memory.current_streak),
        )

    @staticmethod
    def _wins(
        *,
        final_reply: str,
        analysis: ConversationAnalysis,
        opportunity: OpportunityReport,
        ranked: ReplyScore,
        risk: RiskReport,
    ) -> list[str]:
        """Detect what the user did right in this turn."""
        wins: list[str] = []
        if 2 <= len(final_reply) <= 24:
            wins.append("回复控制得比较短，像正常微信。")
        if ranked.pressure >= 75:
            wins.append("没有用压迫或命令语气。")
        if opportunity.action == "邀约" and any(word in final_reply for word in ("定", "安排", "周末", "时间", "地方")):
            wins.append("抓住了机会，把话落到了具体安排。")
        if analysis.intent in {"工作压力", "求安慰", "抱怨", "分享情绪"} and any(
            word in final_reply for word in ("别硬撑", "站你", "缓", "哄你", "我在", "别自己扛")
        ):
            wins.append("先接住了她的情绪，没有急着说教。")
        if opportunity.should_stop and len(final_reply) <= 8:
            wins.append("她降温时你收住了，没有追着问。")
        if risk.risk_level == "low" and not wins:
            wins.append("这轮保持了基本稳定，没有把聊天弄复杂。")
        return wins[:3]

    @staticmethod
    def _skill_for_win(win: str) -> str:
        if "具体安排" in win:
            return "清晰推进"
        if "情绪" in win:
            return "情绪承接"
        if "收住" in win:
            return "低需求感"
        if "压迫" in win:
            return "边界感"
        return "自然表达"

    @classmethod
    def _merge_strengths(cls, current: list[str], wins: list[str]) -> list[str]:
        strengths = list(current)
        for win in wins:
            skill = cls._skill_for_win(win)
            if skill in strengths:
                strengths.remove(skill)
            strengths.insert(0, skill)
        return strengths[:8]

    @staticmethod
    def _next_micro_action(intent: str, action: str, relationship_state: Mapping[str, Any]) -> str:
        if action == "邀约":
            return "下一步只需要确认一个变量：时间、地点或活动。"
        if action in {"降温", "收住"}:
            return "下一步是等，不补话，训练自己稳住。"
        if intent in {"工作压力", "求安慰", "抱怨"}:
            return "下一步先听她多说一句，再决定要不要转轻松。"
        if float(relationship_state.get("favorability_score", 0) or 0) >= 35:
            return "下一步可以留一个轻量见面钩子。"
        return "下一步练习短句接话，别急着证明自己。"

    @staticmethod
    def _encouragement(wins: list[str], streak: int) -> str:
        if streak >= 3:
            return "你已经连续几轮处理得不错，重点是稳住这个节奏。"
        if wins:
            return "这轮有做对的地方，记住这个手感。"
        return "这轮先别苛责自己，下一句只做一件小事就够。"


def _demo() -> None:
    """Run a small module smoke test."""
    analysis = ConversationAnalysis(intent="邀约", interest_score=70)
    opportunity = OpportunityDetector().detect(
        analysis=analysis,
        relationship_state={"stage": "L3", "favorability_score": 40, "invitation_willingness": 60},
        memory={},
        risk=RiskReport(),
        plan=ReplyPlan(objective="推进", tone="自然", action_type="推进"),
    )
    print(opportunity.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
