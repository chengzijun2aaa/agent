"""Base implementation and interfaces for LLM providers."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import json
import os
import socket
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from emotion_agent.providers.config_loader import ProviderConfigLoader
from emotion_agent.utils.config import ProviderConfig
from emotion_agent.utils.exceptions import APIAuthenticationError, APINetworkError, APITimeoutError
from emotion_agent.utils.types import LLMResponse, Message, ProviderName, ProviderRequest, SenderRole


LLMMessage = Mapping[str, str] | Message


@dataclass(frozen=True, slots=True)
class RequestOptions:
    """Resolved generation options for one LLM request."""

    temperature: float
    max_tokens: int
    system_prompt: str | None


class BaseLLM(ABC):
    """Common HTTP-backed LLM provider interface.

    Subclasses only define provider-specific endpoint, headers, payload, and
    response parsing behavior. Callers can swap providers without changing
    business code:

    ``llm = DeepSeekProvider(); response = llm.generate(messages=[...])``
    """

    default_base_url: str
    default_model: str

    def __init__(
        self,
        config: ProviderConfig | None = None,
        *,
        config_path: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """Create a provider from explicit values, config file, and defaults."""
        loaded = config or ProviderConfigLoader.load(self.provider_name, config_path=config_path)
        self.config = ProviderConfig(
            provider=self.provider_name,
            api_key=api_key or loaded.api_key,
            api_key_env=loaded.api_key_env,
            base_url=base_url or loaded.base_url or self.default_base_url,
            model=model or loaded.model or self.default_model,
            timeout_seconds=timeout_seconds or loaded.timeout_seconds,
            temperature=temperature if temperature is not None else loaded.temperature,
            max_tokens=max_tokens if max_tokens is not None else loaded.max_tokens,
            system_prompt=system_prompt if system_prompt is not None else loaded.system_prompt,
            extra=loaded.extra,
        )

    @property
    @abstractmethod
    def provider_name(self) -> ProviderName:
        """Return the stable provider identifier."""

    def generate(
        self,
        prompt: str | ProviderRequest | None = None,
        *,
        messages: Sequence[LLMMessage] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        **metadata: Any,
    ) -> LLMResponse:
        """Generate text with a unified provider interface."""
        return self._chat(
            task="generate",
            prompt=prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            metadata=metadata,
        )

    def analyze(
        self,
        prompt: str | ProviderRequest | None = None,
        *,
        messages: Sequence[LLMMessage] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        **metadata: Any,
    ) -> LLMResponse:
        """Analyze text or messages with the same transport and response shape."""
        return self._chat(
            task="analyze",
            prompt=prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            metadata=metadata,
        )

    def score(
        self,
        prompt: str | ProviderRequest | None = None,
        *,
        messages: Sequence[LLMMessage] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        **metadata: Any,
    ) -> LLMResponse:
        """Score text or messages with the same transport and response shape."""
        return self._chat(
            task="score",
            prompt=prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            metadata=metadata,
        )

    def validate_config(self) -> None:
        """Validate local provider configuration without making a network call."""
        self._api_key()

    def _chat(
        self,
        *,
        task: str,
        prompt: str | ProviderRequest | None,
        messages: Sequence[LLMMessage] | None,
        temperature: float | None,
        max_tokens: int | None,
        system_prompt: str | None,
        metadata: Mapping[str, Any],
    ) -> LLMResponse:
        """Build, send, and parse one provider request."""
        try:
            options = self._resolve_options(
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )
            normalized = self._normalize_messages(prompt=prompt, messages=messages)
            payload = self.build_payload(messages=normalized, options=options)
            headers = self.build_headers()
            response_data, status_code = self._post_json(
                url=self.endpoint,
                payload=payload,
                headers=headers,
            )
            content = self.extract_text(response_data)
            usage = self.extract_usage(response_data)
            return LLMResponse(
                provider=self.provider_name,
                content=content,
                model=self.config.model,
                status_code=status_code,
                usage=usage,
                raw=response_data,
                metadata={"task": task, **dict(metadata)},
            )
        except APIAuthenticationError as exc:
            return self._error_response("authentication_failed", str(exc), metadata=metadata)
        except APITimeoutError as exc:
            return self._error_response("api_timeout", str(exc), metadata=metadata)
        except APINetworkError as exc:
            return self._error_response("network_error", str(exc), metadata=metadata)

    @property
    def endpoint(self) -> str:
        """Return the provider request endpoint."""
        return str(self.config.base_url)

    @abstractmethod
    def build_headers(self) -> dict[str, str]:
        """Build HTTP request headers for the provider."""

    @abstractmethod
    def build_payload(self, messages: Sequence[dict[str, str]], options: RequestOptions) -> dict[str, Any]:
        """Build the provider-specific JSON payload."""

    @abstractmethod
    def extract_text(self, response_data: Mapping[str, Any]) -> str:
        """Extract generated content from provider JSON response."""

    def extract_usage(self, response_data: Mapping[str, Any]) -> Mapping[str, Any]:
        """Extract usage metadata from provider JSON response."""
        usage = response_data.get("usage", {})
        return usage if isinstance(usage, Mapping) else {}

    def _post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> tuple[dict[str, Any], int]:
        """Post JSON and map transport failures to provider exceptions."""
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url=url, data=body, headers=dict(headers), method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            if exc.code in {401, 403}:
                raise APIAuthenticationError(error_body or f"Authentication failed: {exc.code}") from exc
            raise APINetworkError(error_body or f"HTTP request failed: {exc.code}") from exc
        except TimeoutError as exc:
            raise APITimeoutError(f"API request timed out after {self.config.timeout_seconds} seconds") from exc
        except socket.timeout as exc:
            raise APITimeoutError(f"API request timed out after {self.config.timeout_seconds} seconds") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                raise APITimeoutError(f"API request timed out after {self.config.timeout_seconds} seconds") from exc
            raise APINetworkError(str(reason)) from exc
        except OSError as exc:
            raise APINetworkError(str(exc)) from exc

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise APINetworkError("Provider returned non-JSON response") from exc

        if not isinstance(parsed, dict):
            raise APINetworkError("Provider returned unsupported JSON shape")
        return parsed, status_code

    def _resolve_options(
        self,
        *,
        temperature: float | None,
        max_tokens: int | None,
        system_prompt: str | None,
    ) -> RequestOptions:
        """Resolve per-call options against provider configuration defaults."""
        return RequestOptions(
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
            system_prompt=system_prompt if system_prompt is not None else self.config.system_prompt,
        )

    def _normalize_messages(
        self,
        *,
        prompt: str | ProviderRequest | None,
        messages: Sequence[LLMMessage] | None,
    ) -> list[dict[str, str]]:
        """Normalize prompt/request/messages into OpenAI-style role-content pairs."""
        normalized: list[dict[str, str]] = []
        if messages is not None:
            normalized.extend(self._message_to_dict(message) for message in messages)
        if prompt is not None:
            content = prompt.message if isinstance(prompt, ProviderRequest) else prompt
            normalized.append({"role": SenderRole.USER.value, "content": str(content)})
        if not normalized:
            raise APINetworkError("At least one prompt or message is required")
        return normalized

    @staticmethod
    def _message_to_dict(message: LLMMessage) -> dict[str, str]:
        """Convert one message object or mapping into a role-content dictionary."""
        if isinstance(message, Message):
            return {"role": message.role.value, "content": message.content}
        role = str(message.get("role", SenderRole.USER.value))
        content = str(message.get("content", ""))
        return {"role": role, "content": content}

    def _api_key(self) -> str:
        """Resolve the API key from config value, config env name, or defaults."""
        if self.config.api_key:
            return self.config.api_key
        if self.config.api_key_env:
            value = os.getenv(self.config.api_key_env)
            if value:
                return value
        default_env = f"{self.provider_name.value.upper()}_API_KEY"
        value = os.getenv(default_env)
        if value:
            return value
        raise APIAuthenticationError(f"Missing API key for provider: {self.provider_name.value}")

    def _error_response(
        self,
        error_type: str,
        error_message: str,
        *,
        metadata: Mapping[str, Any],
    ) -> LLMResponse:
        """Convert provider errors to the unified response object."""
        return LLMResponse.failed(
            provider=self.provider_name,
            model=self.config.model,
            error_type=error_type,
            error_message=error_message,
            metadata=dict(metadata),
        )


BaseLLMProvider = BaseLLM


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseLLM interface ready")


if __name__ == "__main__":
    _demo()
