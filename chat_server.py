"""Local web chat interface for the emotion agent."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from emotion_agent import ReplyPipeline
from emotion_agent.providers import ClaudeProvider, DeepSeekProvider, GeminiProvider, OpenAIProvider
from emotion_agent.session_store import SessionStore


HOST = "127.0.0.1"
PORT = int(os.getenv("EMOTION_AGENT_PORT", "8765"))
STATIC_DIR = Path(__file__).parent / "web"
DEFAULT_PROVIDER = os.getenv("EMOTION_AGENT_PROVIDER", "deepseek").strip().lower()


def create_llm_provider() -> Any:
    """Create the configured LLM provider; DeepSeek is the restored default."""
    providers = {
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
    }
    provider_cls = providers.get(DEFAULT_PROVIDER, DeepSeekProvider)
    return provider_cls()


def safe_user_id(value: str) -> str:
    """Return a filesystem-safe user id for local session memory files."""
    text = value.strip() or "default_girl"
    safe = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fa5]+", "_", text)
    return safe[:48] or "default_girl"


class ChatApplication:
    """Thread-safe holder for per-session reply pipelines and chat histories."""

    def __init__(self) -> None:
        """Create the chat application state."""
        self.llm = create_llm_provider()
        self.pipelines: dict[str, ReplyPipeline] = {}
        self.chat_histories: dict[str, list[dict[str, str]]] = {}
        self.session_store = SessionStore()
        self.lock = threading.Lock()

    def chat(self, message: str, user_id: str = "default_girl") -> dict[str, Any]:
        """Append a user message, run the pipeline, and append the AI reply."""
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message is empty")

        with self.lock:
            session_id = safe_user_id(user_id)
            pipeline = self._pipeline_for(session_id)
            chat_history = self.chat_histories.setdefault(session_id, [])
            chat_history.append({"role": "user", "content": clean_message})
            result = pipeline.run(chat_history[-20:])
            reply = result.final_reply.strip() or "我在，你慢慢说"
            chat_history.append({"role": "assistant", "content": reply})
            self.session_store.save_history(session_id, chat_history)
            self.session_store.save_state(session_id, result.relationship_state)
            return {
                "reply": reply,
                "provider": self.llm.provider_name.value,
                "model": self.llm.config.model,
                "user_id": session_id,
                "analysis": result.analysis.model_dump(),
                "relationship_state": result.relationship_state,
                "memory": result.memory,
                "risk": result.risk.model_dump(),
                "plan": result.plan.model_dump(),
                "profile": result.plan.behavior_profile.model_dump(),
                "ranked": result.ranked.model_dump(),
                "candidates": [candidate.model_dump() for candidate in result.candidates],
                "history": list(chat_history),
            }

    def reset(self, user_id: str = "default_girl") -> dict[str, Any]:
        """Clear in-memory chat history while preserving saved long-term memory."""
        with self.lock:
            session_id = safe_user_id(user_id)
            self.chat_histories[session_id] = []
            self.session_store.clear_history(session_id)
            return {"ok": True, "user_id": session_id, "history": []}

    def status(self, user_id: str = "default_girl") -> dict[str, Any]:
        """Return current state for one local chat session."""
        with self.lock:
            session_id = safe_user_id(user_id)
            pipeline = self._pipeline_for(session_id)
            return {
                "provider": self.llm.provider_name.value,
                "model": self.llm.config.model,
                "user_id": session_id,
                "relationship_state": pipeline.relationship_machine.export_state(),
                "memory": pipeline.memory_manager.memory.user.summary(),
                "risk": {"risk_level": "low"},
                "analysis": {"intent": "-"},
                "profile": {},
                "history": list(self.chat_histories.setdefault(session_id, [])),
                "candidates": [],
            }

    def _pipeline_for(self, user_id: str) -> ReplyPipeline:
        """Return or create the pipeline for one session."""
        if user_id not in self.pipelines:
            bundle = self.session_store.load(user_id)
            self.chat_histories[user_id] = list(bundle.chat_history)
            self.pipelines[user_id] = ReplyPipeline(
                llm=self.llm,
                memory_path=bundle.memory_path,
                relationship_machine=bundle.relationship_machine,
            )
        return self.pipelines[user_id]


APP = ChatApplication()


class ChatRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the local chat UI and JSON API."""

    server_version = "EmotionAgentChat/1.0"

    def do_GET(self) -> None:
        """Serve static assets."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/session_status":
            query = parse_qs(parsed.query)
            user_id = query.get("user_id", ["default_girl"])[0]
            self._send_json(APP.status(user_id))
            return

        target = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        path = (STATIC_DIR / target).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())) or not path.exists() or not path.is_file():
            self._send_json({"error": "not_found"}, status=404)
            return

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        """Handle JSON API requests."""
        try:
            if self.path == "/api/chat":
                payload = self._read_json()
                response = APP.chat(
                    str(payload.get("message", "")),
                    str(payload.get("user_id", "default_girl")),
                )
                self._send_json(response)
                return
            if self.path == "/api/reset":
                payload = self._read_json()
                self._send_json(APP.reset(str(payload.get("user_id", "default_girl"))))
                return
            self._send_json({"error": "not_found"}, status=404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            self._send_json({"error": "server_error", "detail": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep request logging concise."""
        print(f"{self.address_string()} - {format % args}")

    def _read_json(self) -> dict[str, Any]:
        """Read JSON request body."""
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _send_json(self, data: dict[str, Any], *, status: int = 200) -> None:
        """Send a JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    """Start the local chat server."""
    server = ThreadingHTTPServer((HOST, PORT), ChatRequestHandler)
    print(f"Emotion Agent chat UI: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
