"""Paired comparisons between nested_narrative and selected variants.

For each pair, computes per-case score differences (nested_narrative minus
comparator) and summary statistics. Minimum thinking only.
"""

from __future__ import annotations

import pandas as pd

from ..paths import analysis_dir
from .load import load_minimal

REFERENCE = "nested_narrative"
COMPARATORS = ["flat_alpha", "ui_contract", "alpha_nested"]


def run() -> list[dict]:
    """Compute and write paired comparisons. Returns list of summary dicts."""
    df = load_minimal()
    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    pivot = df.pivot_table(values="weighted_score", index="case_id", columns="variant")
    summaries: list[dict] = []

    for comparator in COMPARATORS:
        diffs = pivot[REFERENCE] - pivot[comparator]
        pair_name = f"{REFERENCE}_vs_{comparator}"

        per_case = pd.DataFrame({"case_id": diffs.index, "difference": diffs.values})
        per_case.to_csv(
            out / f"02_paired_{pair_name}_per_case.csv", index=False, float_format="%.4f"
        )

        summary = {
            "pair": pair_name,
            "mean_diff": round(float(diffs.mean()), 4),
            "narrative_wins": int((diffs > 0).sum()),
            "comparator_wins": int((diffs < 0).sum()),
            "ties": int((diffs == 0).sum()),
        }
        pd.DataFrame([summary]).to_csv(
            out / f"02_paired_{pair_name}_summary.csv", index=False
        )
        summaries.append(summary)

    return summaries
