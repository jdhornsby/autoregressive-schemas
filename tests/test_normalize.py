"""Tests for the normalization module."""

from __future__ import annotations

from src.normalize import normalize

from .conftest import FAKE_FLAT_LEVEL, FAKE_NESTED_LEVEL


def test_normalize_flat_produces_nested():
    norm = normalize("flat_alpha", FAKE_FLAT_LEVEL)

    assert len(norm["encounters"]) == 3
    assert norm["encounters"][0]["enemy"]["name"] == "Shadow Crawler"
    assert norm["encounters"][0]["enemy"]["weakness"] == "Flame Staff"
    assert norm["encounters"][2]["enemy"]["name"] == "Frost Wraith"
    assert norm["boss"]["name"] == "Frost Lich"
    assert norm["boss"]["weakness"] == "Ember Shard"
    assert norm["theme"] == "ice temple"


def test_normalize_flat_field_order():
    norm = normalize("flat_alpha", FAKE_FLAT_LEVEL)
    keys = list(norm.keys())
    assert keys[0] == "theme"
    assert keys[1] == "setting"
    assert "encounters" in keys
    assert "boss" in keys


def test_normalize_nested_reorders():
    norm = normalize("ui_contract", FAKE_NESTED_LEVEL)
    assert list(norm.keys())[0] == "theme"
    assert norm["encounters"][0]["enemy"]["name"] == "Rat"
    assert norm["boss"]["name"] == "Dragon"


def test_normalize_nested_preserves_all_encounters():
    norm = normalize("nested_narrative", FAKE_NESTED_LEVEL)
    assert len(norm["encounters"]) == 3
    names = [e["enemy"]["name"] for e in norm["encounters"]]
    assert names == ["Rat", "Bat", "Snake"]


def test_normalize_nested_encounter_field_order():
    norm = normalize("nested_narrative", FAKE_NESTED_LEVEL)
    enc_keys = list(norm["encounters"][0].keys())
    assert enc_keys == ["location", "enemy", "hazard", "pickup", "trigger"]
