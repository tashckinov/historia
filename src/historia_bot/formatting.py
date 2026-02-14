from __future__ import annotations

import html
import re


def _normalize_llm_text(text: str) -> str:
    return text.replace("\\n", "\n").replace("\\t", "\t").strip()


def _markdown_bold_to_html(text: str) -> str:
    pattern = re.compile(r"\*\*(.+?)\*\*")
    parts: list[str] = []
    cursor = 0
    for match in pattern.finditer(text):
        parts.append(html.escape(text[cursor:match.start()]))
        parts.append(f"<b>{html.escape(match.group(1))}</b>")
        cursor = match.end()
    parts.append(html.escape(text[cursor:]))
    return "".join(parts)


def format_advisor_message(text: str) -> str:
    normalized = _normalize_llm_text(text)
    return _markdown_bold_to_html(normalized)
