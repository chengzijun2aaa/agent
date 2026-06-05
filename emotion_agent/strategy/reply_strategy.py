"""Response strategy data model."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass, field

from emotion_agent.utils.types import ProviderName, StrategyName


@dataclass(frozen=True, slots=True)
class ReplyStrategy:
    """Describes how a response should be generated without containing prompts."""

    name: StrategyName
    provider: ProviderName
    tone: str = "neutral"
    constraints: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "ReplyStrategy":
        """Create the default strategy descriptor."""
        return cls(name=StrategyName.DEFAULT, provider=ProviderName.OPENAI)


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ReplyStrategy.default().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
