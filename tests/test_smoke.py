"""Smoke test: generation and normalization with a mocked Vertex AI client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src import VARIANTS
from src.normalize import normalize
from src.run_eval import run_one

CASE = {
    "genre": "fantasy",
    "mood": "ominous",
    "player_class": "pyromancer",
    "target_difficulty": "medium",
}

FAKE_FLAT_LEVEL = {
    "boss_damage": 30,
    "boss_health": 150,
    "boss_name": "Frost Lich",
    "boss_victory_condition": "Use Ember Shard to break shield, then strike",
    "boss_weakness": "Ember Shard",
    "encounter_0_enemy_damage": 10,
    "encounter_0_enemy_health": 40,
    "encounter_0_enemy_name": "Shadow Crawler",
    "encounter_0_enemy_weakness": "Flame Staff",
    "encounter_0_hazard": "Toxic fog",
    "encounter_0_location": "Crypt entrance",
    "encounter_0_pickup_effect": "Doubles fire damage for one attack",
    "encounter_0_pickup_name": "Ember Shard",
    "encounter_0_trigger": "Defeating crawlers opens the inner gate",
    "encounter_1_enemy_damage": 15,
    "encounter_1_enemy_health": 60,
    "encounter_1_enemy_name": "Ice Sentinel",
    "encounter_1_enemy_weakness": "Flame Staff",
    "encounter_1_hazard": "Falling icicles",
    "encounter_1_location": "Frozen corridor",
    "encounter_1_pickup_effect": "Prevents freezing in boss arena",
    "encounter_1_pickup_name": "Thawing Amulet",
    "encounter_1_trigger": "Corridor collapses, forcing forward",
    "encounter_2_enemy_damage": 20,
    "encounter_2_enemy_health": 80,
    "encounter_2_enemy_name": "Frost Wraith",
    "encounter_2_enemy_weakness": "Ember Shard",
    "encounter_2_hazard": "Freezing mist",
    "encounter_2_location": "Reliquary",
    "encounter_2_pickup_effect": "Restores health to full",
    "encounter_2_pickup_name": "Healing Crystal",
    "encounter_2_trigger": "Breaking the seal awakens the Frost Lich",
    "objective": "Defeat the Frost Lich",
    "player_health": 100,
    "player_weapon": "Flame Staff",
    "player_weapon_damage": 25,
    "reward": "Permafrost Staff",
    "setting": "A frozen crypt beneath a glacier",
    "theme": "ice temple",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT", "test-project")


def test_generate_and_normalize_flat():
    """Generate a flat-alpha level, verify normalization nests correctly."""
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 100
    mock_usage.candidates_token_count = 300
    mock_usage.thoughts_token_count = 0

    mock_response = MagicMock()
    mock_response.text = json.dumps(FAKE_FLAT_LEVEL)
    mock_response.usage_metadata = mock_usage

    with patch("src.generate.genai") as mock_genai:
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response
        result = run_one(VARIANTS[0], CASE)

    assert result["variant"] == "flat_alpha"

    # Raw preserves flat structure.
    assert "encounter_0_enemy_name" in result["output"]
    assert "encounters" not in result["output"]

    # Normalized is nested.
    norm = result["normalized"]
    assert len(norm["encounters"]) == 3
    assert norm["encounters"][0]["enemy"]["name"] == "Shadow Crawler"
    assert norm["encounters"][0]["enemy"]["weakness"] == "Flame Staff"
    assert norm["boss"]["weakness"] == "Ember Shard"
    assert norm["theme"] == "ice temple"


def test_normalize_nested_variant():
    """Normalize a nested variant - reorders to standard format."""
    nested = {
        "objective": "Defeat the boss",
        "player_weapon": "Sword",
        "player_weapon_damage": 20,
        "player_health": 100,
        "encounters": [
            {
                "location": "Room 1",
                "enemy": {"name": "Rat", "health": 10, "damage": 5, "weakness": "Sword"},
                "hazard": "Spikes",
                "pickup": {"name": "Shield", "effect": "Blocks one hit"},
                "trigger": "Door opens",
            },
        ],
        "boss": {
            "name": "Dragon",
            "health": 200,
            "damage": 40,
            "victory_condition": "Use Shield then strike",
            "weakness": "Shield",
        },
        "reward": "Gold",
        "theme": "dungeon",
        "setting": "Dark dungeon",
    }
    norm = normalize("ui_contract", nested)
    assert list(norm.keys())[0] == "theme"
    assert norm["encounters"][0]["enemy"]["name"] == "Rat"
    assert norm["boss"]["name"] == "Dragon"
