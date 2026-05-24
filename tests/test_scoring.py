"""Tests for scoring aggregation logic."""

from __future__ import annotations

import json

from src.scoring import aggregate_variants, compare_models, mean, sd, weighted_score_from_dict

from .conftest import SAMPLE_CASE, make_judgment


def test_mean():
    assert mean([1, 2, 3]) == 2.0


def test_mean_empty():
    assert mean([]) == 0.0


def test_sd():
    result = sd([2, 4, 4, 4, 5, 5, 7, 9])
    assert abs(result - 2.1381) < 0.001


def test_sd_single():
    assert sd([5.0]) == 0.0


def test_weighted_score_from_dict():
    scores = {
        "reference_integrity": {"score": 5, "reason": "ok"},
        "causal_chain": {"score": 3, "reason": "ok"},
        "balance": {"score": 4, "reason": "ok"},
        "thematic_coherence": {"score": 4, "reason": "ok"},
        "mechanical_sense": {"score": 2, "reason": "ok"},
        "completeness": {"score": 2, "reason": "ok"},
    }
    # 15+9+8+8+2+2 = 44 / 12 = 3.6667
    assert weighted_score_from_dict(scores) == 3.6667


def test_aggregate_variants(project_dir):
    judgment = make_judgment(ref=5, causal=4, bal=4, theme=4, mech=4, comp=4)
    data = [{"variant": "flat_alpha", "case": SAMPLE_CASE, "judgment": judgment}]

    path = project_dir / "results" / "judgments" / "test_1_0.json"
    path.write_text(json.dumps(data))

    result = aggregate_variants("test")
    assert result is not None
    assert "flat_alpha" in result["variants"]
    assert result["variants"]["flat_alpha"]["n"] == 1
    assert result["variants"]["flat_alpha"]["weighted_total"] > 0


def test_aggregate_variants_no_files(project_dir):
    assert aggregate_variants("nonexistent") is None


def test_compare_models(project_dir):
    j_a = make_judgment(ref=5, causal=5, bal=5, theme=5, mech=5, comp=5)
    j_b = make_judgment(ref=3, causal=3, bal=3, theme=3, mech=3, comp=3)

    data_a = [{"case": SAMPLE_CASE, "judgment": j_a}]
    data_b = [{"case": SAMPLE_CASE, "judgment": j_b}]

    (project_dir / "results" / "judgments" / "model_a_0.json").write_text(json.dumps(data_a))
    (project_dir / "results" / "judgments" / "model_b_0.json").write_text(json.dumps(data_b))

    result = compare_models("model_a", "model_b")
    assert result["shared_cases"] == 1
    assert result["model_a"]["mean"] == 5.0
    assert result["model_b"]["mean"] == 3.0
    assert result["a_wins"] == 1
    assert result["b_wins"] == 0
