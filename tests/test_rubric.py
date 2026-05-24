"""Tests for rubric scoring functions."""

from __future__ import annotations

from src.rubric import WEIGHTS, CriterionScore, Scores, case_id, weighted_score


def _scores(ref=3, causal=3, bal=3, theme=3, mech=3, comp=3):
    return Scores(
        reference_integrity=CriterionScore(score=ref, reason="ok"),
        causal_chain=CriterionScore(score=causal, reason="ok"),
        balance=CriterionScore(score=bal, reason="ok"),
        thematic_coherence=CriterionScore(score=theme, reason="ok"),
        mechanical_sense=CriterionScore(score=mech, reason="ok"),
        completeness=CriterionScore(score=comp, reason="ok"),
    )


def test_weighted_score_all_fives():
    assert weighted_score(_scores(5, 5, 5, 5, 5, 5)) == 5.0


def test_weighted_score_all_ones():
    assert weighted_score(_scores(1, 1, 1, 1, 1, 1)) == 1.0


def test_weighted_score_mixed():
    # ref=5*3 + causal=3*3 + bal=4*2 + theme=4*2 + mech=2*1 + comp=2*1 = 15+9+8+8+2+2 = 44
    # 44 / 12 = 3.6667
    result = weighted_score(_scores(ref=5, causal=3, bal=4, theme=4, mech=2, comp=2))
    assert result == 3.67


def test_case_id_format():
    case = {
        "genre": "sci-fi",
        "mood": "tense",
        "player_class": "engineer",
        "target_difficulty": "hard",
    }
    assert case_id(case) == "sci-fi_tense_engineer_hard"


def test_weights_sum_to_twelve():
    assert sum(WEIGHTS.values()) == 12
