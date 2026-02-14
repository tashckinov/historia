from historia_bot.game import GameMode, GameState, build_world_update_prompt, plan_event_counts, validate_player_action
from historia_bot.world_state import WorldState


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
    assert "Срез WorldState для страны игрока" in prompt
    assert "План количества событий на этот ход" in prompt
    assert "Итого статей к генерации" in prompt


def test_validate_action_rejects_third_party_treaty() -> None:
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Подписать договор от имени Аргентины с Бразилией",
        world_state=None,
    )
    assert result.is_valid is False
    assert "третьих стран" in result.reason


def test_validate_action_normalizes_impossible_territorial_transfer() -> None:
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Передать территорию Аргентины Бразилии",
        world_state=None,
    )
    assert result.is_valid is True
    assert result.is_partial is True
    assert "дипломатическое предложение" in result.normalized_action


def test_validate_action_rejects_border_change_between_foreign_states() -> None:
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Изменить границы между Аргентиной и Бразилией",
        world_state=None,
    )
    assert result.is_valid is False
    assert "изменение границ" in result.reason


def test_validate_action_uses_world_state_ownership() -> None:
    world_state = WorldState(country_regions={"Уругвай": ["Монтевидео"]})
    result = validate_player_action(
        player_country="Уругвай",
        action_text="Уступить территорию Буэнос-Айреса Бразилии",
        world_state=world_state,
    )
    assert result.is_valid is False
    assert "не владеет" in result.reason


def test_plan_event_counts_depends_on_period_and_actions() -> None:
    state = GameState(mode=GameMode.HISTORICAL_SIMULATION, country="France", model="qwen3:8b")
    state.add_action("A1")
    state.add_action("A2")
    state.add_dialog("ЕС", "D1")

    player_month, random_month, total_month = plan_event_counts(state, "1 месяц", rng=__import__("random").Random(1))
    player_year, random_year, total_year = plan_event_counts(state, "1 год", rng=__import__("random").Random(1))

    assert player_year >= player_month
    assert 0 <= random_month <= 2
    assert 2 <= random_year <= 3
    assert 1 <= total_month <= 15
    assert 1 <= total_year <= 15
