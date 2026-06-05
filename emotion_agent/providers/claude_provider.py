"""Claude LLM provider implementation."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping, Sequence

from emotion_agent.providers.base import BaseLLM, RequestOptions
from emotion_agent.utils.types import ProviderName


class ClaudeProvider(BaseLLM):
    """Provider adapter for Anthropic Claude Messages requests."""

    default_base_url = "https://api.anthropic.com/v1/messages"
    default_model = "claude-3-5-haiku-latest"

    @property
    def provider_name(self) -> ProviderName:
        """Return the provider identifier."""
        return ProviderName.CLAUDE

    def build_headers(self) -> dict[str, str]:
        """Build Claude request headers."""
        return {
            "x-api-key": self._api_key(),
            "anthropic-version": self.config.extra.get("anthropic_version", "2023-06-01"),
            "Content-Type": "application/json",
        }

    def build_payload(self, messages: Sequence[dict[str, str]], options: RequestOptions) -> dict[str, Any]:
        """Build a Claude Messages request payload."""
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [self._to_claude_message(message) for message in messages if message["role"] != "system"],
            "temperature": options.temperature,
            "max_tokens": options.max_tokens,
        }
        system_messages = [message["content"] for message in messages if message["role"] == "system"]
        if options.system_prompt:
            system_messages.insert(0, options.system_prompt)
        if system_messages:
            payload["system"] = "\n\n".join(system_messages)
        return payload

    def extract_text(self, response_data: Mapping[str, Any]) -> str:
        """Extract response text from Claude Messages JSON."""
        content_blocks = response_data.get("content", [])
        texts: list[str] = []
        for block in content_blocks if isinstance(content_blocks, list) else []:
            if isinstance(block, Mapping) and block.get("type") == "text":
                texts.append(str(block.get("text", "") or ""))
        return "\n".join(text for text in texts if text)

    @staticmethod
    def _to_claude_message(message: Mapping[str, str]) -> dict[str, str]:
        """Convert normalized messages to Claude-supported roles."""
        role = message["role"]
        if role not in {"user", "assistant"}:
            role = "user"
        return {"role": role, "content": message["content"]}


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ClaudeProvider().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
