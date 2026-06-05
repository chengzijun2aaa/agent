"""End-to-end emotional reply pipeline."""

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

    def run(self, chat_history: Sequence[str | Mapping[str, Any]]) -> ReplyPipelineResult:
        """Run the full reply pipeline and return the final reply plus diagnostics."""
        analysis = self.analyzer.analyze(chat_history)
        relationship_state_model = self.relationship_machine.update_state(chat_history)
        relationship_state = self.relationship_machine.export_state()
        self.memory_manager.update_memory(chat_history)
        memory = self.memory_manager.memory.user.summary()
        risk = self.risk_detector.detect(chat_history)
        plan = self.strategy_planner.plan(analysis, relationship_state, memory, risk)
        candidates = self.reply_generator.generate(chat_history, plan, relationship_state, memory)
        humanized = self.humanizer.humanize(candidates)
        ranked = self.reply_ranker.rank(humanized, risk, relationship_state)
        _ = relationship_state_model
        return ReplyPipelineResult(
            final_reply=ranked.candidate.text,
            analysis=analysis,
            relationship_state=relationship_state,
            memory=memory,
            risk=risk,
            plan=plan,
            candidates=humanized,
            ranked=ranked,
        )


def _demo() -> None:
    """Run a small module smoke test."""
    pipeline = ReplyPipeline(memory_path="memory_demo.json")
    result = pipeline.run(["我家猫今天又拆家了", "你在干嘛"])
    print(result.final_reply)
    Path("memory_demo.json").unlink(missing_ok=True)


if __name__ == "__main__":
    _demo()
