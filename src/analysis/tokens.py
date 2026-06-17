"""Mean thinking-token usage across conditions × variants."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..paths import analysis_dir, raw_dir
from . import reachability
from .load import VARIANT_MAP
from .reachability import CONDITION_COLORS, CONDITION_LABELS, CONDITIONS


def aggregate() -> pd.DataFrame:
    rows: list[dict] = []
    rdir = raw_dir()
    for cond in CONDITIONS:
        for suffix, variant in VARIANT_MAP.items():
            files = sorted(rdir.glob(f"{cond}_{suffix}_*.json"))
            tokens: list[int] = []
            for f in files:
                for entry in json.loads(Path(f).read_text()):
                    tt = entry.get("stats", {}).get("thinking_tokens")
                    if tt is not None:
                        tokens.append(int(tt))
            if not tokens:
                continue
            rows.append({
                "variant": variant,
                "condition": cond,
                "files": len(files),
                "levels": len(tokens),
                "mean_thinking_tokens": round(sum(tokens) / len(tokens), 1),
            })
    return pd.DataFrame(rows)


def to_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to variant × condition wide form. Match the reachability chart's variant order."""
    wide = long_df.pivot_table(
        values="mean_thinking_tokens", index="variant", columns="condition"
    )
    present_conds = [c for c in CONDITIONS if c in wide.columns]
    wide = wide[present_conds]

    try:
        order = list(reachability.to_wide(reachability.aggregate()).index)
    except FileNotFoundError:
        return wide.sort_values(present_conds[-1], ascending=False)
    return wide.reindex([v for v in order if v in wide.index])


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
                    bar.get_x() + bar.get_width() / 2,
                    v + max(wide.values.max() * 0.015, 5),
                    f"{int(round(v))}",
                    ha="center", va="bottom", fontsize=7, color="#444444",
                )

    ax.set_xticks(x)
    ax.set_xticklabels(variants, fontsize=9, rotation=20, ha="right")
    ymax = max(50.0, float(np.nanmax(wide.values)) * 1.18)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Mean thinking tokens per level", fontsize=10)

    fig.suptitle(
        "Thinking token usage per generation",
        fontsize=13, fontweight="bold", color="#333333", y=0.985,
    )
    ax.set_title(
        "Gemini 3.1 Flash Lite  ·  summer 2026\n"
        "preview release at minimal thinking; GA release at minimal → high",
        fontsize=9, color="#666666", style="italic", pad=10,
    )
    fig.text(
        0.5, 0.01,
        "Note: minimal-thinking conditions (preview, stable) use ~0 thinking "
        "tokens by configuration, not by model behavior.",
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
        raise FileNotFoundError(f"No raw stats found in {raw_dir()}")

    wide = to_wide(long_df)

    long_path = out / "06_thinking_tokens_long.csv"
    wide_path = out / "06_thinking_tokens.csv"
    chart_path = out / "06_thinking_tokens_chart.png"

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
