"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src import paths

SAMPLE_CASE = {
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

FAKE_NESTED_LEVEL = {
    "theme": "dungeon",
    "setting": "Dark dungeon",
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
        {
            "location": "Room 2",
            "enemy": {"name": "Bat", "health": 20, "damage": 10, "weakness": "Shield"},
            "hazard": "Pit traps",
            "pickup": {"name": "Torch", "effect": "Lights dark areas"},
            "trigger": "Wall crumbles",
        },
        {
            "location": "Room 3",
            "enemy": {"name": "Snake", "health": 30, "damage": 15, "weakness": "Torch"},
            "hazard": "Poison gas",
            "pickup": {"name": "Amulet", "effect": "Dispels boss shield"},
            "trigger": "Floor opens to boss lair",
        },
    ],
    "boss": {
        "name": "Dragon",
        "health": 200,
        "damage": 40,
        "weakness": "Amulet",
        "victory_condition": "Use Amulet then strike with Sword",
    },
    "objective": "Defeat the Dragon",
    "reward": "Gold",
}


def make_judgment(ref=5, causal=4, bal=4, theme=4, mech=4, comp=4):
    """Build a minimal valid judgment dict."""
    return {
        "summary": "Test level.",
        "scores": {
            "reference_integrity": {"score": ref, "reason": "ok"},
            "causal_chain": {"score": causal, "reason": "ok"},
            "balance": {"score": bal, "reason": "ok"},
            "thematic_coherence": {"score": theme, "reason": "ok"},
            "mechanical_sense": {"score": mech, "reason": "ok"},
            "completeness": {"score": comp, "reason": "ok"},
        },
        "best_element": "good",
        "worst_element": "fine",
        "overall": "solid",
    }


@pytest.fixture()
def project_dir(tmp_path):
    """Set up a temporary project directory and configure paths."""
    for d in ["inputs", "results/raw", "results/normalized",
              "results/judgments", "results/scores", "results/analysis"]:
        (tmp_path / d).mkdir(parents=True)
    paths.set_root(tmp_path)
    yield tmp_path
    paths.set_root(Path.cwd())


@pytest.fixture()
def mock_genai():
    """Patch the genai client to return a fake response."""
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 100
    mock_usage.candidates_token_count = 300
    mock_usage.thoughts_token_count = 0

    mock_response = MagicMock()
    mock_response.text = json.dumps(FAKE_FLAT_LEVEL)
    mock_response.usage_metadata = mock_usage

    with patch("src.generate.genai") as genai:
        genai.Client.return_value.models.generate_content.return_value = mock_response
        yield genai


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT", "test-project")
