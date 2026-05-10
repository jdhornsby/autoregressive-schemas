"""Schema variants for the game level generator."""

from __future__ import annotations

from pydantic import BaseModel

# 1. flat_alpha - all 39 fields flat, sorted A-Z


class FlatAlphaLevel(BaseModel):
    boss_damage: int
    boss_health: int
    boss_name: str
    boss_victory_condition: str
    boss_weakness: str
    encounter_0_enemy_damage: int
    encounter_0_enemy_health: int
    encounter_0_enemy_name: str
    encounter_0_enemy_weakness: str
    encounter_0_hazard: str
    encounter_0_location: str
    encounter_0_pickup_effect: str
    encounter_0_pickup_name: str
    encounter_0_trigger: str
    encounter_1_enemy_damage: int
    encounter_1_enemy_health: int
    encounter_1_enemy_name: str
    encounter_1_enemy_weakness: str
    encounter_1_hazard: str
    encounter_1_location: str
    encounter_1_pickup_effect: str
    encounter_1_pickup_name: str
    encounter_1_trigger: str
    encounter_2_enemy_damage: int
    encounter_2_enemy_health: int
    encounter_2_enemy_name: str
    encounter_2_enemy_weakness: str
    encounter_2_hazard: str
    encounter_2_location: str
    encounter_2_pickup_effect: str
    encounter_2_pickup_name: str
    encounter_2_trigger: str
    objective: str
    player_health: int
    player_weapon: str
    player_weapon_damage: int
    reward: str
    setting: str
    theme: str


# 2. grouped_by_type - nested, fields sorted by data type (ints first)


class TypeEnemy(BaseModel):
    health: int
    damage: int
    name: str
    weakness: str


class TypePickup(BaseModel):
    name: str
    effect: str


class TypeEncounter(BaseModel):
    enemy: TypeEnemy
    pickup: TypePickup
    location: str
    hazard: str
    trigger: str


class TypeBoss(BaseModel):
    health: int
    damage: int
    name: str
    weakness: str
    victory_condition: str


class TypeGroupedLevel(BaseModel):
    player_weapon_damage: int
    player_health: int
    player_weapon: str
    theme: str
    setting: str
    encounters: list[TypeEncounter]
    boss: TypeBoss
    objective: str
    reward: str


# 3. append_order - nested, fields in the order they'd accumulate over sprints


class AppendEnemy(BaseModel):
    name: str
    health: int
    damage: int
    weakness: str


class AppendPickup(BaseModel):
    name: str
    effect: str


class AppendEncounter(BaseModel):
    location: str
    enemy: AppendEnemy
    trigger: str
    pickup: AppendPickup
    hazard: str


class AppendBoss(BaseModel):
    name: str
    health: int
    damage: int
    weakness: str
    victory_condition: str


class AppendOrderLevel(BaseModel):
    theme: str
    encounters: list[AppendEncounter]
    objective: str
    player_weapon: str
    player_weapon_damage: int
    player_health: int
    boss: AppendBoss
    setting: str
    reward: str


# 4. ui_contract - nested, fields ordered by UI render sequence


class UIEnemy(BaseModel):
    name: str
    health: int
    damage: int
    weakness: str


class UIPickup(BaseModel):
    name: str
    effect: str


class UIEncounter(BaseModel):
    location: str
    enemy: UIEnemy
    hazard: str
    pickup: UIPickup
    trigger: str


class UIBoss(BaseModel):
    name: str
    health: int
    damage: int
    victory_condition: str
    weakness: str


class UIContractLevel(BaseModel):
    objective: str
    player_weapon: str
    player_weapon_damage: int
    player_health: int
    encounters: list[UIEncounter]
    boss: UIBoss
    reward: str
    theme: str
    setting: str


# 5. alpha_nested - nested, but keys sorted A-Z at every level (linter-style)


class AlphaEnemy(BaseModel):
    damage: int
    health: int
    name: str
    weakness: str


class AlphaPickup(BaseModel):
    effect: str
    name: str


class AlphaEncounter(BaseModel):
    enemy: AlphaEnemy
    hazard: str
    location: str
    pickup: AlphaPickup
    trigger: str


class AlphaBoss(BaseModel):
    damage: int
    health: int
    name: str
    victory_condition: str
    weakness: str


class AlphaNestedLevel(BaseModel):
    boss: AlphaBoss
    encounters: list[AlphaEncounter]
    objective: str
    player_health: int
    player_weapon: str
    player_weapon_damage: int
    reward: str
    setting: str
    theme: str


# 6. nested_narrative - nested, fields in design-decision order


class NarrativeEnemy(BaseModel):
    name: str
    health: int
    damage: int
    weakness: str


class NarrativePickup(BaseModel):
    name: str
    effect: str


class NarrativeEncounter(BaseModel):
    location: str
    enemy: NarrativeEnemy
    hazard: str
    pickup: NarrativePickup
    trigger: str


class NarrativeBoss(BaseModel):
    name: str
    health: int
    damage: int
    weakness: str
    victory_condition: str


class NarrativeLevel(BaseModel):
    theme: str
    setting: str
    player_weapon: str
    player_weapon_damage: int
    player_health: int
    encounters: list[NarrativeEncounter]
    boss: NarrativeBoss
    objective: str
    reward: str
