"""Score aggregation for judgment files."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .paths import judgments_dir, scores_dir
from .rubric import WEIGHTS, case_id

TOTAL_WEIGHT = sum(WEIGHTS.values())


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def sd(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5


def weighted_score_from_dict(scores: dict) -> float:
    """Compute weighted score from a {criterion: {score: int, ...}} dict."""
    total = sum(scores[c]["score"] * WEIGHTS[c] for c in WEIGHTS)
    return round(total / TOTAL_WEIGHT, 4)


def _load_judgments(prefix: str) -> list[dict]:
    """Load all judgment files matching a prefix."""
    rows: list[dict] = []
    for f in sorted(judgments_dir().glob(f"{prefix}_*.json")):
        rows.extend(json.loads(f.read_text()))
    return rows


def _load_judgments_with_variant(exec_id: str, variant_map: dict[str, str]) -> list[dict]:
    """Load judgment files, inferring variant from the filename suffix."""
    rows: list[dict] = []
    for f in sorted(judgments_dir().glob(f"{exec_id}_*.json")):
        stem = Path(f).stem  # e.g. "minimal_1_0"
        # strip exec_id prefix to get "{variant_key}_{part}"
        suffix = stem[len(exec_id) + 1:]
        variant_key = suffix.rsplit("_", 1)[0]  # "1"
        variant_name = variant_map.get(variant_key, variant_key)

        for row in json.loads(f.read_text()):
            rows.append({"variant": variant_name, **row})
    return rows





VARIANT_MAP = {
    "1": "flat_alpha",
    "2": "grouped_by_type",
    "3": "append_order",
    "4": "ui_contract",
    "5": "alpha_nested",
    "6": "nested_narrative",
}


def aggregate_variants(exec_id: str) -> dict | None:
    """Aggregate judgment scores by variant. Returns the result dict or None."""
    rows = _load_judgments_with_variant(exec_id, VARIANT_MAP)
    if not rows:
        return None

    by_variant: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_variant[row["variant"]].append(row["judgment"])

    variants: dict[str, dict] = {}
    for name, judgments in by_variant.items():
        criteria: dict[str, float] = {}
        for c in WEIGHTS:
            vals = [j["scores"][c]["score"] for j in judgments]
            criteria[c] = round(mean(vals), 2)

        w = sum(criteria[c] * WEIGHTS[c] for c in WEIGHTS) / TOTAL_WEIGHT
        variants[name] = {
            "n": len(judgments),
            "criteria": criteria,
            "weighted_total": round(w, 2),
        }

    result = {
        "exec_id": exec_id,
        "n_judgments": len(rows),
        "variants": variants,
    }

    scores_dir().mkdir(parents=True, exist_ok=True)
    path = scores_dir() / f"{exec_id}_scores.json"
    path.write_text(json.dumps(result, indent=2))
    return result





def _load_model_scores(prefix: str) -> dict[str, list[float]]:
    """Load weighted scores per case for a model prefix."""
    by_case: dict[str, list[float]] = defaultdict(list)
    for row in _load_judgments(prefix):
        cid = case_id(row["case"])
        by_case[cid].append(weighted_score_from_dict(row["judgment"]["scores"]))
    return dict(by_case)


def _load_model_criteria(prefix: str) -> dict[str, list[dict[str, int]]]:
    """Load per-criterion scores per case for a model prefix."""
    by_case: dict[str, list[dict[str, int]]] = defaultdict(list)
    for row in _load_judgments(prefix):
        cid = case_id(row["case"])
        scores = {c: row["judgment"]["scores"][c]["score"] for c in WEIGHTS}
        by_case[cid].append(scores)
    return dict(by_case)


def compare_models(model_a: str, model_b: str) -> dict:
    """Run head-to-head model comparison. Writes CSVs and returns summary."""
    import csv

    a_scores = _load_model_scores(model_a)
    b_scores = _load_model_scores(model_b)
    a_criteria = _load_model_criteria(model_a)
    b_criteria = _load_model_criteria(model_b)

    if not a_scores:
        raise FileNotFoundError(f"No judgment files for {model_a}")
    if not b_scores:
        raise FileNotFoundError(f"No judgment files for {model_b}")

    shared = sorted(set(a_scores) & set(b_scores))
    tag = f"{model_a}_vs_{model_b}"
    out = scores_dir()
    out.mkdir(parents=True, exist_ok=True)

    # Summary stats
    all_a = [ws for cid in shared for ws in a_scores[cid]]
    all_b = [ws for cid in shared for ws in b_scores[cid]]

    with open(out / f"{tag}_summary_stats.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "n", "mean", "sd", "min", "max"])
        for name, vals in [(model_a, all_a), (model_b, all_b)]:
            w.writerow([name, len(vals), round(mean(vals), 4), round(sd(vals), 4),
                        round(min(vals), 4), round(max(vals), 4)])

    # Per-criterion
    criteria_rows: dict[str, dict] = {}
    with open(out / f"{tag}_criteria.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["criterion", "weight", f"{model_a}_mean", f"{model_b}_mean", "diff"])
        for c in WEIGHTS:
            a_vals = [s[c] for cid in shared for s in a_criteria[cid]]
            b_vals = [s[c] for cid in shared for s in b_criteria[cid]]
            a_m, b_m = round(mean(a_vals), 4), round(mean(b_vals), 4)
            w.writerow([c, WEIGHTS[c], a_m, b_m, round(a_m - b_m, 4)])
            criteria_rows[c] = {"a": a_m, "b": b_m, "diff": round(a_m - b_m, 4)}

    # Per-case
    a_wins = b_wins = ties = 0
    diffs: list[float] = []

    with open(out / f"{tag}_per_case.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", f"{model_a}_mean", f"{model_b}_mean", "diff"])
        for cid in shared:
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

    # Paired summary
    with open(out / f"{tag}_paired_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair", "mean_diff", f"{model_a}_wins", f"{model_b}_wins", "ties"])
        w.writerow([tag, round(mean(diffs), 4), a_wins, b_wins, ties])

    return {
        "shared_cases": len(shared),
        "model_a": {"name": model_a, "n": len(all_a), "mean": round(mean(all_a), 4)},
        "model_b": {"name": model_b, "n": len(all_b), "mean": round(mean(all_b), 4)},
        "mean_diff": round(mean(diffs), 4),
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "criteria": criteria_rows,
    }
