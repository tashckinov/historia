from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class GameMode(str, Enum):
    PRESENT = "Настоящее время"
    PRESENT_WITH_EVENTS = "Настоящее + события 2025->сейчас"
    MODE_2015 = "2015 + события 2025->сейчас"


PERIOD_OPTIONS = ["1 неделя", "1 месяц", "3 месяца", "6 месяцев", "1 год"]
DIALOG_PARTNERS = ["США", "Китай", "ЕС", "НАТО", "ООН", "БРИКС"]
MAX_ACTIONS_PER_TURN = 15


@dataclass
class TurnAction:
    text: str


@dataclass
class DialogueEntry:
    partner: str
    message: str


@dataclass
class Turn:
    actions: List[TurnAction] = field(default_factory=list)
    dialogs: List[DialogueEntry] = field(default_factory=list)


@dataclass
class GameState:
    mode: GameMode | None = None
    country: str | None = None
    model: str | None = None
    current_turn: Turn = field(default_factory=Turn)

    def add_action(self, text: str) -> bool:
        if len(self.current_turn.actions) >= MAX_ACTIONS_PER_TURN:
            return False
        self.current_turn.actions.append(TurnAction(text=text.strip()))
        return True

    def add_dialog(self, partner: str, message: str) -> None:
        self.current_turn.dialogs.append(DialogueEntry(partner=partner, message=message.strip()))

    def can_finish_turn(self) -> bool:
        return bool(self.current_turn.actions or self.current_turn.dialogs)

    def reset_turn(self) -> None:
        self.current_turn = Turn()


def build_world_update_prompt(state: GameState, period: str) -> str:
    actions = "\n".join(f"- {a.text}" for a in state.current_turn.actions) or "- Нет действий"
    dialogs = (
        "\n".join(f"- {d.partner}: {d.message}" for d in state.current_turn.dialogs)
        or "- Нет диалогов"
    )
    return f"""
Ты — симулятор мировой геополитики в текстовой игре.

Контекст партии:
- Режим: {state.mode.value if state.mode else "Не выбран"}
- Страна игрока: {state.country or "Не выбрана"}
- AI-модель: {state.model or "Не выбрана"}
- Период перемотки: {period}

Действия игрока за период:
{actions}

Диалоги игрока за период:
{dialogs}

Сгенерируй последствия в формате JSON:
{{
  "articles": [
    {{"title": "...", "description": "..."}}
  ]
}}

Правила вывода:
1) Верни от 1 до 15 статей в зависимости от насыщенности действий.
2) Каждая статья должна быть реалистичной, связанной с действиями/диалогами и мировыми реакциями.
3) В описании учитывай экономику, дипломатию, безопасность, внутреннюю политику, международные альянсы.
4) Пиши на русском языке.
5) Верни ТОЛЬКО JSON без markdown.
""".strip()
