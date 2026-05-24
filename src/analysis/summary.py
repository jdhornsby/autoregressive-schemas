"""Summary statistics per variant at minimum thinking.

For each variant, computes mean, standard deviation, standard error,
min, and max of the weighted score across 64 input cases.
"""

from __future__ import annotations

import math

import pandas as pd

from ..paths import analysis_dir
from .load import VARIANT_MAP, load_minimal

EXPECTED_N = 64


def run() -> pd.DataFrame:
    """Compute and write summary stats. Returns the DataFrame."""
    df = load_minimal()
    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for variant in VARIANT_MAP.values():
        subset = df[df["variant"] == variant]
        n = len(subset)
        if n != EXPECTED_N:
            raise ValueError(f"{variant}: expected {EXPECTED_N} cases, got {n}")

        scores = subset["weighted_score"]
        std = float(scores.std())
        rows.append({
            "variant": variant,
            "n": n,
            "mean": round(float(scores.mean()), 4),
            "sd": round(std, 4),
            "se": round(std / math.sqrt(n), 4),
            "min": round(float(scores.min()), 4),
            "max": round(float(scores.max()), 4),
        })

    result = pd.DataFrame(rows)
    path = out / "01_summary_stats.csv"
    result.to_csv(path, index=False)
    return result
