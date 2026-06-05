"""Strategy planning for stage-aware emotional replies."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping
from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.conversation_analyzer import ConversationAnalysis
# 假设 RiskReport 包含风险等级和安全指令
class RiskReport(BaseModel):
    risk_level: str = "low"
    safety_instruction: str = "保持克制，不要过度卷入情绪"

class ReplyPlan(BaseModel):
    """Concrete plan used by the reply generator."""
    model_config = ConfigDict(extra="ignore")

    objective: str
    tone: str
    tactics: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    target_length: str = "short"
    candidate_count: int = 6  # 对齐生成层的6条候选

class StrategyPlanner:
    """Plans response strategy from analysis, relationship state, memory, and risk."""

    def plan(
        self,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
        risk: RiskReport,
    ) -> ReplyPlan:
        """Create a reply plan for downstream generation."""
        
        # 1. 提取核心信号
        stage = str(analysis.relationship_stage or relationship_state.get("stage", "L1"))
        intent = analysis.intent
        score = analysis.interest_score
        
        # 初始化基础配置
        tactics = [f"当前阶段：{stage}", f"意图倾向：{intent}"]
        avoid = ["自嗨式回复", "逻辑说教", "查户口", "反问施压", "长篇大论"]

        # ============================================================
        # 🚨 【拦截网 A：生成策略前强行过滤记忆源头】
        # ============================================================
        memory_info = self._memory_hint(memory)
        # 如果不是主动聊宠物，或者上游记忆里有猫，直接污染源切断，不注入 tactics
        if memory_info != "暂无" and "猫" not in memory_info and intent in {"分享生活", "闲聊", "寻找话题"}:
            tactics.append(f"背景参考：对方{memory_info}")

        # 2. 处理高风险场景
        if analysis.risk_level != "low" or risk.risk_level != "low":
            objective = "优先接住负面情绪，不评判，不建议，只提供安全陪伴。"
            tone = "温和、可靠、低压"
            tactics.append("使用情绪共振技术")
            avoid.extend(["暧昧推进", "开玩笑"])
            current_candidate_count = 6  # 👈 哪怕高风险也强制要 6 条，不给它变 3 条的机会
        else:
            # 3. 核心决策矩阵：根据意图匹配战术
            current_candidate_count = 6
            if intent in {"工作压力", "抱怨", "求安慰"}:
                objective = "情绪承接 + 战友感。"
                tone = "松弛、有温度、站她这边"
                tactics.append("吐槽那个让她烦的人/事，而不是教她怎么做")
            elif intent in {"分享生活", "调侃", "分享情绪"}:
                if score >= 70:
                    objective = "同频放大，适当拉扯，增加暧昧浓度。"
                    tone = "俏皮、自信、带点攻击性(互损)"
                    tactics.append("捕捉对方话里的槽点进行反击")
                else:
                    objective = "正向反馈，鼓励对方继续表达。"
                    tone = "好奇、捧哏、轻松"
                    tactics.append("针对她分享的细节提一个好玩的开放式问题")
            elif intent == "测试":
                objective = "不自证，幽默破局，拿回框架。"
                tone = "高价值、半真半假、不卑不亢"
                tactics.append("用幽默反弹对方的试探")
            elif intent == "邀约":
                objective = "爽快答应，并明确下一步动作。"
                tone = "大方、有期待感、行动导向"
            elif intent == "冷淡" or score < 40:
                objective = "礼貌离场，不纠缠，保持姿态。"
                tone = "平静、高冷、不卑不亢"
                tactics.append("提供撤退信号，结束本次对话")
            else:
                objective = "保持连接，发现新话题。"
                tone = "随性、朋友感、无压力"

        # 4. 根据阶段修正
        if stage in {"L1", "L2"}:
            avoid.extend(["越位关心", "过度暧昧"])

        # ============================================================
        # 🔥【拦截网 B：兜底物理防猫墙，天王老子来了也得过滤】
        # ============================================================
        # 无论走哪个分支，最后在这里统一清洗
        tactics = [t for t in tactics if "猫" not in t]
        
        user_text = getattr(analysis, "user_raw_text", "") or ""
        if "猫" not in user_text and intent != "宠物话题":
            avoid.append("绝对不要主动提起‘猫’或任何宠物话题（包括猫咪今天乖不乖等询问，坚决禁止）")
        # ============================================================

        return ReplyPlan(
            objective=objective,
            tone=tone,
            tactics=tactics,
            avoid=avoid,
            candidate_count=current_candidate_count
        )

    @staticmethod
    def _memory_hint(memory: Mapping[str, Any]) -> str:
        """Build a compact memory hint."""
        city = memory.get("city")
        pets = memory.get("pets", [])
        if city: 
            return f"在{city}"
        if pets: 
            first_pet = pets[0]
            breed = first_pet.get("breed") if isinstance(first_pet, dict) else first_pet
            return f"养了一只{breed or '宠物'}"
        return "暂无"
def _demo() -> None:
    """Run a small module smoke test."""
    planner = StrategyPlanner()
    # 测试场景：对方在抱怨工作压力
    analysis = ConversationAnalysis(
        intent="工作压力", 
        emotion="烦躁", 
        interest_score=55, 
        relationship_stage="L3", 
        risk_level="low"
    )
    plan = planner.plan(analysis, {"stage": "L3"}, {}, RiskReport())
    print(f"Objective: {plan.objective}")
    print(f"Tactics: {plan.tactics}")
    print(f"Avoid: {plan.avoid}")

if __name__ == "__main__":
    _demo()