"""Command-line entry point for the emotion agent package."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.main import main


if __name__ == "__main__":
    main()
