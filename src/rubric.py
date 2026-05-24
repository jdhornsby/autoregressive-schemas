"""Pydantic models for game level judgments and weighted-score computation.

Judgments are produced out-of-band by Claude Code sub-agents reading
judge_prompt.md. This module validates those judgments when score.py
loads them from disk.
"""

from __future__ import annotations

from pydantic import BaseModel, conint

WEIGHTS: dict[str, int] = {
    "reference_integrity": 3,
    "causal_chain": 3,
    "balance": 2,
    "thematic_coherence": 2,
    "mechanical_sense": 1,
    "completeness": 1,
}

assert sum(WEIGHTS.values()) == 12

Score = conint(ge=1, le=5)


class CriterionScore(BaseModel):
    score: Score
    reason: str


class Scores(BaseModel):
    reference_integrity: CriterionScore
    causal_chain: CriterionScore
    balance: CriterionScore
    thematic_coherence: CriterionScore
    mechanical_sense: CriterionScore
    completeness: CriterionScore


class Judgment(BaseModel):
    summary: str
    scores: Scores
    best_element: str
    worst_element: str
    overall: str


def weighted_score(scores: Scores) -> float:
    total = sum(getattr(scores, k).score * w for k, w in WEIGHTS.items())
    return round(total / sum(WEIGHTS.values()), 2)


def case_id(case: dict) -> str:
    """Build a unique key from a case dict, e.g. 'fantasy_ominous_pyromancer_medium'."""
    return f"{case['genre']}_{case['mood']}_{case['player_class']}_{case['target_difficulty']}"
