"""01: Summary statistics per variant at minimum thinking.

For each variant, computes mean, standard deviation, standard error,
min, and max of the weighted score across 64 input cases.
"""

from __future__ import annotations

import math
from pathlib import Path

from .load import VARIANT_MAP, load_minimal

EXPECTED_N = 64
OUTPUT_DIR = Path("results/analysis")


def main() -> None:
    df = load_minimal()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for variant in VARIANT_MAP.values():
        subset = df[df["variant"] == variant]
        n = len(subset)
        if n != EXPECTED_N:
            raise ValueError(f"{variant}: expected {EXPECTED_N} cases, got {n}")

        scores = subset["weighted_score"]
        sd = float(scores.std())
        rows.append(
            {
                "variant": variant,
                "n": n,
                "mean": round(float(scores.mean()), 4),
                "sd": round(sd, 4),
                "se": round(sd / math.sqrt(n), 4),
                "min": round(float(scores.min()), 4),
                "max": round(float(scores.max()), 4),
            }
        )

    import pandas as pd

    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "01_summary_stats.csv", index=False)
    print(f"  wrote {OUTPUT_DIR / '01_summary_stats.csv'}")


if __name__ == "__main__":
    main()
