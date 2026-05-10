"""Generate stacked bar chart of weighted criterion contributions by variant."""
from __future__ import annotations

import json
import glob
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# --- Constants ---
VARIANT_MAP = {
    "1": "flat_alpha",
    "2": "grouped_by_type",
    "3": "append_order",
    "4": "ui_contract",
    "5": "alpha_nested",
    "6": "nested_narrative",
}

CRITERIA = [
    "reference_integrity",
    "causal_chain",
    "balance",
    "thematic_coherence",
    "mechanical_sense",
    "completeness",
]

WEIGHTS = {
    "reference_integrity": 3,
    "causal_chain": 3,
    "balance": 2,
    "thematic_coherence": 2,
    "mechanical_sense": 1,
    "completeness": 1,
}

TOTAL_WEIGHT = sum(WEIGHTS.values())  # 12

EXPECTED_N = 64

# Stack order: heaviest weight at bottom
STACK_ORDER = [
    "reference_integrity",   # weight 3
    "causal_chain",          # weight 3
    "balance",               # weight 2
    "thematic_coherence",    # weight 2
    "mechanical_sense",      # weight 1
    "completeness",          # weight 1
]

# --- Pretty labels ---
CRITERION_LABELS = {
    "reference_integrity": "Reference Integrity (×3)",
    "causal_chain": "Causal Chain (×3)",
    "balance": "Balance (×2)",
    "thematic_coherence": "Thematic Coherence (×2)",
    "mechanical_sense": "Mechanical Sense (×1)",
    "completeness": "Completeness (×1)",
}

VARIANT_LABELS = {
    "flat_alpha": "flat_alpha",
    "grouped_by_type": "grouped_by_type",
    "append_order": "append_order",
    "ui_contract": "ui_contract",
    "alpha_nested": "alpha_nested",
    "nested_narrative": "nested_narrative",
}

# --- Colors: muted palette ---
COLORS = {
    "reference_integrity": "#2d5a87",
    "causal_chain": "#4a90c4",
    "balance": "#6aaa5e",
    "thematic_coherence": "#8cc47e",
    "mechanical_sense": "#d4a055",
    "completeness": "#e8c88a",
}


def load_scores() -> dict[str, list[dict[str, int]]]:
    """Load per-case criterion scores grouped by variant.

    Returns dict mapping variant name to list of 64 score dicts.
    """
    scores: dict[str, list[dict[str, int]]] = defaultdict(list)

    for f in sorted(glob.glob("results/judgments/minimal_*.json")):
        fname = Path(f).stem  # e.g. minimal_1_0
        parts = fname.split("_")
        v_num = parts[1]
        variant = VARIANT_MAP[v_num]

        with open(f) as fh:
            records = json.load(fh)

        for rec in records:
            criterion_scores = {
                c: rec["judgment"]["scores"][c]["score"] for c in CRITERIA
            }
            scores[variant].append(criterion_scores)

    # Validate counts
    for variant, case_scores in scores.items():
        if len(case_scores) != EXPECTED_N:
            raise ValueError(
                f"{variant}: expected {EXPECTED_N} cases, got {len(case_scores)}"
            )

    return dict(scores)


def compute_weighted_contributions(
    scores: dict[str, list[dict[str, int]]],
) -> dict[str, dict[str, float]]:
    """Compute mean weighted contribution per criterion per variant.

    Each contribution = mean(criterion_score) * weight / total_weight.
    Contributions sum to the variant's overall weighted mean.
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
    # Sort variants by total mean, highest on the left
    variant_totals = {
        v: sum(contributions[v].values()) for v in contributions
    }
    sorted_variants = sorted(variant_totals, key=lambda v: variant_totals[v], reverse=True)

    fig, ax = plt.subplots(figsize=(11, 6))

    x = range(len(sorted_variants))
    bottoms = [0.0] * len(sorted_variants)

    for criterion in STACK_ORDER:
        values = [contributions[v][criterion] for v in sorted_variants]
        bars = ax.bar(
            x,
            values,
            bottom=bottoms,
            label=CRITERION_LABELS[criterion],
            color=COLORS[criterion],
            edgecolor="white",
            linewidth=0.5,
            width=0.6,
        )
        bottoms = [b + v for b, v in zip(bottoms, values)]

    # Add total labels on top of each bar
    for i, v in enumerate(sorted_variants):
        total = variant_totals[v]
        ax.text(i, total + 0.02, f"{total:.2f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#333333")

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [VARIANT_LABELS[v] for v in sorted_variants],
        fontsize=9,
        rotation=20,
        ha="right",
    )
    ax.set_ylabel("Weighted Score (1–5 scale)", fontsize=10)
    ax.set_ylim(0, 5.0)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.25))

    # Clean up spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(colors="#666666", labelsize=9)
    ax.yaxis.grid(True, which="major", color="#e0e0e0", linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend - placed outside plot area to avoid clipping bar labels
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles[::-1], labels[::-1],  # reverse so heaviest weight is at top of legend
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        fontsize=8,
        frameon=True,
        framealpha=0.9,
        edgecolor="#cccccc",
    )

    ax.set_title(
        "Weighted Score by Schema Variant",
        fontsize=12,
        fontweight="bold",
        pad=12,
        color="#333333",
    )

    fig.tight_layout()
    fig.subplots_adjust(right=0.78)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Chart saved to {out_path}")


def main() -> None:
    scores = load_scores()
    contributions = compute_weighted_contributions(scores)

    # Sanity check: print totals
    print("Variant totals (should be ~3.84–4.32):")
    for v in sorted(contributions, key=lambda v: sum(contributions[v].values()), reverse=True):
        total = sum(contributions[v].values())
        breakdown = "  ".join(f"{c[:4]}={contributions[v][c]:.3f}" for c in STACK_ORDER)
        print(f"  {v:20s}  {total:.4f}   {breakdown}")

    out_path = "results/analysis/stacked_bar_scores.png"
    make_chart(contributions, out_path)


if __name__ == "__main__":
    main()
