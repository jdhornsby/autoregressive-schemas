"""Compute weighted aggregate scores from judgments.

Usage:
    uv run python -m src.score my_run
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .rubric import WEIGHTS

JUDGMENTS_DIR = Path("results/judgments")
SCORES_DIR = Path("results/scores")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate judgment scores.")
    parser.add_argument("exec_id", help="Execution identifier")
    args = parser.parse_args()

    rows: list[dict] = []
    for f in sorted(JUDGMENTS_DIR.glob(f"{args.exec_id}_*.json")):
        rows.extend(json.loads(f.read_text()))

    if not rows:
        print(f"No judgment files found for {args.exec_id!r} in {JUDGMENTS_DIR}")
        return

    by_variant: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_variant[row["variant"]].append(row["judgment"])

    variants: dict[str, dict] = {}
    for name, judgments in by_variant.items():
        criteria: dict[str, float] = {}
        for c in WEIGHTS:
            vals = [j["scores"][c]["score"] for j in judgments]
            criteria[c] = round(sum(vals) / len(vals), 2)

        w = sum(criteria[c] * WEIGHTS[c] for c in WEIGHTS) / sum(WEIGHTS.values())
        variants[name] = {
            "n": len(judgments),
            "criteria": criteria,
            "weighted_total": round(w, 2),
        }

    out = {
        "exec_id": args.exec_id,
        "n_judgments": len(rows),
        "variants": variants,
    }

    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    path = SCORES_DIR / f"{args.exec_id}_scores.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"Scores written to {path}")


if __name__ == "__main__":
    main()
