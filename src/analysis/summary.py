"""Summary statistics per variant at a given thinking level.

For each variant, computes mean, standard deviation, standard error,
min, and max of the weighted score across the loaded cases.
"""

from __future__ import annotations

import math
from typing import Iterable

import pandas as pd

from ..paths import analysis_dir
from .load import VARIANT_MAP, load_thinking_level


def run(
    thinking: str = "minimal",
    variants: Iterable[str] | None = None,
    *,
    expected_n: int | None = 64,
) -> pd.DataFrame:
    """Compute and write summary stats. Returns the DataFrame.

    Args:
        thinking: thinking level to summarize.
        variants: variant names to include; None loads all six.
        expected_n: if set, raise when any variant has a different number of cases.
            Pass None when running on a partial-case subset.
    """
    df = load_thinking_level(thinking, variants, strict=False)
    if df.empty:
        raise FileNotFoundError(
            f"No data loaded for thinking={thinking!r} variants={variants}"
        )

    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    canonical = list(VARIANT_MAP.values())
    present = [v for v in canonical if v in set(df["variant"].unique())]

    rows: list[dict] = []
    for variant in present:
        subset = df[df["variant"] == variant]
        n = len(subset)
        if expected_n is not None and n != expected_n:
            raise ValueError(f"{variant}: expected {expected_n} cases, got {n}")

        scores = subset["weighted_score"]
        std = float(scores.std()) if n > 1 else 0.0
        rows.append({
            "variant": variant,
            "n": n,
            "mean": round(float(scores.mean()), 4),
            "sd": round(std, 4),
            "se": round(std / math.sqrt(n), 4) if n > 0 else 0.0,
            "min": round(float(scores.min()), 4),
            "max": round(float(scores.max()), 4),
        })

    result = pd.DataFrame(rows)
    path = out / f"01_summary_stats_{thinking}.csv"
    result.to_csv(path, index=False)
    return result
