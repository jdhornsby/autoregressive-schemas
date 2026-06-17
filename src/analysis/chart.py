"""Stacked bar chart of weighted criterion contributions by variant."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as ticker  # noqa: E402

from ..paths import analysis_dir, judgments_dir
from ..rubric import WEIGHTS
from .load import VARIANT_MAP

CRITERIA = list(WEIGHTS.keys())
TOTAL_WEIGHT = sum(WEIGHTS.values())

CRITERION_LABELS = {
    "reference_integrity": "Reference Integrity (×3)",
    "causal_chain": "Causal Chain (×3)",
    "balance": "Balance (×2)",
    "thematic_coherence": "Thematic Coherence (×2)",
    "mechanical_sense": "Mechanical Sense (×1)",
    "completeness": "Completeness (×1)",
}

COLORS = {
    "reference_integrity": "#2d5a87",
    "causal_chain": "#4a90c4",
    "balance": "#6aaa5e",
    "thematic_coherence": "#8cc47e",
    "mechanical_sense": "#d4a055",
    "completeness": "#e8c88a",
}

# Stack order: heaviest weight at bottom
STACK_ORDER = list(WEIGHTS.keys())


def load_scores(
    thinking: str = "minimal",
    variants: Iterable[str] | None = None,
    *,
    expected_n: int | None = 64,
) -> dict[str, list[dict[str, int]]]:
    """Load per-case criterion scores grouped by variant."""
    wanted = set(variants) if variants is not None else set(VARIANT_MAP.values())
    scores: dict[str, list[dict[str, int]]] = defaultdict(list)

    for f in sorted(judgments_dir().glob(f"{thinking}_*.json")):
        parts = Path(f).stem.split("_")
        suffix = parts[1]
        if suffix not in VARIANT_MAP:
            continue
        variant = VARIANT_MAP[suffix]
        if variant not in wanted:
            continue

        with open(f) as fh:
            records = json.load(fh)

        for rec in records:
            criterion_scores = {c: rec["judgment"]["scores"][c]["score"] for c in CRITERIA}
            scores[variant].append(criterion_scores)

    if expected_n is not None:
        for variant, case_scores in scores.items():
            if len(case_scores) != expected_n:
                raise ValueError(
                    f"{variant}: expected {expected_n} cases, got {len(case_scores)}"
                )

    missing = wanted - set(scores)
    if missing and variants is not None:
        raise FileNotFoundError(
            f"No judgments at thinking={thinking!r} for variants: {sorted(missing)}"
        )

    return dict(scores)


def compute_contributions(
    scores: dict[str, list[dict[str, int]]],
) -> dict[str, dict[str, float]]:
    """Compute mean weighted contribution per criterion per variant.

    Each contribution = mean(criterion_score) * weight / total_weight.
    """
    contributions: dict[str, dict[str, float]] = {}
    for variant, case_scores in scores.items():
        contrib: dict[str, float] = {}
        for c in CRITERIA:
            vals = [cs[c] for cs in case_scores]
            mean_score = sum(vals) / len(vals)
            contrib[c] = mean_score * WEIGHTS[c] / TOTAL_WEIGHT
        contributions[variant] = contrib
    return contributions


def make_chart(
    contributions: dict[str, dict[str, float]],
    out_path: str,
    *,
    title: str = "Weighted Score by Schema Variant",
) -> None:
    """Render stacked bar chart and save to out_path."""
    variant_totals = {v: sum(contributions[v].values()) for v in contributions}
    sorted_variants = sorted(variant_totals, key=lambda v: variant_totals[v], reverse=True)

    fig, ax = plt.subplots(figsize=(11, 6))
    x = range(len(sorted_variants))
    bottoms = [0.0] * len(sorted_variants)

    for criterion in STACK_ORDER:
        values = [contributions[v][criterion] for v in sorted_variants]
        ax.bar(
            x, values, bottom=bottoms,
            label=CRITERION_LABELS[criterion], color=COLORS[criterion],
            edgecolor="white", linewidth=0.5, width=0.6,
        )
        bottoms = [b + v for b, v in zip(bottoms, values)]

    for i, v in enumerate(sorted_variants):
        total = variant_totals[v]
        ax.text(i, total + 0.02, f"{total:.2f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#333333")

    ax.set_xticks(list(x))
    ax.set_xticklabels(sorted_variants, fontsize=9, rotation=20, ha="right")
    ax.set_ylabel("Weighted Score (1–5 scale)", fontsize=10)
    ax.set_ylim(0, 5.0)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.25))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(colors="#666666", labelsize=9)
    ax.yaxis.grid(True, which="major", color="#e0e0e0", linewidth=0.5)
    ax.set_axisbelow(True)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles[::-1], labels[::-1],
        loc="upper left", bbox_to_anchor=(1.01, 1.0),
        fontsize=8, frameon=True, framealpha=0.9, edgecolor="#cccccc",
    )

    ax.set_title(title, fontsize=12, fontweight="bold", pad=12, color="#333333")

    fig.tight_layout()
    fig.subplots_adjust(right=0.78)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run(
    thinking: str = "minimal",
    variants: Iterable[str] | None = None,
    *,
    expected_n: int | None = 64,
) -> str:
    """Generate the chart. Returns the output path."""
    scores = load_scores(thinking, variants, expected_n=expected_n)
    contributions = compute_contributions(scores)
    out_path = str(analysis_dir() / f"stacked_bar_scores_{thinking}.png")
    title = f"Weighted Score by Schema Variant ({thinking} thinking)"
    make_chart(contributions, out_path, title=title)
    return out_path
