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
from emotion_agent.storage.interaction_logger import InteractionLogger


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
        self.chat_histories: dict[str, list[dict[str, Any]]] = {}
        self.session_store = SessionStore()
        self.interaction_logger = InteractionLogger()
        self.last_turn_ids: dict[str, str] = {}
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
            previous_turn_id = self.last_turn_ids.get(session_id)
            if previous_turn_id:
                self.interaction_logger.log_follow_up(
                    user_id=session_id,
                    previous_turn_id=previous_turn_id,
                    follow_up_message=clean_message,
                )
            chat_history.append({"role": "user", "content": clean_message, "metadata": {"source": "incoming"}})
            effective_history = self._effective_history(chat_history)
            result = pipeline.run(effective_history[-20:])
            reply = result.final_reply.strip() or "我在，你慢慢说"
            candidates = [candidate.model_dump() for candidate in result.candidates]
            diagnostics = {
                "analysis": result.analysis.model_dump(),
                "relationship_state": result.relationship_state,
                "risk": result.risk.model_dump(),
                "plan": result.plan.model_dump(),
                "growth_support": result.growth_support.model_dump(),
                "ranked": result.ranked.model_dump(),
            }
            turn_id = self.interaction_logger.log_generation(
                user_id=session_id,
                user_message=clean_message,
                reply=reply,
                candidates=candidates,
                diagnostics=diagnostics,
            )
            chat_history.append(
                {
                    "role": "assistant",
                    "content": reply,
                    "metadata": {
                        "turn_id": turn_id,
                        "delivery_status": "suggested",
                        "suggested_reply": reply,
                    },
                }
            )
            self.session_store.save_history(session_id, chat_history)
            self.session_store.save_state(session_id, result.relationship_state)
            self.last_turn_ids[session_id] = turn_id
            return {
                "reply": reply,
                "turn_id": turn_id,
                "provider": self.llm.provider_name.value,
                "model": self.llm.config.model,
                "user_id": session_id,
                "analysis": result.analysis.model_dump(),
                "relationship_state": result.relationship_state,
                "memory": result.memory,
                "risk": result.risk.model_dump(),
                "plan": result.plan.model_dump(),
                "growth_support": result.growth_support.model_dump(),
                "profile": result.plan.behavior_profile.model_dump(),
                "ranked": result.ranked.model_dump(),
                "candidates": candidates,
                "history": list(chat_history),
            }

    def feedback(
        self,
        *,
        user_id: str = "default_girl",
        turn_id: str | None = None,
        action: str = "feedback",
        rating: str | None = None,
        selected_reply: str = "",
        selected_index: int | None = None,
        edited_reply: str = "",
    ) -> dict[str, Any]:
        """Record copy, selection, edit, and good/bad feedback."""
        with self.lock:
            session_id = safe_user_id(user_id)
            resolved_turn_id = turn_id or self.last_turn_ids.get(session_id)
            event_id = self.interaction_logger.log_feedback(
                user_id=session_id,
                turn_id=resolved_turn_id,
                action=action,
                rating=rating,
                selected_reply=selected_reply,
                selected_index=selected_index,
                edited_reply=edited_reply,
            )
            actual_reply = edited_reply.strip() or selected_reply.strip()
            if actual_reply and action in {"copy", "candidate_copy", "sent"}:
                self._record_sent_reply(
                    session_id=session_id,
                    turn_id=resolved_turn_id,
                    actual_reply=actual_reply,
                    selected_reply=selected_reply,
                    selected_index=selected_index,
                    action=action,
                )
            return {
                "ok": True,
                "event_id": event_id,
                "turn_id": resolved_turn_id,
                "user_id": session_id,
                "history": list(self.chat_histories.setdefault(session_id, [])),
            }

    def reset(self, user_id: str = "default_girl") -> dict[str, Any]:
        """Clear in-memory chat history while preserving saved long-term memory."""
        with self.lock:
            session_id = safe_user_id(user_id)
            self.chat_histories[session_id] = []
            self.last_turn_ids.pop(session_id, None)
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
                "turn_id": self.last_turn_ids.get(session_id),
                "relationship_state": pipeline.relationship_machine.export_state(),
                "memory": pipeline.memory_manager.memory.user.summary(),
                "risk": {"risk_level": "low"},
                "analysis": {"intent": "-"},
                "profile": {},
                "growth_support": {},
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

    def _record_sent_reply(
        self,
        *,
        session_id: str,
        turn_id: str | None,
        actual_reply: str,
        selected_reply: str,
        selected_index: int | None,
        action: str,
    ) -> None:
        """Persist what was actually sent so future turns can follow the topic."""
        chat_history = self.chat_histories.setdefault(session_id, [])
        matched = False

        for item in reversed(chat_history):
            if item.get("role") != "assistant":
                continue
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
                item["metadata"] = metadata
            if turn_id and metadata.get("turn_id") != turn_id:
                continue

            item["content"] = actual_reply
            metadata.update(
                {
                    "turn_id": turn_id,
                    "delivery_status": "sent",
                    "actual_sent_text": actual_reply,
                    "selected_reply": selected_reply,
                    "selected_index": selected_index,
                    "sent_action": action,
                }
            )
            matched = True
            break

        if not matched:
            chat_history.append(
                {
                    "role": "assistant",
                    "content": actual_reply,
                    "metadata": {
                        "turn_id": turn_id,
                        "delivery_status": "sent",
                        "actual_sent_text": actual_reply,
                        "selected_reply": selected_reply,
                        "selected_index": selected_index,
                        "sent_action": action,
                    },
                }
            )

        self.session_store.save_history(session_id, chat_history)

    @staticmethod
    def _effective_history(chat_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Use only real incoming messages and assistant replies confirmed as sent."""
        effective: list[dict[str, Any]] = []
        for item in chat_history:
            role = str(item.get("role", "user"))
            content = str(item.get("content", "")).strip()
            if not content:
                continue

            if role != "assistant":
                effective.append({"role": role, "content": content})
                continue

            metadata = item.get("metadata", {})
            delivery_status = metadata.get("delivery_status") if isinstance(metadata, dict) else None
            if delivery_status == "suggested":
                continue
            effective.append({"role": "assistant", "content": content})

        return effective


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
            if self.path == "/api/feedback":
                payload = self._read_json()
                selected_index = payload.get("selected_index")
                self._send_json(
                    APP.feedback(
                        user_id=str(payload.get("user_id", "default_girl")),
                        turn_id=str(payload["turn_id"]) if payload.get("turn_id") else None,
                        action=str(payload.get("action", "feedback")),
                        rating=str(payload["rating"]) if payload.get("rating") else None,
                        selected_reply=str(payload.get("selected_reply", "")),
                        selected_index=int(selected_index) if selected_index is not None else None,
                        edited_reply=str(payload.get("edited_reply", "")),
                    )
                )
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
