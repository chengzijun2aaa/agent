"""End-to-end emotional reply pipeline - Refactored Topology Version"""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.conversation_analyzer import ConversationAnalysis, ConversationAnalyzer
from emotion_agent.analyzers.risk_detector import RiskDetector, RiskReport
from emotion_agent.generator.reply_generator import ReplyCandidate, ReplyGenerator
from emotion_agent.humanizer.humanizer import Humanizer
from emotion_agent.memory.memory_manager import MemoryManager
from emotion_agent.ranker.reply_ranker import ReplyRanker, ReplyScore
from emotion_agent.state.relationship_state_machine import RelationshipStateMachine
from emotion_agent.strategy.growth_support import (
    ConfidenceTracker,
    GrowthSupportResult,
    OfflineDateAssistant,
    OpportunityDetector,
    SocialCoach,
)
from emotion_agent.strategy.strategy_planner import ReplyPlan, StrategyPlanner


class ReplyPipelineResult(BaseModel):
    """Structured result emitted by the full reply pipeline."""

    model_config = ConfigDict(extra="ignore")

    final_reply: str
    analysis: ConversationAnalysis
    relationship_state: dict[str, Any]
    memory: dict[str, Any]
    risk: RiskReport
    plan: ReplyPlan
    candidates: list[ReplyCandidate] = Field(default_factory=list)
    ranked: ReplyScore
    growth_support: GrowthSupportResult = Field(default_factory=GrowthSupportResult)


