"""OpenAI LLM provider implementation."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping, Sequence

from emotion_agent.providers.base import BaseLLM, RequestOptions
from emotion_agent.utils.types import ProviderName


class OpenAIProvider(BaseLLM):
    """Provider adapter for OpenAI Chat Completions compatible requests."""

    default_base_url = "https://api.openai.com/v1/chat/completions"
    default_model = "gpt-4.1-mini"

    @property
    def provider_name(self) -> ProviderName:
        """Return the provider identifier."""
        return ProviderName.OPENAI

    def build_headers(self) -> dict[str, str]:
        """Build OpenAI request headers."""
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }

    def build_payload(self, messages: Sequence[dict[str, str]], options: RequestOptions) -> dict[str, Any]:
        """Build an OpenAI Chat Completions request payload."""
        payload_messages = list(messages)
        if options.system_prompt:
            payload_messages = [{"role": "system", "content": options.system_prompt}, *payload_messages]
        return {
            "model": self.config.model,
            "messages": payload_messages,
            "temperature": options.temperature,
            "max_tokens": options.max_tokens,
        }

    def extract_text(self, response_data: Mapping[str, Any]) -> str:
        """Extract response text from OpenAI Chat Completions JSON."""
        choices = response_data.get("choices", [])
        if not choices:
            return ""
        first = choices[0]
        if not isinstance(first, Mapping):
            return ""
        message = first.get("message", {})
        if not isinstance(message, Mapping):
            return ""
        return str(message.get("content", "") or "")


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{OpenAIProvider().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
