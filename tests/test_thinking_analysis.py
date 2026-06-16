"""Tests for the cross-thinking-level analysis module."""

from __future__ import annotations

import json
from pathlib import Path

from src.analysis import thinking as thinking_mod

from .conftest import FAKE_NESTED_LEVEL, SAMPLE_CASE, make_judgment


def _write_pair(
    project_dir: Path,
    thinking: str,
    suffix: str,
    case: dict,
    judgment: dict,
    *,
    thinking_tokens: int = 0,
    latency_ms: int = 100,
    output_tokens: int = 200,
) -> None:
    """Write one raw + one judgment entry for an exec_id."""
    exec_id = f"{thinking}_{suffix}"
    raw_entry = {
        "variant": "flat_alpha" if suffix == "1" else "nested_narrative",
        "case": case,
        "output": FAKE_NESTED_LEVEL,
        "normalized": FAKE_NESTED_LEVEL,
        "stats": {
            "latency_ms": latency_ms,
            "thinking_level": thinking,
            "prompt_tokens": 50,
            "thinking_tokens": thinking_tokens,
            "output_tokens": output_tokens,
            "retries": 0,
            "model": "gemini-3.1-flash-lite",
        },
    }
    (project_dir / "results" / "raw" / f"{exec_id}_0.json").write_text(
        json.dumps([raw_entry])
    )
    judge_entry = {"case": case, "judgment": judgment}
    (project_dir / "results" / "judgments" / f"{exec_id}_0.json").write_text(
        json.dumps([judge_entry])
    )


def test_run_writes_all_outputs_and_lift(project_dir):
    # flat_alpha at minimal (4s) and at low (5s) — lift should be positive.
    low_judgment = make_judgment(ref=4, causal=4, bal=4, theme=4, mech=4, comp=4)
    high_judgment = make_judgment(ref=5, causal=5, bal=5, theme=5, mech=5, comp=5)
    _write_pair(project_dir, "minimal", "1", SAMPLE_CASE, low_judgment,
                thinking_tokens=0, latency_ms=1000)
    _write_pair(project_dir, "low", "1", SAMPLE_CASE, high_judgment,
                thinking_tokens=500, latency_ms=2000)

    report = thinking_mod.run(["minimal", "low"], ["flat_alpha"], baseline="minimal")

    cpq = report["cost_per_quality"]
    flat_minimal = cpq[(cpq["variant"] == "flat_alpha")
                       & (cpq["thinking_level"] == "minimal")].iloc[0]
    flat_low = cpq[(cpq["variant"] == "flat_alpha")
                   & (cpq["thinking_level"] == "low")].iloc[0]

    assert flat_minimal["lift_vs_baseline"] == 0.0
    assert flat_low["lift_vs_baseline"] == 1.0  # 5.0 - 4.0
    assert flat_low["mean_thinking_tokens"] == 500
    assert flat_low["mean_latency_ms"] == 2000

    lift = report["criterion_lift"]
    causal_low = lift[(lift["thinking_level"] == "low")
                      & (lift["criterion"] == "causal_chain")].iloc[0]
    assert causal_low["lift_vs_baseline"] == 1.0  # 5 - 4

    for key in ("summary", "deltas", "chart", "cost_per_quality", "criterion_lift"):
        assert Path(report["_paths"][key]).exists()


def test_failure_mode_report_buckets_correctly(project_dir):
    # flat_alpha @ minimal: low score (failing). flat_alpha @ low: high score (fixed).
    fail_judgment = make_judgment(ref=2, causal=2, bal=3, theme=3, mech=3, comp=3)
    fix_judgment = make_judgment(ref=5, causal=5, bal=5, theme=5, mech=5, comp=5)
    ref_judgment = make_judgment(ref=5, causal=5, bal=5, theme=5, mech=5, comp=5)

    _write_pair(project_dir, "minimal", "1", SAMPLE_CASE, fail_judgment)
    _write_pair(project_dir, "low", "1", SAMPLE_CASE, fix_judgment)
    _write_pair(project_dir, "minimal", "6", SAMPLE_CASE, ref_judgment)

    fm = thinking_mod.failure_mode_report(
        target_variant="flat_alpha",
        reference_variant="nested_narrative",
        new_levels=["low"],
        baseline="minimal",
        baseline_threshold=3.5,
        fixed_threshold=4.0,
    )

    counts = fm["counts"]["low"]
    assert counts["total_failing_at_baseline"] == 1
    assert counts["matched"] == 1
    assert counts["fixed"] == 1
    assert counts["improved"] == 0
    assert counts["still_broken"] == 0

    md_path = Path(fm["paths"]["low"])
    assert md_path.exists()
    content = md_path.read_text()
    assert "fixed" in content.lower()
    assert SAMPLE_CASE["genre"] in content  # case appears in markdown


def test_failure_mode_report_skips_baseline_passing_cases(project_dir):
    # flat_alpha @ minimal scores ABOVE the failure threshold — should not appear.
    pass_judgment = make_judgment(ref=5, causal=5, bal=5, theme=5, mech=5, comp=5)
    _write_pair(project_dir, "minimal", "1", SAMPLE_CASE, pass_judgment)
    _write_pair(project_dir, "low", "1", SAMPLE_CASE, pass_judgment)

    fm = thinking_mod.failure_mode_report(
        target_variant="flat_alpha",
        reference_variant="nested_narrative",
        new_levels=["low"],
        baseline="minimal",
        baseline_threshold=3.5,
        fixed_threshold=4.0,
    )

    counts = fm["counts"]["low"]
    assert counts["total_failing_at_baseline"] == 0
    assert counts["matched"] == 0
    assert counts["fixed"] == 0
