Read `<FILE_PATH>`. It contains a JSON array of single-player game levels. Note the array length — call it N. Your output must contain exactly N entries, one per level. Process every level; do not stop after the first few.

Mechanics: the player fights three encounters in order. They start with `player_weapon`. After defeating each encounter's enemy, they collect that encounter's `pickup.name`.

**Pickups are NOT available DURING the encounter they appear in.** The pickup from encounter i is only acquired AFTER its enemy is defeated, so it can only be used in encounter i+1 and later.

Inventory facing each enemy:
- Encounter 0: {player_weapon}
- Encounter 1: {player_weapon, encounter[0].pickup.name}
- Encounter 2: {player_weapon, encounter[0].pickup.name, encounter[1].pickup.name}

**Important:** Treat the inventory list I describe above as a closed set. Do NOT add encounter[i].pickup.name to encounter[i]'s inventory. If the weakness for encounter 2 names an item that only appears as encounter[2].pickup.name, that's a chain break — NOT satisfied.

Question (three per level — one per encounter): does anything in the inventory at that point satisfy `encounter[i].enemy.weakness`?

Read names by meaning, not strict spelling. Examples:
- weapon "Flame Burst Staff" satisfies weakness "Flame Burst" — the staff produces it. SATISFIES.
- pickup "Voltage Conduit" satisfies weakness "Chain Lightning" — the conduit channels lightning. SATISFIES.
- inventory ["Iron Greataxe", "Obsidian Spike", "Storm Essence"] does NOT satisfy weakness "Charged Obsidian Spike" — none of those three IS a charged spike, even if combining them might charge one. DOES NOT SATISFY.
- pickup "Healing Potion" does NOT satisfy weakness "Holy Light".

Do not write or run code. Read each (weakness, inventory) pair and decide.

**Before returning, count your output entries and verify the count equals N. If it does not, complete the missing levels first.**

Return only JSON, no preamble, no fences:

```
[
  {
    "case_id": "<genre>_<mood>_<player_class>_<target_difficulty>",
    "encounters": [
      { "index": 0, "weakness": "<verbatim>", "inventory": ["<weapon>"], "satisfied": true|false },
      { "index": 1, "weakness": "<verbatim>", "inventory": ["<weapon>", "<pickup_0>"], "satisfied": true|false },
      { "index": 2, "weakness": "<verbatim>", "inventory": ["<weapon>", "<pickup_0>", "<pickup_1>"], "satisfied": true|false }
    ],
    "n_satisfied": 0|1|2|3
  }
]
```
