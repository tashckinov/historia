from historia_bot.game import GameMode, GameState, build_world_update_prompt, validate_player_action


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
    assert "intent:" in prompt
    assert "feasibility:" in prompt
    assert "outcome:" in prompt
    assert "Невозможные действия не считаются совершившимися фактами" in prompt


def test_validate_action_rejects_third_party_treaty() -> None:
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Подписать договор от имени Аргентины с Бразилией",
        world_facts={},
    )
    assert result.is_valid is False
    assert "третьих стран" in result.reason


def test_validate_action_normalizes_impossible_territorial_transfer() -> None:
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Передать территорию Аргентины Бразилии",
        world_facts={},
    )
    assert result.is_valid is True
    assert result.is_partial is True
    assert "дипломатическое предложение" in result.normalized_action


def test_validate_action_rejects_border_change_between_foreign_states() -> None:
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Изменить границы между Аргентиной и Бразилией",
        world_facts={},
    )
    assert result.is_valid is False
    assert "изменение границ" in result.reason
