"""Head-to-head scoring for model comparisons.

Aggregates judgment files by model, computes weighted scores per case,
and produces paired comparison outputs (summary stats, per-case diffs,
win/loss/tie counts).

Usage:
    uv run python -m src.score_models <model_a_prefix> <model_b_prefix>

Example:
    uv run python -m src.score_models flash_v1_gemini_35_flash flash_v1_gemini_3_flash_preview
"""

from __future__ import annotations

import argparse
import csv
import json
import glob
from collections import defaultdict
from pathlib import Path

from .rubric import WEIGHTS

JUDGMENTS_DIR = Path("results/judgments")
ANALYSIS_DIR = Path("results/analysis")
TOTAL_WEIGHT = sum(WEIGHTS.values())


def case_id(case: dict) -> str:
    return f"{case['genre']}_{case['mood']}_{case['player_class']}_{case['target_difficulty']}"


def weighted_score(scores: dict) -> float:
    total = sum(scores[c]["score"] * WEIGHTS[c] for c in WEIGHTS)
    return round(total / TOTAL_WEIGHT, 4)


def load_model(prefix: str) -> dict[str, list[float]]:
    """Load all judgments for a model prefix, return {case_id: [weighted_scores]}."""
    by_case: dict[str, list[float]] = defaultdict(list)
    files = sorted(glob.glob(str(JUDGMENTS_DIR / f"{prefix}_*.json")))
    if not files:
        raise FileNotFoundError(f"No judgment files matching {prefix}_*.json")
    for f in files:
        for row in json.loads(Path(f).read_text()):
            cid = case_id(row["case"])
            ws = weighted_score(row["judgment"]["scores"])
            by_case[cid].append(ws)
    return dict(by_case)


def load_model_criteria(prefix: str) -> dict[str, list[dict[str, int]]]:
    """Load all judgments for a model prefix, return {case_id: [criterion_scores_dict]}."""
    by_case: dict[str, list[dict[str, int]]] = defaultdict(list)
    files = sorted(glob.glob(str(JUDGMENTS_DIR / f"{prefix}_*.json")))
    for f in files:
        for row in json.loads(Path(f).read_text()):
            cid = case_id(row["case"])
            scores = {c: row["judgment"]["scores"][c]["score"] for c in WEIGHTS}
            by_case[cid].append(scores)
    return dict(by_case)


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def sd(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5


def main() -> None:
    parser = argparse.ArgumentParser(description="Head-to-head model scoring.")
    parser.add_argument("model_a", help="Prefix for model A judgment files")
    parser.add_argument("model_b", help="Prefix for model B judgment files")
    args = parser.parse_args()

    a_scores = load_model(args.model_a)
    b_scores = load_model(args.model_b)
    a_criteria = load_model_criteria(args.model_a)
    b_criteria = load_model_criteria(args.model_b)

    shared_cases = sorted(set(a_scores) & set(b_scores))
    print(f"Shared cases: {len(shared_cases)}")

    # --- 01: Summary stats per model ---
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{args.model_a}_vs_{args.model_b}"

    all_a = [ws for cid in shared_cases for ws in a_scores[cid]]
    all_b = [ws for cid in shared_cases for ws in b_scores[cid]]

    summary_path = ANALYSIS_DIR / f"{tag}_summary_stats.csv"
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "n", "mean", "sd", "min", "max"])
        for name, vals in [(args.model_a, all_a), (args.model_b, all_b)]:
            w.writerow([
                name, len(vals),
                round(mean(vals), 4), round(sd(vals), 4),
                round(min(vals), 4), round(max(vals), 4),
            ])
    print(f"Written: {summary_path}")

    # --- 02: Per-criterion summary ---
    criteria_path = ANALYSIS_DIR / f"{tag}_criteria.csv"
    with open(criteria_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["criterion", "weight", f"{args.model_a}_mean", f"{args.model_b}_mean", "diff"])
        for c in WEIGHTS:
            a_vals = [s[c] for cid in shared_cases for s in a_criteria[cid]]
            b_vals = [s[c] for cid in shared_cases for s in b_criteria[cid]]
            a_m, b_m = round(mean(a_vals), 4), round(mean(b_vals), 4)
            w.writerow([c, WEIGHTS[c], a_m, b_m, round(a_m - b_m, 4)])
    print(f"Written: {criteria_path}")

    # --- 03: Paired per-case comparison ---
    per_case_path = ANALYSIS_DIR / f"{tag}_per_case.csv"
    a_wins = b_wins = ties = 0
    diffs = []

    with open(per_case_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", f"{args.model_a}_mean", f"{args.model_b}_mean", "diff"])
        for cid in shared_cases:
            a_m = round(mean(a_scores[cid]), 4)
            b_m = round(mean(b_scores[cid]), 4)
            diff = round(a_m - b_m, 4)
            diffs.append(diff)
            w.writerow([cid, a_m, b_m, diff])
            if diff > 0:
                a_wins += 1
            elif diff < 0:
                b_wins += 1
            else:
                ties += 1
    print(f"Written: {per_case_path}")

    # --- 04: Paired summary ---
    paired_path = ANALYSIS_DIR / f"{tag}_paired_summary.csv"
    with open(paired_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair", "mean_diff", f"{args.model_a}_wins", f"{args.model_b}_wins", "ties"])
        w.writerow([tag, round(mean(diffs), 4), a_wins, b_wins, ties])
    print(f"Written: {paired_path}")

    # --- Print summary ---
    print(f"\n{'─' * 50}")
    print(f"{args.model_a}: mean={mean(all_a):.3f}  n={len(all_a)}")
    print(f"{args.model_b}: mean={mean(all_b):.3f}  n={len(all_b)}")
    print(f"Mean diff (A-B): {mean(diffs):.3f}")
    print(f"Wins: {args.model_a}={a_wins}  {args.model_b}={b_wins}  ties={ties}")


if __name__ == "__main__":
    main()
