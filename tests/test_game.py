from historia_bot.game import GameMode, GameState, build_world_update_prompt


def test_action_limit():
    state = GameState(mode=GameMode.HISTORICAL_SIMULATION, country="Россия", model="qwen3:8b")
    for i in range(15):
        assert state.add_action(f"действие {i}")
    assert not state.add_action("лишнее")


def test_prompt_contains_data():
    state = GameState(mode=GameMode.HISTORICAL_SIMULATION, country="France", model="qwen3:8b")
    state.add_action("Увеличить оборонный бюджет")
    state.add_dialog("ЕС", "Продвинуть новые санкции")

    prompt = build_world_update_prompt(state, "1 месяц")
    assert "France" in prompt
    assert "qwen3:8b" in prompt
    assert "Увеличить оборонный бюджет" in prompt
    assert "ЕС" in prompt
    assert "1 месяц" in prompt
    assert "Follow all historical events past the start date." in prompt
