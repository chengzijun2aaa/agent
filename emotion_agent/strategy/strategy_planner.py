"""Strategy Planner - natural romantic progression decisions."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.conversation_analyzer import ConversationAnalysis
from emotion_agent.analyzers.risk_detector import RiskReport


class BehaviorProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    warmth: int = Field(default=50)
    responsiveness: int = Field(default=50)
    playfulness: int = Field(default=50)
    guardedness: int = Field(default=50)
    emotional_need: int = Field(default=50)
    vulnerability: int = Field(default=0)


class ReplyPlan(BaseModel):
    """动态行动计划"""
    model_config = ConfigDict(extra="ignore")

    objective: str
    tone: str
    action_type: str = "推进"          # 接情绪 / 调侃 / 后撤 / 推进 / 邀约 / 结束
    emotional_need: str = "被看见"
    relationship_move: str = "自然推进"
    tactics: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    target_length: str = "medium"
    candidate_count: int = 8
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)


class StrategyPlanner:
    """Choose a reply direction that avoids friend-zone style over-comforting."""

    def plan(
        self,
        analysis: Any,
        *args: Any,
        relationship_state: Mapping[str, Any] | None = None,
        memory: Mapping[str, Any] | None = None,
        risk: Any | None = None,
        profile: Any | None = None,
    ) -> ReplyPlan:
        if args:
            relationship_state = args[0] if len(args) >= 1 and isinstance(args[0], Mapping) else relationship_state
            memory = args[1] if len(args) >= 2 and isinstance(args[1], Mapping) else memory
            risk = args[2] if len(args) >= 3 else risk
        relationship_state = relationship_state or {}
        memory = memory or {}
        analysis_obj = self._coerce_analysis(analysis)
        profile_data = self._coerce_profile(memory=memory, explicit_profile=profile)
        
        user_text = str(getattr(analysis_obj, "user_raw_text", "") or "").lower()
        intent = getattr(analysis_obj, "intent", "分享生活")
        stage = str(relationship_state.get("stage", getattr(analysis_obj, "relationship_stage", "L1")))
        favorability = float(relationship_state.get("favorability_score", 0) or 0)
        initiative = float(relationship_state.get("initiative", 0) or 0)
        invitation = float(relationship_state.get("invitation_willingness", 0) or 0)
        dependence = float(relationship_state.get("emotional_dependence", 0) or 0)
        
        vuln = getattr(analysis_obj, "vulnerability", 50)
        sexual_tension = getattr(analysis_obj, "sexual_tension", 0)
        compliance = getattr(analysis_obj, "compliance", 0)
        escalation = getattr(analysis_obj, "escalation_window", "low")
        favor_release = getattr(analysis_obj, "favor_release", 0)
        leadership_preference = int(profile_data.get("leadership_preference", 50) or 50)
        reassurance_need = int(profile_data.get("reassurance_need", 50) or 50)
        playfulness = int(profile_data.get("playfulness", 50) or 50)
        sensitivity = int(profile_data.get("sensitivity", 50) or 50)
        boundary_sensitivity = int(profile_data.get("boundary_sensitivity", 50) or 50)
        progression_pace = float(profile_data.get("progression_pace", 1.0) or 1.0)
        preferred_feedback = [str(item) for item in profile_data.get("preferred_feedback", []) if str(item).strip()]
        avoided_moves = [str(item) for item in profile_data.get("avoided_moves", []) if str(item).strip()]
        profile_label = str(profile_data.get("label", "平衡观察型") or "平衡观察型")
        boundary_cautious = boundary_sensitivity >= 70 or progression_pace <= 0.85

        progress_ready = (
            stage in {"L2", "L3", "L4", "L5", "L6"}
            or favorability >= 15
            or initiative >= 30
            or invitation >= 45
            or dependence >= 40
        )
        if boundary_cautious and invitation < 60 and stage not in {"L4", "L5", "L6"}:
            progress_ready = favorability >= 30 or dependence >= 55 or initiative >= 45

        # ==================== 核心行动决策 ====================
        if intent in {"求安慰", "抱怨", "分享情绪", "工作压力"} or vuln >= 70:
            # 先接住，再把关系从树洞拉回男女互动。
            objective = "接住情绪，同时给一点偏爱和下一步"
            tone = "稳、温柔、带一点男友感"
            if leadership_preference >= 65:
                tone = "稳、温柔、清晰安排"
            action_type = "接情绪推进" if progress_ready else "接情绪"
            tactics = [
                "先承接她的情绪，不讲大道理",
                "第二句给偏爱感，不只当树洞",
                "能推进时自然带到见面、陪她放松、下次带她缓一缓",
                "避免连续追问和纯陪聊"
            ]

        elif intent in {"撒娇", "性暗示"} or sexual_tension >= 65:
            # 调情要轻，不跳过对方反馈。
            objective = "接住撒娇，同时把暧昧感往见面和偏爱推进"
            tone = "松弛、轻暧昧、有一点占有感"
            if boundary_cautious:
                tone = "松弛、轻暧昧、不过界"
            action_type = "轻暧昧推进"
            tactics = [
                "先回应她的撒娇，不立刻讲道理",
                "给一句偏爱或轻调侃",
                "把话题落到下次见面、抱一下、带她放松等低压力场景",
                "不越过明确边界"
            ]

        elif intent in {"邀约", "释放好感"} or (stage in {"L4", "L5"} and favor_release >= 60):
            # 该推进 / 邀约
            objective = "趁热打铁推进关系"
            tone = "果断 + 带领"
            action_type = "推进"
            tactics = [
                "明确接受邀约并主导细节",
                "给出具体时间或地点方向",
                "加一点见面后的轻松期待，不写成商务确认"
            ]

        elif intent in {"测试", "框架挑战", "吃醋"}:
            # 该调侃 / 框架战
            objective = "稳住框架，同时释放在意感"
            tone = "戏谑 + 稳定 + 有一点偏爱"
            if playfulness < 45 or sensitivity >= 70:
                tone = "稳、轻松、少开冒犯玩笑"
            action_type = "调侃"
            tactics = [
                "先不慌不解释",
                "用轻调侃接住她的试探",
                "最后给一点确定感，避免聊成对抗"
            ]

        elif intent in {"冷淡", "敷衍", "撤退"}:
            # 该后撤 / 结束话题
            objective = "优雅后撤，保留吸引力"
            tone = "松弛 + 神秘"
            action_type = "后撤"
            tactics = [
                "短回复 + 留钩子",
                "降低需求感",
                "让她下次主动找你"
            ]

        else:  # 默认
            if progress_ready:
                objective = "避免纯闲聊，把话题轻轻往暧昧或见面推进"
                tone = "松弛 + 轻暧昧 + 有方向"
                if leadership_preference >= 65:
                    tone = "松弛 + 清晰带领 + 有方向"
                action_type = "轻暧昧推进"
                tactics = [
                    "抓住她的话题做一句回应",
                    "加一点男女感，不只做朋友式陪聊",
                    "能自然邀约时给一个轻量见面钩子"
                ]
            else:
                objective = "建立吸引，先让聊天有轻松张力"
                tone = "风趣 + 不急不贴"
                action_type = "调侃"
                tactics = [
                    "轻松接话",
                    "避免查岗式追问",
                    "留下下一句能回的口子"
                ]

        if boundary_cautious and action_type in {"推进", "轻暧昧推进", "接情绪推进"}:
            tactics.append("她对边界或节奏更敏感，推进要用选择题和低压力安排，不用压迫感")
        if leadership_preference >= 65:
            tactics.append("画像提示：她更接受清晰带领，回复里可以给安排、给方向、给收场")
        if reassurance_need >= 65:
            tactics.append("画像提示：她需要确定感，先稳住情绪再推进，别只开玩笑")
        if playfulness >= 65:
            tactics.append("画像提示：她能接轻调侃，可以让回复更像真实微信互动")
        if preferred_feedback:
            tactics.append(f"优先反馈: {' / '.join(preferred_feedback[:3])}")
        if avoided_moves:
            tactics.append(f"避免动作: {' / '.join(avoided_moves[:3])}")

        tactics.extend([
            f"当前阶段: {stage} | Intent: {intent} | 好感度: {favorability:.1f} | 主动性: {initiative:.1f} | 画像: {profile_label}",
            "不要连续三轮只安慰或只问问题",
            "每次回复尽量包含：接她的话 + 一点态度 + 一个轻推进",
            "主导感=稳定、清楚、有安排，不是命令、压迫或替对方做决定"
        ])

        return ReplyPlan(
            objective=objective,
            tone=tone,
            action_type=action_type,
            emotional_need="被接住，同时感到被偏爱",
            relationship_move="自然推进关系",
            tactics=self._dedupe(tactics),
            avoid=["纯高情商废话", "过度共情不推进", "闺蜜式陪聊", "连续查岗追问", "安全平淡回复"],
            target_length="medium",
            candidate_count=8,
            behavior_profile=BehaviorProfile(
                warmth=70 if reassurance_need >= 65 else 55,
                responsiveness=65 if initiative >= 30 else 50,
                playfulness=playfulness,
                guardedness=boundary_sensitivity,
                emotional_need=reassurance_need,
                vulnerability=vuln,
            ),
        )

    # ==================== 兼容方法（保持不变） ====================
    @staticmethod
    def _coerce_analysis(value: Any) -> ConversationAnalysis:
        if isinstance(value, ConversationAnalysis):
            return value
        if isinstance(value, Mapping):
            try:
                return ConversationAnalysis.model_validate(value)
            except:
                pass
        return ConversationAnalysis(
            intent=str(getattr(value, "intent", "分享生活")),
            vulnerability=int(getattr(value, "vulnerability", 50)),
            sexual_tension=int(getattr(value, "sexual_tension", 0)),
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen = set()
        result = []
        for v in values:
            text = str(v).strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result

    @staticmethod
    def _coerce_profile(
        *,
        memory: Mapping[str, Any] | None,
        explicit_profile: Any | None,
    ) -> dict[str, Any]:
        """Read the per-person interaction profile from memory or an explicit value."""
        if isinstance(explicit_profile, Mapping):
            return dict(explicit_profile)
        if explicit_profile is not None and hasattr(explicit_profile, "summary"):
            summary = explicit_profile.summary()
            return dict(summary) if isinstance(summary, Mapping) else {}
        if not isinstance(memory, Mapping):
            return {}
        profile = memory.get("profile", {})
        return dict(profile) if isinstance(profile, Mapping) else {}


def _demo() -> None:
    planner = StrategyPlanner()
    plan = planner.plan(
        ConversationAnalysis(
            intent="撒娇",
            emotion="委屈",
            vulnerability=80,
            sexual_tension=65,
            relationship_stage="L4"
        )
    )
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
