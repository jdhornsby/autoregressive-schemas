# Striking pair 3: jungle_ominous_necromancer_hard

## Input

- Genre: jungle
- Mood: ominous
- Player class: necromancer
- Target difficulty: hard

## Scores

| Criterion | flat_alpha | nested_narrative |
|-----------|-----------|-----------------|
| reference_integrity | 3 | 5 |
| causal_chain | 3 | 5 |
| balance | 3 | 5 |
| thematic_coherence | 5 | 5 |
| mechanical_sense | 4 | 5 |
| completeness | 3 | 5 |
| **weighted** | **3.42** | **5.00** |

## flat_alpha judge notes

**Best element:** Enemy naming — Rotting Vine-Stalker, Carrion Ape, Shadow Jaguar, Grave Warden of the Canopy — creates a coherent dark jungle bestiary that feels designed around the necromancer class.
**Worst element:** Boss victory condition 'Purify the Blighted Heart' provides no instruction on using the stated boss weakness item (Soul-Infused Obsidian Dagger) — players would not know how to end the fight.

## nested_narrative judge notes

**Best element:** The Verdant Lich boss — a lich that has fused with the jungle itself — is the most inventive boss concept in the jungle section and creates a natural climax for a necromancer exploring corrupted ruins.
**Worst element:** Nothing stands out as a serious flaw. The level is well-constructed across all criteria.

## flat_alpha full output

```json
{
  "theme": "Dark Necromantic Overgrowth",
  "setting": "Sunken Amazonian Rainforest",
  "player_weapon": "Scythe of Withering",
  "player_weapon_damage": 15,
  "player_health": 100,
  "encounters": [
    {
      "location": "Overgrown Ruins",
      "enemy": {
        "name": "Rotting Vine-Stalker",
        "health": 40,
        "damage": 10,
        "weakness": "Scythe of Withering"
      },
      "hazard": "Toxic Fog",
      "pickup": {
        "name": "Corpse-Lantern",
        "effect": "Increases attack range"
      },
      "trigger": "Light the Corpse-Lantern to reveal the path to the altar"
    },
    {
      "location": "Deep Mud Flats",
      "enemy": {
        "name": "Carrion Ape",
        "health": 60,
        "damage": 15,
        "weakness": "Corpse-Lantern"
      },
      "hazard": "Swamp Quicksand",
      "pickup": {
        "name": "Soul-Infused Obsidian Dagger",
        "effect": "Stuns enemies on strike"
      },
      "trigger": "Slay the Ape to activate the ancient stone gate"
    },
    {
      "location": "Ancient Temple Courtyard",
      "enemy": {
        "name": "Shadow Jaguar",
        "health": 80,
        "damage": 20,
        "weakness": "Scythe of Withering"
      },
      "hazard": "Spiky Undergrowth",
      "pickup": {
        "name": "Essence Vials",
        "effect": "Restores 20 health"
      },
      "trigger": "Defeat the Jaguar to unlock the sanctum entrance"
    }
  ],
  "boss": {
    "name": "Grave Warden of the Canopy",
    "health": 150,
    "damage": 25,
    "weakness": "Soul-Infused Obsidian Dagger",
    "victory_condition": "Purify the Blighted Heart"
  },
  "objective": "Cleanse the corrupted heart of the jungle",
  "reward": "Cursed Jungle Crown"
}
```

## nested_narrative full output

```json
{
  "theme": "Ominous Jungle",
  "setting": "The Whispering Canopy, a dense, fog-ridden rainforest where ancient ruins are overgrown with pulsating bioluminescent fungi.",
  "player_weapon": "Scythe of the Withered Grave",
  "player_weapon_damage": 25,
  "player_health": 100,
  "encounters": [
    {
      "location": "The Mossy Path",
      "enemy": {
        "name": "Rotten Stalker",
        "health": 50,
        "damage": 15,
        "weakness": "Scythe of the Withered Grave"
      },
      "hazard": "Toxic Spore Vents",
      "pickup": {
        "name": "Corpse-Candle Flame",
        "effect": "Ignites necrotic energy to burn through organic barriers."
      },
      "trigger": "Defeating the Stalker reveals a hidden switch that disables the containment field of the next zone."
    },
    {
      "location": "The Serpent Coil Altar",
      "enemy": {
        "name": "Vine-Strangled Revenant",
        "health": 70,
        "damage": 20,
        "weakness": "Corpse-Candle Flame"
      },
      "hazard": "Rapidly closing iron vines",
      "pickup": {
        "name": "Cursed Obsidian Eye",
        "effect": "Allows the wearer to see through illusions and reveals structural weak points."
      },
      "trigger": "The Revenant drops a key shard that unlocks the entrance to the Forbidden Ziggurat."
    },
    {
      "location": "The Shadowed Bridge",
      "enemy": {
        "name": "Spectral Guardian",
        "health": 90,
        "damage": 30,
        "weakness": "Cursed Obsidian Eye"
      },
      "hazard": "Unstable crumbling stonework",
      "pickup": {
        "name": "Heart of the Jungle",
        "effect": "A pulsating gem that destabilizes unnatural life forces."
      },
      "trigger": "The Guardian dissipates to form a portal leading directly to the boss chamber."
    }
  ],
  "boss": {
    "name": "The Verdant Lich",
    "health": 250,
    "damage": 45,
    "weakness": "Heart of the Jungle",
    "victory_condition": "Channel the Heart of the Jungle into the Lich's core to strip its immortality and land the final blow."
  },
  "objective": "Purge the corruption from the jungle and reclaim the Forbidden Ziggurat.",
  "reward": "The Necromancer's Amulet of Life-Stealing."
}
```
