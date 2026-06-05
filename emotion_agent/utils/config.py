"""Configuration models for the emotion agent."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass, field

from emotion_agent.utils.types import ProviderName


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Configuration required by one LLM provider adapter."""

    provider: ProviderName
    api_key: str | None = None
    api_key_env: str | None = None
    base_url: str | None = None
    model: str | None = None
    timeout_seconds: float = 30.0
    temperature: float = 0.7
    max_tokens: int = 1024
    system_prompt: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, provider: ProviderName, values: dict[str, object]) -> "ProviderConfig":
        """Create provider config from parsed config data."""
        known_keys = {
            "api_key",
            "api_key_env",
            "base_url",
            "model",
            "timeout_seconds",
            "temperature",
            "max_tokens",
            "system_prompt",
        }
        extra = {str(key): str(value) for key, value in values.items() if key not in known_keys}
        return cls(
            provider=provider,
            api_key=_optional_str(values.get("api_key")),
            api_key_env=_optional_str(values.get("api_key_env")),
            base_url=_optional_str(values.get("base_url")),
            model=_optional_str(values.get("model")),
            timeout_seconds=float(values.get("timeout_seconds", 30.0)),
            temperature=float(values.get("temperature", 0.7)),
            max_tokens=int(values.get("max_tokens", 1024)),
            system_prompt=_optional_str(values.get("system_prompt")),
            extra=extra,
        )


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Top-level configuration for composing the agent."""

    default_provider: ProviderName = ProviderName.OPENAI
    max_recent_messages: int = 50
    enable_persistent_memory: bool = False
    provider_configs: dict[ProviderName, ProviderConfig] = field(default_factory=dict)

    def provider_config_for(self, provider: ProviderName) -> ProviderConfig:
        """Return provider config or an empty default for the provider."""
        return self.provider_configs.get(provider, ProviderConfig(provider=provider))


def _optional_str(value: object) -> str | None:
    """Return a string value unless the parsed value is empty."""
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{AgentConfig().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
