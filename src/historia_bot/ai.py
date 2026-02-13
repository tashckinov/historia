from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List


class AIEngine:
    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    @staticmethod
    def list_models(base_url: str = "http://localhost:11434") -> List[str]:
        url = f"{base_url.rstrip('/')}/api/tags"
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