class ReplyPipeline:
    """Runs analysis, state, memory, risk, strategy, generation, humanization, and ranking."""

    def __init__(
        self,
        *,
        llm: Any | None = None,
        memory_path: str | Path = "memory.json",
        relationship_machine: RelationshipStateMachine | None = None,
    ) -> None:
        """Create a reply pipeline with optional LLM and state dependencies."""
        self.analyzer = ConversationAnalyzer(llm=llm)
        self.relationship_machine = relationship_machine or RelationshipStateMachine()
        self.memory_manager = MemoryManager(memory_path)
        self.risk_detector = RiskDetector()
        self.strategy_planner = StrategyPlanner()
        self.reply_generator = ReplyGenerator(llm=llm)
        self.humanizer = Humanizer()
        self.reply_ranker = ReplyRanker()
        self.opportunity_detector = OpportunityDetector()
        self.social_coach = SocialCoach()
        self.offline_assistant = OfflineDateAssistant()
        self.confidence_tracker = ConfidenceTracker()
        self.llm = llm

    def run(self, chat_history: Sequence[str | Mapping[str, Any]]) -> ReplyPipelineResult:
        """Run the full reply pipeline with strict, leak-free sequential data topology."""
        if not chat_history:
            raise ValueError("Chat history cannot be empty.")

        # 🚀 步骤 1：基础语义分析与底层原始记忆载入
        analysis = self.analyzer.analyze(chat_history)
        self.memory_manager.update_memory(chat_history, learn_profile=False)
        latest_user_messages = self._latest_user_messages(chat_history)
        
        # 🚀 步骤 2：提取当下最敏感的实时风险信号（不依赖状态机，纯粹客观安全网）
        risk = self.risk_detector.detect(chat_history)
        
        # 🚀 步骤 3：状态机吃进最新风险指标，校正本轮关系得分 (修复旧版时序颠倒)
        # 从原始内存中捞取基础步长画像，用于辅助状态机进行阻尼计算
        base_profile = self.memory_manager.memory.user.summary() if hasattr(self.memory_manager.memory, "user") else {}
        _ = self.relationship_machine.update_state(chat_history, profile=base_profile)
        relationship_state = self.relationship_machine.export_state()

        # 🚀 步骤 4：基于最新的、纯净的关系状态，全面迭代并固化用户深度 Profile
        profile = self.memory_manager.update_profile(
            latest_user_messages,
            analysis=analysis.model_dump(),
            relationship_state=relationship_state,
        )
        
        # 🚀 步骤 5：记忆持久化，确保下游所有 Agent 模块拿到的 memory 完全一致
        self.memory_manager.save_memory(self.memory_manager.memory)
        current_memory = self.memory_manager.memory.user.summary()

        # 🚀 步骤 6：核心高价值决策引擎 (Planner) 启动
        # 此时的语义、关系状态、长期记忆、实时风险全为【当下一秒最新】，绝无死锁或滞后
        plan = self.strategy_planner.plan(analysis, relationship_state, current_memory, risk)
        
        # 🚀 步骤 7：生成、去标点活人化 (Humanize) 与高框架去重重排行 (Ranker)
        candidates = self.reply_generator.generate(chat_history, plan, relationship_state, current_memory)
        humanized_candidates = self.humanizer.humanize(candidates)
        ranked = self.reply_ranker.rank(humanized_candidates, risk, relationship_state, chat_history, current_memory)
        final_reply = ranked.candidate.text

        # 🚀 步骤 8：成长支持辅助系统结算 (Opportunity, Coach, DateAssist, Confidence)
        opportunity = self.opportunity_detector.detect(
            analysis=analysis,
            relationship_state=relationship_state,
            memory=current_memory,
            risk=risk,
            plan=plan,
        )
        
        confidence = self.confidence_tracker.update(
            self.memory_manager.memory.user.confidence,
            final_reply=final_reply,
            analysis=analysis,
            relationship_state=relationship_state,
            opportunity=opportunity,
            ranked=ranked,
            risk=risk,
        )
        
        social_coach = self.social_coach.explain(
            final_reply=final_reply,
            analysis=analysis,
            relationship_state=relationship_state,
            memory=current_memory,
            risk=risk,
            plan=plan,
            opportunity=opportunity,
        )
        
        offline_assist = self.offline_assistant.prepare(
            analysis=analysis,
            relationship_state=relationship_state,
            memory=current_memory,
            opportunity=opportunity,
        )
        
        growth_support = GrowthSupportResult(
            social_coach=social_coach,
            opportunity=opportunity,
            offline_assist=offline_assist,
            confidence=confidence,
        )

        return ReplyPipelineResult(
            final_reply=final_reply,
            analysis=analysis,
            relationship_state=relationship_state,
            memory=current_memory,
            risk=risk,
            plan=plan,
            candidates=humanized_candidates,
            ranked=ranked,
            growth_support=growth_support,
        )

    @staticmethod
    def _latest_user_messages(chat_history: Sequence[str | Mapping[str, Any]]) -> list[str | Mapping[str, Any]]:
        """Return the latest message from the other person for profile learning."""
        for item in reversed(chat_history):
            if isinstance(item, str):
                return [item]
            role = str(item.get("role", "user")).lower()
            if role not in {"assistant", "me", "boy", "我"}:
                return [item]
        return []


def _demo() -> None:
    """Run an advanced pipeline end-to-end simulation test."""
    pipeline = ReplyPipeline(memory_path="memory_demo.json")
    # 模拟包含对方倒苦水和反问的复杂输入
    result = pipeline.run([
        {"role": "user", "content": "今天加班到好晚，领导还一直挑刺，真的烦死了"},
        {"role": "assistant", "content": "辛苦啦，等忙完这阵请你吃大餐"},
        {"role": "user", "content": "好呀，你现在在干嘛呢"}
    ])
    print("=================== 管道全链路打通测试成功 ===================")
    print(f"最终推荐回复 ->: {result.final_reply}")
    print(f"当前判定好感度 ->: {result.relationship_state.get('favorability_score')} ({result.relationship_state.get('favorability_label')})")
    print(f"系统执行策略 ->: {result.plan.action_type if hasattr(result.plan, 'action_type') else '常规模式'}")
    Path("memory_demo.json").unlink(missing_ok=True)


if __name__ == "__main__":
    _demo()