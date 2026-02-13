from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Tuple

from historia_bot.game import DialogueEntry, GameMode, GameState, Turn, TurnAction


class SqliteStorage:
    def __init__(self, db_path: str = "historia.sqlite3") -> None:
        self._db_path = db_path
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_state (
                    user_id INTEGER PRIMARY KEY,
                    mode TEXT,
                    country TEXT,
                    model TEXT,
                    waiting TEXT,
                    actions_json TEXT NOT NULL DEFAULT '[]',
                    dialogs_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )

    def load_user_state(self, user_id: int) -> Tuple[GameState, str | None]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT mode, country, model, waiting, actions_json, dialogs_json
                FROM user_state
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return GameState(), None

        mode_raw, country, model, waiting, actions_raw, dialogs_raw = row
        mode = None
        if isinstance(mode_raw, str):
            for candidate in GameMode:
                if candidate.value == mode_raw:
                    mode = candidate
                    break

        state = GameState(mode=mode, country=country, model=model)

        actions_payload = json.loads(actions_raw) if actions_raw else []
        dialogs_payload = json.loads(dialogs_raw) if dialogs_raw else []

        state.current_turn = Turn(
            actions=[
                TurnAction(text=item.get("text", "").strip())
                for item in actions_payload
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ],
            dialogs=[
                DialogueEntry(
                    partner=item.get("partner", "").strip(),
                    message=item.get("message", "").strip(),
                )
                for item in dialogs_payload
                if isinstance(item, dict)
                and isinstance(item.get("partner"), str)
                and isinstance(item.get("message"), str)
            ],
        )
        return state, waiting

    def save_user_state(self, user_id: int, state: GameState, waiting: str | None) -> None:
        actions_json = json.dumps([{"text": a.text} for a in state.current_turn.actions], ensure_ascii=False)
        dialogs_json = json.dumps(
            [{"partner": d.partner, "message": d.message} for d in state.current_turn.dialogs],
            ensure_ascii=False,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_state (user_id, mode, country, model, waiting, actions_json, dialogs_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    mode=excluded.mode,
                    country=excluded.country,
                    model=excluded.model,
                    waiting=excluded.waiting,
                    actions_json=excluded.actions_json,
                    dialogs_json=excluded.dialogs_json
                """,
                (
                    user_id,
                    state.mode.value if state.mode else None,
                    state.country,
                    state.model,
                    waiting,
                    actions_json,
                    dialogs_json,
                ),
            )

    def delete_user_state(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
