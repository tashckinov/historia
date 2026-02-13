from __future__ import annotations

import json
from pathlib import Path
import os
import urllib.request
from typing import Any, Dict, List


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


class AIEngine:
    def __init__(self, model: str, base_url: str | None = None) -> None:
        self._model = model
        self._base_url = (base_url or default_ollama_base_url()).rstrip("/")

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

    def _chat(self, system: str, user: str, temperature: float) -> str:
        url = f"{self._base_url}/api/chat"
        body = {
            "model": self._model,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))

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
            system="Ты генератор игровых новостей. Возвращай только валидный JSON.",
            user=prompt,
            temperature=0.9,
        )
        payload = json.loads(raw)
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            return []
        return articles[:15]
