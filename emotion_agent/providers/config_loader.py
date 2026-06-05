"""Configuration loading helpers for LLM providers."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import os
from pathlib import Path
from typing import Any

from emotion_agent.utils.config import ProviderConfig
from emotion_agent.utils.types import ProviderName


class ProviderConfigLoader:
    """Loads provider configuration from a lightweight ``config.yaml`` file."""

    DEFAULT_FILE_NAME = "config.yaml"

    @classmethod
    def load(cls, provider: ProviderName, config_path: str | Path | None = None) -> ProviderConfig:
        """Load one provider's configuration from YAML-like project settings."""
        cls._load_dotenv()
        raw = cls._read_config(config_path)
        values = cls._provider_values(raw, provider)
        return ProviderConfig.from_mapping(provider=provider, values=values)

    @classmethod
    def _load_dotenv(cls) -> None:
        """Load simple KEY=VALUE pairs from a project ``.env`` file."""
        for path in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
            if not path.exists():
                continue
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                clean_key = key.strip()
                clean_value = value.strip().strip('"').strip("'")
                os.environ.setdefault(clean_key, clean_value)

    @classmethod
    def _read_config(cls, config_path: str | Path | None) -> dict[str, Any]:
        """Read and parse the configuration file if it exists."""
        path = cls._resolve_path(config_path)
        if path is None or not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        data = cls._parse_yaml(text)
        return data if isinstance(data, dict) else {}

    @classmethod
    def _resolve_path(cls, config_path: str | Path | None) -> Path | None:
        """Resolve the first usable configuration path."""
        candidates: list[Path] = []
        if config_path is not None:
            candidates.append(Path(config_path))
        candidates.append(Path.cwd() / cls.DEFAULT_FILE_NAME)
        candidates.append(Path(__file__).resolve().parents[2] / cls.DEFAULT_FILE_NAME)

        for candidate in candidates:
            resolved = candidate if candidate.is_absolute() else Path.cwd() / candidate
            if resolved.exists():
                return resolved
        return candidates[0] if config_path is not None else None

    @classmethod
    def _provider_values(cls, raw: dict[str, Any], provider: ProviderName) -> dict[str, object]:
        """Extract one provider's settings from known config layouts."""
        providers = raw.get("providers")
        if isinstance(providers, dict):
            values = providers.get(provider.value, {})
        else:
            values = raw.get(provider.value, {})
        return cls._expand_env(values if isinstance(values, dict) else {})

    @classmethod
    def _parse_yaml(cls, text: str) -> dict[str, Any]:
        """Parse YAML with PyYAML when available, otherwise use a small fallback."""
        try:
            import yaml  # type: ignore[import-not-found]

            parsed = yaml.safe_load(text)
            return parsed if isinstance(parsed, dict) else {}
        except ModuleNotFoundError:
            return cls._parse_simple_yaml(text)

    @classmethod
    def _parse_simple_yaml(cls, text: str) -> dict[str, Any]:
        """Parse simple nested mappings used by the sample provider config."""
        root: dict[str, Any] = {}
        stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

        for raw_line in text.splitlines():
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            line = raw_line.strip()
            key, separator, value = line.partition(":")
            if not separator:
                continue

            while indent <= stack[-1][0]:
                stack.pop()

            parent = stack[-1][1]
            clean_key = key.strip()
            clean_value = value.strip()
            if not clean_value:
                child: dict[str, Any] = {}
                parent[clean_key] = child
                stack.append((indent, child))
            else:
                parent[clean_key] = cls._parse_scalar(clean_value)

        return root

    @staticmethod
    def _parse_scalar(value: str) -> object:
        """Parse one scalar value from the fallback YAML reader."""
        unquoted = value.strip().strip('"').strip("'")
        expanded = os.path.expandvars(unquoted)
        lowered = expanded.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"null", "none", "~"}:
            return None
        try:
            return int(expanded)
        except ValueError:
            pass
        try:
            return float(expanded)
        except ValueError:
            return expanded

    @classmethod
    def _expand_env(cls, values: dict[str, Any]) -> dict[str, object]:
        """Expand environment variables in string config values."""
        expanded: dict[str, object] = {}
        for key, value in values.items():
            if isinstance(value, str):
                expanded[key] = os.path.expandvars(value)
            else:
                expanded[key] = value
        return expanded


def _demo() -> None:
    """Run a small module smoke test."""
    config = ProviderConfigLoader.load(ProviderName.OPENAI)
    print(f"ProviderConfigLoader ready: {config.provider.value}")


if __name__ == "__main__":
    _demo()
