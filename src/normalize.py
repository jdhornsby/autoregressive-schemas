"""Normalize any variant's output to a common nested format for judging."""

from __future__ import annotations

FLAT_VARIANTS = frozenset({"flat_alpha"})

ENCOUNTER_COUNT = 3


def _normalize_flat(raw: dict) -> dict:
    encounters = []
    for i in range(ENCOUNTER_COUNT):
        encounters.append(
            {
                "location": raw[f"encounter_{i}_location"],
                "enemy": {
                    "name": raw[f"encounter_{i}_enemy_name"],
                    "health": raw[f"encounter_{i}_enemy_health"],
                    "damage": raw[f"encounter_{i}_enemy_damage"],
                    "weakness": raw[f"encounter_{i}_enemy_weakness"],
                },
                "hazard": raw[f"encounter_{i}_hazard"],
                "pickup": {
                    "name": raw[f"encounter_{i}_pickup_name"],
                    "effect": raw[f"encounter_{i}_pickup_effect"],
                },
                "trigger": raw[f"encounter_{i}_trigger"],
            }
        )
    return {
        "theme": raw["theme"],
        "setting": raw["setting"],
        "player_weapon": raw["player_weapon"],
        "player_weapon_damage": raw["player_weapon_damage"],
        "player_health": raw["player_health"],
        "encounters": encounters,
        "boss": {
            "name": raw["boss_name"],
            "health": raw["boss_health"],
            "damage": raw["boss_damage"],
            "weakness": raw["boss_weakness"],
            "victory_condition": raw["boss_victory_condition"],
        },
        "objective": raw["objective"],
        "reward": raw["reward"],
    }


def _normalize_nested(raw: dict) -> dict:
    return {
        "theme": raw["theme"],
        "setting": raw["setting"],
        "player_weapon": raw["player_weapon"],
        "player_weapon_damage": raw["player_weapon_damage"],
        "player_health": raw["player_health"],
        "encounters": [
            {
                "location": enc["location"],
                "enemy": {
                    "name": enc["enemy"]["name"],
                    "health": enc["enemy"]["health"],
                    "damage": enc["enemy"]["damage"],
                    "weakness": enc["enemy"]["weakness"],
                },
                "hazard": enc["hazard"],
                "pickup": {
                    "name": enc["pickup"]["name"],
                    "effect": enc["pickup"]["effect"],
                },
                "trigger": enc["trigger"],
            }
            for enc in raw["encounters"]
        ],
        "boss": {
            "name": raw["boss"]["name"],
            "health": raw["boss"]["health"],
            "damage": raw["boss"]["damage"],
            "weakness": raw["boss"]["weakness"],
            "victory_condition": raw["boss"]["victory_condition"],
        },
        "objective": raw["objective"],
        "reward": raw["reward"],
    }


def normalize(variant_name: str, raw: dict) -> dict:
    if variant_name in FLAT_VARIANTS:
        return _normalize_flat(raw)
    return _normalize_nested(raw)
