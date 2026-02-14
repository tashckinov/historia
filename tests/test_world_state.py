from historia_bot.world_state import WorldState


def test_world_state_roundtrip_dict() -> None:
    original = WorldState(
        territory_owner={"RegionA": "A"},
        country_regions={"A": ["RegionA"]},
        active_wars=[("A", "B")],
        active_truces=[("C", "D")],
    )
    restored = WorldState.from_dict(original.to_dict())
    assert restored.territory_owner["RegionA"] == "A"
    assert restored.country_regions["A"] == ["RegionA"]
    assert ("A", "B") in restored.active_wars
    assert ("C", "D") in restored.active_truces


def test_apply_confirmed_updates_only() -> None:
    state = WorldState(territory_owner={"RegionA": "A"}, country_regions={"A": ["RegionA"]})
    articles = [
        {
            "confirmed": False,
            "territory_changes": [{"region": "RegionA", "to": "B"}],
        },
        {
            "confirmed": True,
            "territory_changes": [{"region": "RegionA", "to": "B"}],
            "wars_started": [["A", "B"]],
        },
    ]
    state.apply_confirmed_updates(articles)
    assert state.territory_owner["RegionA"] == "B"
    assert "RegionA" in state.country_regions["B"]
    assert ("A", "B") in state.active_wars
