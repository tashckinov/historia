from historia_bot.game import GameMode, GameState
from historia_bot.storage import SqliteStorage


def test_storage_roundtrip(tmp_path):
    db = tmp_path / "historia.sqlite3"
    storage = SqliteStorage(str(db))

    state = GameState(mode=GameMode.PRESENT, country="Poland", model="qwen3:8b")
    state.add_action("Подписать оборонный пакт")
    state.add_dialog("НАТО", "Усилить присутствие")
    storage.save_user_state(123, state, "advisor")

    loaded_state, loaded_waiting = storage.load_user_state(123)
    assert loaded_state.mode == GameMode.PRESENT
    assert loaded_state.country == "Poland"
    assert loaded_state.model == "qwen3:8b"
    assert loaded_waiting == "advisor"
    assert loaded_state.current_turn.actions[0].text == "Подписать оборонный пакт"
    assert loaded_state.current_turn.dialogs[0].partner == "НАТО"


def test_storage_delete(tmp_path):
    db = tmp_path / "historia.sqlite3"
    storage = SqliteStorage(str(db))

    state = GameState(country="France")
    storage.save_user_state(1, state, None)
    storage.delete_user_state(1)

    loaded_state, loaded_waiting = storage.load_user_state(1)
    assert loaded_state.country is None
    assert loaded_waiting is None
