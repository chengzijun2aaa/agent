"""Factory and registry for LLM providers."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from collections.abc import Callable

from emotion_agent.providers.base import BaseLLM
from emotion_agent.providers.claude_provider import ClaudeProvider
from emotion_agent.providers.deepseek_provider import DeepSeekProvider
from emotion_agent.providers.gemini_provider import GeminiProvider
from emotion_agent.providers.openai_provider import OpenAIProvider
from emotion_agent.utils.config import ProviderConfig
from emotion_agent.utils.exceptions import ConfigurationError
from emotion_agent.utils.types import ProviderName

ProviderBuilder = Callable[[ProviderConfig | None], BaseLLM]


class ProviderFactory:
    """Creates provider instances from registered provider builders."""

    def __init__(self) -> None:
        """Create an empty provider factory."""
        self._builders: dict[ProviderName, ProviderBuilder] = {}

    @classmethod
    def with_default_providers(cls) -> "ProviderFactory":
        """Create a factory preloaded with supported provider placeholders."""
        factory = cls()
        factory.register(ProviderName.OPENAI, OpenAIProvider)
        factory.register(ProviderName.DEEPSEEK, DeepSeekProvider)
        factory.register(ProviderName.CLAUDE, ClaudeProvider)
        factory.register(ProviderName.GEMINI, GeminiProvider)
        return factory

    def register(self, name: ProviderName, builder: ProviderBuilder) -> None:
        """Register a provider builder by provider name."""
        self._builders[name] = builder

    def create(self, name: ProviderName, config: ProviderConfig | None = None) -> BaseLLM:
        """Create a provider instance by name."""
        builder = self._builders.get(name)
        if builder is None:
            raise ConfigurationError(f"Provider is not registered: {name.value}")
        return builder(config)

    def available(self) -> tuple[ProviderName, ...]:
        """Return the registered provider names."""
        return tuple(self._builders.keys())


def _demo() -> None:
    """Run a small module smoke test."""
    names = [name.value for name in ProviderFactory.with_default_providers().available()]
    print(f"ProviderFactory ready: {', '.join(names)}")


if __name__ == "__main__":
    _demo()
