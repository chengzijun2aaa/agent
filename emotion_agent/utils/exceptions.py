"""Project-specific exceptions."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all agent-level errors."""


class ConfigurationError(AgentError):
    """Raised when required configuration is invalid or missing."""


class ProviderError(AgentError):
    """Raised when an LLM provider boundary fails."""


class APITimeoutError(ProviderError):
    """Raised when an LLM API request exceeds its timeout."""


class APIAuthenticationError(ProviderError):
    """Raised when an LLM API request is not authenticated."""


class APINetworkError(ProviderError):
    """Raised when the network fails before a valid API response is received."""


class StorageError(AgentError):
    """Raised when a persistence adapter fails."""


class StrategyError(AgentError):
    """Raised when response strategy selection fails."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("Exception hierarchy ready")


if __name__ == "__main__":
    _demo()
