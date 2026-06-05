"""Logging utilities for the emotion agent."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import logging


class LoggerFactory:
    """Creates consistently named loggers for project modules."""

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Return a logger with the project namespace."""
        return logging.getLogger(f"emotion_agent.{name}")


def _demo() -> None:
    """Run a small module smoke test."""
    print(LoggerFactory.get_logger("demo").name)


if __name__ == "__main__":
    _demo()
