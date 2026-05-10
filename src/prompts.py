"""Single prompt for all schema variants.

Constant across all variants. Describes the task and constraints,
not the schema. Structure is the only independent variable.
"""

from __future__ import annotations

PROMPT = """\
Design a game level.
Genre: {genre}. Mood: {mood}. Player class: {player_class}.
Target difficulty: {target_difficulty}. Encounters: 3, one enemy each.

Enemy weaknesses must reference the player weapon or a pickup from \
a prior encounter. The boss weakness must reference a specific pickup \
the player acquired during encounters. Each encounter trigger must \
set up the next encounter or the boss fight.
"""
