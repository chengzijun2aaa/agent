"""Provider-backed response generator placeholder."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Sequence

from emotion_agent.generator.base import BaseGenerator
from emotion_agent.providers.base import BaseLLMProvider
from emotion_agent.strategy.reply_strategy import ReplyStrategy
from emotion_agent.utils.types import AgentContext, AnalysisResult, GenerationResult, ProviderRequest


class ResponseGenerator(BaseGenerator):
    """Delegates draft generation to an LLM provider boundary."""

    def __init__(self, provider: BaseLLMProvider) -> None:
        """Create a generator with a provider dependency."""
        self._provider = provider

    def generate(
        self,
        context: AgentContext,
        strategy: ReplyStrategy,
        analyses: Sequence[AnalysisResult],
    ) -> GenerationResult:
        """Generate a placeholder draft response through the provider interface."""
        request = ProviderRequest(
            user_id=context.user_id,
            message=context.current_message.content,
            strategy_name=strategy.name.value,
            analysis_labels={item.analyzer_name: item.label for item in analyses},
        )
        response = self._provider.generate(request)
        return GenerationResult(text=response.content, provider=response.provider, metadata=response.metadata)


def _demo() -> None:
    """Run a small module smoke test."""
    from emotion_agent.providers.openai_provider import OpenAIProvider

    print(f"{ResponseGenerator(OpenAIProvider()).__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
