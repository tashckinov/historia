from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Tuple

from historia_bot.game import DialogueEntry, GameMode, GameState, Turn, TurnAction
from historia_bot.world_state import WorldState


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
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    session_name TEXT,
                    active INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            existing_session_cols = [row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()]
            if "session_name" not in existing_session_cols:
                conn.execute("ALTER TABLE sessions ADD COLUMN session_name TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id INTEGER PRIMARY KEY,
                    mode TEXT,
                    country TEXT,
                    model TEXT,
                    waiting TEXT,
                    actions_json TEXT NOT NULL DEFAULT '[]',
                    dialogs_json TEXT NOT NULL DEFAULT '[]',
                    world_state_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
                """
            )
            existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(session_state)").fetchall()]
            if "world_state_json" not in existing_cols:
                conn.execute("ALTER TABLE session_state ADD COLUMN world_state_json TEXT NOT NULL DEFAULT '{}'")

    def create_session(self, user_id: int, make_active: bool = True) -> int:
        with self._connect() as conn:
            cur = conn.execute("INSERT INTO sessions (user_id, active, session_name) VALUES (?, 0, ?)", (user_id, None))
            session_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO session_state (session_id, mode, country, model, waiting, actions_json, dialogs_json, world_state_json) VALUES (?, NULL, NULL, NULL, NULL, '[]', '[]', '{}')",
                (session_id,),
            )
            if make_active:
                conn.execute("UPDATE sessions SET active = 0 WHERE user_id = ?", (user_id,))
                conn.execute("UPDATE sessions SET active = 1 WHERE session_id = ?", (session_id,))
            return session_id

    def list_sessions(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.session_id, s.active, s.session_name, st.mode, st.country, st.model
                FROM sessions s
                LEFT JOIN session_state st ON st.session_id = s.session_id
                WHERE s.user_id = ?
                ORDER BY s.session_id DESC
                """,
                (user_id,),
            ).fetchall()
        return [
            {
                "session_id": int(row[0]),
                "active": bool(row[1]),
                "name": row[2],
                "mode": row[3],
                "country": row[4],
                "model": row[5],
            }
            for row in rows
        ]


    def set_session_name(self, user_id: int, session_id: int, name: str) -> None:
        clean = name.strip()
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET session_name = ? WHERE user_id = ? AND session_id = ?",
                (clean or None, user_id, session_id),
            )

    def delete_session(self, user_id: int, session_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ? AND session_id = ?", (user_id, session_id))

    def get_active_session_id(self, user_id: int) -> int | None:
        with self._connect() as conn:
            row = conn.execute("SELECT session_id FROM sessions WHERE user_id = ? AND active = 1", (user_id,)).fetchone()
        return int(row[0]) if row else None

    def set_active_session(self, user_id: int, session_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET active = 0 WHERE user_id = ?", (user_id,))
            conn.execute("UPDATE sessions SET active = 1 WHERE user_id = ? AND session_id = ?", (user_id, session_id))

    def clear_active_session(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET active = 0 WHERE user_id = ?", (user_id,))

    def load_session_state(self, user_id: int, session_id: int) -> Tuple[GameState, str | None, WorldState]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT st.mode, st.country, st.model, st.waiting, st.actions_json, st.dialogs_json, st.world_state_json
                FROM session_state st
                JOIN sessions s ON s.session_id = st.session_id
                WHERE s.user_id = ? AND s.session_id = ?
                """,
                (user_id, session_id),
            ).fetchone()

        if row is None:
            return GameState(), None, WorldState()

        mode_raw, country, model, waiting, actions_raw, dialogs_raw, world_state_raw = row
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
        world_state_payload = json.loads(world_state_raw) if world_state_raw else {}
        world_state = WorldState.from_dict(world_state_payload if isinstance(world_state_payload, dict) else {})
        return state, waiting, world_state

    def save_session_state(self, user_id: int, session_id: int, state: GameState, waiting: str | None, world_state: WorldState | None = None) -> None:
        actions_json = json.dumps([{"text": a.text} for a in state.current_turn.actions], ensure_ascii=False)
        dialogs_json = json.dumps(
            [{"partner": d.partner, "message": d.message} for d in state.current_turn.dialogs],
            ensure_ascii=False,
        )
        world_state_json = json.dumps((world_state or WorldState()).to_dict(), ensure_ascii=False)
        with self._connect() as conn:
            # keep relation ownership check in update where clause
            conn.execute(
                """
                UPDATE session_state
                SET mode = ?, country = ?, model = ?, waiting = ?, actions_json = ?, dialogs_json = ?, world_state_json = ?
                WHERE session_id = ?
                """,
                (
                    state.mode.value if state.mode else None,
                    state.country,
                    state.model,
                    waiting,
                    actions_json,
                    dialogs_json,
                    world_state_json,
                    session_id,
                ),
            )
            conn.execute("UPDATE sessions SET active = 1 WHERE user_id = ? AND session_id = ?", (user_id, session_id))

    # backward-compatible wrappers
    def load_user_state(self, user_id: int) -> Tuple[GameState, str | None, WorldState]:
        session_id = self.get_active_session_id(user_id)
        if session_id is None:
            return GameState(), None, WorldState()
        return self.load_session_state(user_id, session_id)

    def save_user_state(self, user_id: int, state: GameState, waiting: str | None, world_state: WorldState | None = None) -> None:
        session_id = self.get_active_session_id(user_id)
        if session_id is None:
            session_id = self.create_session(user_id, make_active=True)
        self.save_session_state(user_id, session_id, state, waiting, world_state)

    def delete_user_state(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
