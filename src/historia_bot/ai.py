from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, List


class AIEngineError(Exception):
    """Base exception for AI engine failures."""


class AIRequestTimeoutError(AIEngineError):
    """Raised when Ollama request exceeds timeout."""


def request_timeout_seconds() -> float:
    raw = os.environ.get("OLLAMA_REQUEST_TIMEOUT", "120").strip()
    try:
        value = float(raw)
    except ValueError:
        return 120.0
    return value if value > 0 else 120.0


def _is_wsl(osrelease_path: str = "/proc/sys/kernel/osrelease") -> bool:
    try:
        osrelease = Path(osrelease_path).read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "microsoft" in osrelease


def _wsl_windows_host_ip(resolv_conf_path: str = "/etc/resolv.conf") -> str | None:
    try:
        content = Path(resolv_conf_path).read_text(encoding="utf-8")
    except OSError:
        return None

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "nameserver":
            return parts[1]
    return None


def default_ollama_base_url() -> str:
    env_url = os.environ.get("OLLAMA_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    if _is_wsl():
        win_ip = _wsl_windows_host_ip()
        if win_ip:
            return f"http://{win_ip}:11434"

    return "http://localhost:11434"


def _extract_json_object(text: str) -> str | None:
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fenced:
        return fenced.group(1)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _parse_articles(raw: str) -> List[Dict[str, Any]]:
    candidates: List[str] = []
    direct = raw.strip()
    if direct:
        candidates.append(direct)
    extracted = _extract_json_object(raw)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        if not isinstance(articles, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in articles:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            description = item.get("description")
            normalized.append(
                {
                    "title": str(title).strip() if title is not None else "",
                    "description": str(description).strip() if description is not None else "",
                }
            )
        return normalized[:15]

    return []


class AIEngine:
    def __init__(self, model: str, base_url: str | None = None) -> None:
        self._model = model
        self._base_url = (base_url or default_ollama_base_url()).rstrip("/")
        self._request_timeout = request_timeout_seconds()

    @staticmethod
    def list_models(base_url: str | None = None) -> List[str]:
        resolved_url = (base_url or default_ollama_base_url()).rstrip("/")
        url = f"{resolved_url}/api/tags"
        req = urllib.request.Request(url=url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        models = payload.get("models", [])
        if not isinstance(models, list):
            return []

        result: List[str] = []
        for item in models:
            name = item.get("name") if isinstance(item, dict) else None
            if isinstance(name, str) and name.strip():
                result.append(name)
        return result

    def _chat(self, system: str, user: str, temperature: float, json_mode: bool = False) -> str:
        url = f"{self._base_url}/api/chat"
        body: Dict[str, Any] = {
            "model": self._model,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            body["format"] = "json"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._request_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise AIRequestTimeoutError("Ollama request timed out") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError | socket.timeout):
                raise AIRequestTimeoutError("Ollama request timed out") from exc
            raise AIEngineError(f"Ollama request failed: {exc}") from exc

        message = payload.get("message", {})
        if not isinstance(message, dict):
            return ""
        content = message.get("content", "")
        return content.strip() if isinstance(content, str) else ""

    def ask_advisor(self, context: str) -> str:
        return self._chat(
            system="Ты геополитический советник в стратегической игре. Отвечай кратко и по делу.",
            user=context,
            temperature=0.7,
        )

    def generate_world_update(self, prompt: str) -> List[Dict[str, Any]]:
        raw = self._chat(
            system="Ты генератор игровых новостей. Верни JSON-объект с полем articles.",
            user=prompt,
            temperature=0.9,
            json_mode=True,
        )
        return _parse_articles(raw)
