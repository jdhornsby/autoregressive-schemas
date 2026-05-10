"""02: Paired comparisons between nested_narrative and selected variants.

For each pair, computes per-case score differences (nested_narrative minus
comparator) and summary statistics. Minimum thinking only.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .load import load_minimal

REFERENCE = "nested_narrative"
COMPARATORS = ["flat_alpha", "ui_contract", "alpha_nested"]
OUTPUT_DIR = Path("results/analysis")


def main() -> None:
    df = load_minimal()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pivot = df.pivot_table(values="weighted_score", index="case_id", columns="variant")

    for comparator in COMPARATORS:
        diffs = pivot[REFERENCE] - pivot[comparator]
        pair_name = f"{REFERENCE}_vs_{comparator}"

        # Per-case differences
        per_case = pd.DataFrame({"case_id": diffs.index, "difference": diffs.values})
        per_case.to_csv(
            OUTPUT_DIR / f"02_paired_{pair_name}_per_case.csv",
            index=False,
            float_format="%.4f",
        )

        # Summary
        summary = pd.DataFrame(
            [
                {
                    "pair": pair_name,
                    "mean_diff": round(float(diffs.mean()), 4),
                    "narrative_wins": int((diffs > 0).sum()),
                    "comparator_wins": int((diffs < 0).sum()),
                    "ties": int((diffs == 0).sum()),
                }
            ]
        )
        summary.to_csv(
            OUTPUT_DIR / f"02_paired_{pair_name}_summary.csv",
            index=False,
        )

        print(
            f"  wrote {pair_name}: mean_diff={float(diffs.mean()):.4f}, "
            f"wins={int((diffs > 0).sum())}/{int((diffs < 0).sum())}/{int((diffs == 0).sum())}"
        )


if __name__ == "__main__":
    main()
