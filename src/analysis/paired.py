"""Paired comparisons between a reference variant and selected comparators.

For each pair, computes per-case score differences (reference minus
comparator) and summary statistics.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from ..paths import analysis_dir
from .load import load_thinking_level

DEFAULT_REFERENCE = "nested_narrative"
DEFAULT_COMPARATORS = ("flat_alpha", "ui_contract", "alpha_nested")


def run(
    thinking: str = "minimal",
    reference: str = DEFAULT_REFERENCE,
    comparators: Iterable[str] = DEFAULT_COMPARATORS,
) -> list[dict]:
    """Compute and write paired comparisons. Returns list of summary dicts."""
    comparators = list(comparators)
    wanted_variants = [reference, *comparators]
    df = load_thinking_level(thinking, wanted_variants, strict=False)
    if df.empty:
        raise FileNotFoundError(
            f"No data for thinking={thinking!r} variants={wanted_variants}"
        )

    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    pivot = df.pivot_table(values="weighted_score", index="case_id", columns="variant")
    if reference not in pivot.columns:
        raise ValueError(f"Reference variant {reference!r} not present at thinking={thinking}")

    summaries: list[dict] = []

    for comparator in comparators:
        if comparator not in pivot.columns:
            continue
        diffs = pivot[reference] - pivot[comparator]
        pair_name = f"{reference}_vs_{comparator}"
        tag = f"{thinking}_{pair_name}"

        per_case = pd.DataFrame({"case_id": diffs.index, "difference": diffs.values})
        per_case.to_csv(
            out / f"02_paired_{tag}_per_case.csv", index=False, float_format="%.4f"
        )

        summary = {
            "pair": pair_name,
            "thinking_level": thinking,
            "mean_diff": round(float(diffs.mean()), 4),
            "reference_wins": int((diffs > 0).sum()),
            "comparator_wins": int((diffs < 0).sum()),
            "ties": int((diffs == 0).sum()),
        }
        pd.DataFrame([summary]).to_csv(
            out / f"02_paired_{tag}_summary.csv", index=False
        )
        summaries.append(summary)

    return summaries
