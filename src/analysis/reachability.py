"""Per-encounter weakness-reachability rates across conditions × variants.

For each encounter, asks whether the player's inventory at that point contains
anything that satisfies the enemy's named weakness. Aggregates the break rate
per (variant, condition) cell from `results/judgments/reachability_*.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..paths import analysis_dir, judgments_dir
from .load import VARIANT_MAP

CONDITIONS = ["minimal", "gamin", "low", "medium", "high"]

CONDITION_LABELS = {
    "minimal": "preview - minimal",
    "gamin":   "stable - minimal",
    "low":     "stable - low",
    "medium":  "stable - medium",
    "high":    "stable - high",
}

CONDITION_COLORS = {
    "minimal": "#c93838",
    "gamin":   "#b4c9e0",
    "low":     "#7fa2c4",
    "medium":  "#4a7ba9",
    "high":    "#1f4869",
}


def aggregate() -> pd.DataFrame:
    rows: list[dict] = []
    jdir = judgments_dir()
    for cond in CONDITIONS:
        for suffix, variant in VARIANT_MAP.items():
            files = sorted(jdir.glob(f"reachability_{cond}_{suffix}_*.json"))
            enc = breaks = 0
            for f in files:
                for level in json.loads(Path(f).read_text()):
                    for e in level["encounters"]:
                        enc += 1
                        if not e["satisfied"]:
                            breaks += 1
            if enc == 0:
                continue
            rows.append({
                "variant": variant,
                "condition": cond,
                "files": len(files),
                "encounters": enc,
                "breaks": breaks,
                "rate_pct": round(breaks / enc * 100, 1),
            })
    return pd.DataFrame(rows)


def to_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to variant × condition wide form. Rows sorted by preview-minimal rate desc."""
    wide = long_df.pivot_table(
        values="rate_pct", index="variant", columns="condition"
    )
    present_conds = [c for c in CONDITIONS if c in wide.columns]
    wide = wide[present_conds]
    sort_col = "minimal" if "minimal" in wide.columns else present_conds[0]
    wide = wide.sort_values(sort_col, ascending=False)
    return wide


def _make_chart(wide: pd.DataFrame, out_path: str) -> None:
    """Grouped bars: one group per variant, one bar per condition."""
    variants = list(wide.index)
    conditions = list(wide.columns)

    fig, ax = plt.subplots(figsize=(max(8, 1.6 * len(variants) + 3), 6))
    x = np.arange(len(variants))
    width = 0.8 / max(1, len(conditions))

    for i, cond in enumerate(conditions):
        offset = (i - (len(conditions) - 1) / 2) * width
        vals = wide[cond].values
        bars = ax.bar(
            x + offset, vals, width,
            label=CONDITION_LABELS.get(cond, cond),
            color=CONDITION_COLORS.get(cond, "#888888"),
            edgecolor="white", linewidth=0.5,
        )
        for bar, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, v + 0.15, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=7, color="#444444",
                )

    ax.set_xticks(x)
    ax.set_xticklabels(variants, fontsize=9, rotation=20, ha="right")
    ymax = max(10.0, float(np.nanmax(wide.values)) * 1.2)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Encounter break rate (%)  ↓ lower is better", fontsize=10)
    fig.suptitle(
        "Logical game break rate",
        fontsize=13, fontweight="bold", color="#333333", y=0.985,
    )
    ax.set_title(
        "Gemini 3.1 Flash Lite  ·  summer 2026\n"
        "preview release at minimal thinking; stable release at minimal → high",
        fontsize=9, color="#666666", style="italic", pad=10,
    )
    fig.text(
        0.5, 0.01,
        "Note: low thinking is inconsistent — flat_alpha and alpha_nested "
        "spike above their minimal baselines before medium / high resolve them.",
        ha="center", fontsize=8, color="#666666", style="italic",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color="#e0e0e0", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(title="Condition", fontsize=9)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.18)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run() -> dict:
    """Aggregate, write CSV + chart, return paths."""
    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    long_df = aggregate()
    if long_df.empty:
        raise FileNotFoundError(
            f"No reachability_*.json files found in {judgments_dir()}"
        )

    wide = to_wide(long_df)

    long_path = out / "05_reachability_long.csv"
    wide_path = out / "05_reachability.csv"
    chart_path = out / "05_reachability_chart.png"

    long_df.to_csv(long_path, index=False)
    wide.rename(columns=CONDITION_LABELS).to_csv(wide_path, float_format="%.1f")
    _make_chart(wide, str(chart_path))

    return {
        "long": long_df,
        "wide": wide,
        "_paths": {
            "long": str(long_path),
            "wide": str(wide_path),
            "chart": str(chart_path),
        },
    }
