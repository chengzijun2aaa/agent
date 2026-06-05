"""Application composition root for the WeChat emotion chat agent."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass
from typing import Sequence

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.analyzers.emotion_analyzer import EmotionAnalyzer
from emotion_agent.analyzers.intent_analyzer import IntentAnalyzer
from emotion_agent.analyzers.risk_analyzer import RiskAnalyzer
from emotion_agent.generator.response_generator import ResponseGenerator
from emotion_agent.humanizer.response_humanizer import ResponseHumanizer
from emotion_agent.memory.conversation_memory import ConversationMemory
from emotion_agent.providers.provider_factory import ProviderFactory
from emotion_agent.ranker.response_ranker import ResponseRanker
from emotion_agent.state.conversation_state import ConversationState
from emotion_agent.storage.memory_storage import InMemoryStorage
from emotion_agent.strategy.strategy_selector import StrategySelector
from emotion_agent.utils.config import AgentConfig
from emotion_agent.utils.types import AgentContext, GenerationResult, Message, SenderRole


@dataclass(slots=True)
class EmotionChatAgent:
    """Coordinates high-level agent components without embedding business rules."""

    config: AgentConfig
    analyzers: Sequence[BaseAnalyzer]
    memory: ConversationMemory
    state: ConversationState
    strategy_selector: StrategySelector
    generator: ResponseGenerator
    humanizer: ResponseHumanizer
    ranker: ResponseRanker
    storage: InMemoryStorage

    def build_context(self, user_id: str, message: str) -> AgentContext:
        """Create an agent context from raw input and current state."""
        inbound = Message(role=SenderRole.USER, content=message)
        return AgentContext(
            user_id=user_id,
            current_message=inbound,
            recent_messages=self.memory.get_recent(),
            state=self.state,
        )

    def handle_message(self, user_id: str, message: str) -> GenerationResult:
        """Run the architectural pipeline with placeholder component behavior."""
        context = self.build_context(user_id=user_id, message=message)
        analyses = [analyzer.analyze(context) for analyzer in self.analyzers]
        strategy = self.strategy_selector.select(context=context, analyses=analyses)
        draft = self.generator.generate(context=context, strategy=strategy, analyses=analyses)
        humanized = self.humanizer.humanize(context=context, draft=draft)
        ranked = self.ranker.rank(context=context, candidates=[humanized])
        return ranked.result


def build_default_agent(config: AgentConfig | None = None) -> EmotionChatAgent:
    """Build a default agent object graph for development and smoke testing."""
    resolved_config = config or AgentConfig()
    provider_factory = ProviderFactory.with_default_providers()
    provider = provider_factory.create(resolved_config.default_provider)

    return EmotionChatAgent(
        config=resolved_config,
        analyzers=(EmotionAnalyzer(), IntentAnalyzer(), RiskAnalyzer()),
        memory=ConversationMemory(),
        state=ConversationState.new(),
        strategy_selector=StrategySelector.default(),
        generator=ResponseGenerator(provider=provider),
        humanizer=ResponseHumanizer(),
        ranker=ResponseRanker(),
        storage=InMemoryStorage(),
    )


def main() -> None:
    """Run a minimal smoke test for the composed architecture."""
    agent = build_default_agent()
    result = agent.handle_message(user_id="demo-user", message="hello")
    print(f"Agent ready: {agent.__class__.__name__}")
    print(f"Placeholder response: {result.text!r}")


if __name__ == "__main__":
    main()
