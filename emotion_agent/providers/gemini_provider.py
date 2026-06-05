"""Gemini LLM provider implementation."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping, Sequence

from emotion_agent.providers.base import BaseLLM, RequestOptions
from emotion_agent.utils.types import ProviderName


class GeminiProvider(BaseLLM):
    """Provider adapter for Google Gemini generateContent requests."""

    default_base_url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    default_model = "gemini-3.5-flash"

    @property
    def provider_name(self) -> ProviderName:
        """Return the provider identifier."""
        return ProviderName.GEMINI

    @property
    def endpoint(self) -> str:
        """Return the Gemini endpoint with the configured model inserted."""
        return str(self.config.base_url).format(model=self.config.model)

    def build_headers(self) -> dict[str, str]:
        """Build Gemini request headers."""
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key(),
        }

    def build_payload(self, messages: Sequence[dict[str, str]], options: RequestOptions) -> dict[str, Any]:
        """Build a Gemini generateContent request payload."""
        payload: dict[str, Any] = {
            "contents": [self._to_gemini_content(message) for message in messages if message["role"] != "system"],
            "generationConfig": {
                "temperature": options.temperature,
                "maxOutputTokens": options.max_tokens,
            },
        }
        system_messages = [message["content"] for message in messages if message["role"] == "system"]
        if options.system_prompt:
            system_messages.insert(0, options.system_prompt)
        if system_messages:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_messages)}],
            }
        return payload

    def extract_text(self, response_data: Mapping[str, Any]) -> str:
        """Extract response text from Gemini generateContent JSON."""
        candidates = response_data.get("candidates", [])
        if not candidates:
            return ""
        first = candidates[0]
        if not isinstance(first, Mapping):
            return ""
        content = first.get("content", {})
        if not isinstance(content, Mapping):
            return ""
        parts = content.get("parts", [])
        texts: list[str] = []
        for part in parts if isinstance(parts, list) else []:
            if isinstance(part, Mapping):
                texts.append(str(part.get("text", "") or ""))
        return "\n".join(text for text in texts if text)

    def extract_usage(self, response_data: Mapping[str, Any]) -> Mapping[str, Any]:
        """Extract Gemini usage metadata."""
        usage = response_data.get("usageMetadata", {})
        return usage if isinstance(usage, Mapping) else {}

    @staticmethod
    def _to_gemini_content(message: Mapping[str, str]) -> dict[str, Any]:
        """Convert normalized messages to Gemini content format."""
        role = "model" if message["role"] == "assistant" else "user"
        return {"role": role, "parts": [{"text": message["content"]}]}


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{GeminiProvider().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
