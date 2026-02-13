from historia_bot.game import GameMode, GameState
from historia_bot.storage import SqliteStorage


def test_storage_roundtrip_with_sessions(tmp_path):
    db = tmp_path / "historia.sqlite3"
    storage = SqliteStorage(str(db))

    session_id = storage.create_session(123)
    state = GameState(mode=GameMode.HISTORICAL_SIMULATION, country="Poland", model="qwen3:8b")
    state.add_action("Подписать оборонный пакт")
    state.add_dialog("НАТО", "Усилить присутствие")
    storage.save_session_state(123, session_id, state, "advisor")

    loaded_state, loaded_waiting = storage.load_session_state(123, session_id)
    assert loaded_state.mode == GameMode.HISTORICAL_SIMULATION
    assert loaded_state.country == "Poland"
    assert loaded_state.model == "qwen3:8b"
    assert loaded_waiting == "advisor"
    assert loaded_state.current_turn.actions[0].text == "Подписать оборонный пакт"
    assert loaded_state.current_turn.dialogs[0].partner == "НАТО"


def test_list_and_activate_sessions(tmp_path):
    db = tmp_path / "historia.sqlite3"
    storage = SqliteStorage(str(db))

    first = storage.create_session(1)
    second = storage.create_session(1)
    sessions = storage.list_sessions(1)

    assert len(sessions) == 2
    assert sessions[0]["session_id"] == second
    assert sessions[0]["active"] is True

    storage.set_active_session(1, first)
    assert storage.get_active_session_id(1) == first
