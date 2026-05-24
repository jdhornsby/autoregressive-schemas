"""Stacked bar chart of weighted criterion contributions by variant."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as ticker  # noqa: E402

from ..paths import analysis_dir, judgments_dir
from ..rubric import WEIGHTS

CRITERIA = list(WEIGHTS.keys())
TOTAL_WEIGHT = sum(WEIGHTS.values())
EXPECTED_N = 64

VARIANT_MAP = {
    "1": "flat_alpha",
    "2": "grouped_by_type",
    "3": "append_order",
    "4": "ui_contract",
    "5": "alpha_nested",
    "6": "nested_narrative",
}

CRITERION_LABELS = {
    "reference_integrity": "Reference Integrity (\u00d73)",
    "causal_chain": "Causal Chain (\u00d73)",
    "balance": "Balance (\u00d72)",
    "thematic_coherence": "Thematic Coherence (\u00d72)",
    "mechanical_sense": "Mechanical Sense (\u00d71)",
    "completeness": "Completeness (\u00d71)",
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


def load_scores() -> dict[str, list[dict[str, int]]]:
    """Load per-case criterion scores grouped by variant."""
    scores: dict[str, list[dict[str, int]]] = defaultdict(list)

    for f in sorted(judgments_dir().glob("minimal_*.json")):
        parts = Path(f).stem.split("_")
        variant = VARIANT_MAP[parts[1]]

        with open(f) as fh:
            records = json.load(fh)

        for rec in records:
            criterion_scores = {c: rec["judgment"]["scores"][c]["score"] for c in CRITERIA}
            scores[variant].append(criterion_scores)

    for variant, case_scores in scores.items():
        if len(case_scores) != EXPECTED_N:
            raise ValueError(f"{variant}: expected {EXPECTED_N} cases, got {len(case_scores)}")

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


def make_chart(contributions: dict[str, dict[str, float]], out_path: str) -> None:
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
    ax.set_ylabel("Weighted Score (1\u20135 scale)", fontsize=10)
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

    ax.set_title(
        "Weighted Score by Schema Variant",
        fontsize=12, fontweight="bold", pad=12, color="#333333",
    )

    fig.tight_layout()
    fig.subplots_adjust(right=0.78)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run() -> str:
    """Generate the chart. Returns the output path."""
    scores = load_scores()
    contributions = compute_contributions(scores)
    out_path = str(analysis_dir() / "stacked_bar_scores.png")
    make_chart(contributions, out_path)
    return out_path
