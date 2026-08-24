from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:0.6b"


def _load_project_env(path: Path = ENV_PATH) -> None:
    """Load simple KEY=VALUE entries without replacing explicit environment values."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ.setdefault(key, value)


class OllamaClient:
    """Small client for Ollama's local /api/tags and /api/generate endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        _load_project_env()
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"} if data is not None else {},
            method="POST" if data is not None else "GET",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def check_health(self) -> dict[str, Any]:
        """Return truthful server status and the models reported by Ollama."""
        try:
            response = self._request("/api/tags")
            models = [
                str(item.get("name", "")).strip()
                for item in response.get("models", [])
                if isinstance(item, dict) and item.get("name")
            ]
            return {
                "online": True,
                "models": models,
                "configured_model": self.model,
                "configured_model_available": self.model in models,
                "error": None,
            }
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            return {
                "online": False,
                "models": [],
                "configured_model": self.model,
                "configured_model_available": False,
                "error": f"{type(error).__name__}: {error}",
            }

    def generate(
        self,
        prompt: str,
        format_json: bool = False,
        temperature: float = 0.2,
    ) -> str | dict[str, Any] | list[Any]:
        """Generate with Ollama, or return a clearly marked safe fallback when unavailable."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format_json:
            payload["format"] = "json"

        try:
            response = self._request("/api/generate", payload)
            text = str(response.get("response", "")).strip()
            if not text:
                raise ValueError("Ollama returned an empty response")
            if not format_json:
                return text
            parsed = json.loads(text)
            if not isinstance(parsed, (dict, list)):
                raise ValueError("Ollama JSON response must be an object or array")
            return parsed
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as error:
            return self._fallback(prompt, format_json, error)

    def _fallback(
        self,
        prompt: str,
        format_json: bool,
        error: Exception,
    ) -> str | dict[str, Any]:
        message = (
            "Ollama is unavailable. No model-generated content was returned; "
            "a human review is required."
        )
        if not format_json:
            return message
        return {
            "status": "FALLBACK",
            "review_status": "NEEDS_HUMAN_REVIEW",
            "response": message,
            "prompt_received": bool(prompt.strip()),
            "error_type": type(error).__name__,
        }


def main() -> int:
    client = OllamaClient()
    health = client.check_health()
    fallback = client.generate("Health check fallback probe.", format_json=True)
    fallback_safe = isinstance(fallback, dict) and fallback.get("review_status") == "NEEDS_HUMAN_REVIEW"
    adapter_passed = bool(health["online"] or fallback_safe)

    print(f"OLLAMA ADAPTER: {'PASS' if adapter_passed else 'FAIL'}")
    print(f"OLLAMA SERVER ONLINE: {'YES' if health['online'] else 'NO'}")
    print(f"OLLAMA MODEL: {client.model}")
    print(f"CONFIGURED MODEL AVAILABLE: {'YES' if health['configured_model_available'] else 'NO'}")
    if health["error"]:
        print(f"HEALTH DETAIL: {health['error']}")
    return 0 if adapter_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
