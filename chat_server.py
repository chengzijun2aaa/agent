"""Local web chat interface for the emotion agent."""

from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from emotion_agent import ReplyPipeline
from emotion_agent.providers import DeepSeekProvider


HOST = "127.0.0.1"
PORT = 8766
STATIC_DIR = Path(__file__).parent / "web"


def _load_dotenv() -> None:
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        print(f"Loaded .env from: {env_path}")
    else:
        print(f".env not found at: {env_path}")


_load_dotenv()
print(f"DEEPSEEK_API_KEY loaded: {'DEEPSEEK_API_KEY' in os.environ}")


class ChatApplication:
    """Thread-safe holder for the long-lived reply pipeline."""

    def __init__(self) -> None:
        """Create the chat application state."""
        llm = DeepSeekProvider()
        print(f"DeepSeek config: api_key={llm.config.api_key}, api_key_env={llm.config.api_key_env}, base_url={llm.config.base_url}")
        print(f"Env DEEPSEEK_API_KEY: {os.environ.get('DEEPSEEK_API_KEY', 'NOT FOUND')[:10]}...")
        try:
            key = llm._api_key()
            print(f"Resolved API key: {key[:10]}...")
        except Exception as e:
            print(f"Failed to resolve API key: {e}")
        
        # Test LLM connection
        print("Testing LLM connection...")
        try:
            test_response = llm.generate("Hello")
            print(f"LLM test success: {test_response.success}, content: {test_response.content[:50]}")
        except Exception as e:
            print(f"LLM test failed: {e}")
            
        self.pipeline = ReplyPipeline(llm=llm, memory_path="memory.json")
        self.chat_history: list[dict[str, str]] = []
        self.lock = threading.Lock()

    def chat(self, message: str) -> dict[str, Any]:
        """Append a user message, run the pipeline, and append the AI reply."""
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message is empty")

        with self.lock:
            self.chat_history.append({"role": "user", "content": clean_message})
            print(f"Chat history: {self.chat_history[-20:]}")
            result = self.pipeline.run(self.chat_history[-20:])
            print(f"Pipeline result final_reply: {result.final_reply}")
            print(f"Pipeline result candidates: {[c.text for c in result.candidates]}")
            reply = result.final_reply.strip() or "我在，你慢慢说"
            self.chat_history.append({"role": "assistant", "content": reply})
            return {
                "reply": reply,
                "analysis": result.analysis.model_dump(),
                "relationship_state": result.relationship_state,
                "memory": result.memory,
                "risk": result.risk.model_dump(),
                "plan": result.plan.model_dump(),
                "ranked": result.ranked.model_dump(),
                "candidates": [candidate.model_dump() for candidate in result.candidates],
                "history": list(self.chat_history),
            }

    def reset(self) -> dict[str, Any]:
        """Clear in-memory chat history while preserving saved long-term memory."""
        with self.lock:
            self.chat_history.clear()
            return {"ok": True, "history": []}


APP = ChatApplication()


class ChatRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the local chat UI and JSON API."""

    server_version = "EmotionAgentChat/1.0"

    def do_GET(self) -> None:
        """Serve static assets."""
        parsed = urlparse(self.path)
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
        print(f"Received POST request: {self.path}")
        try:
            if self.path == "/api/chat":
                payload = self._read_json()
                print(f"Chat payload: {payload}")
                response = APP.chat(str(payload.get("message", "")))
                print(f"Chat response: {response['reply'][:50]}...")
                self._send_json(response)
                return
            if self.path == "/api/reset":
                self._send_json(APP.reset())
                return
            self._send_json({"error": "not_found"}, status=404)
        except ValueError as exc:
            print(f"ValueError: {exc}")
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            print(f"Exception: {exc}")
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
