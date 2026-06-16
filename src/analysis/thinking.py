"""Cross-thinking-level comparison for one or more variants.

For each (variant, thinking_level), reports mean weighted score, per-criterion
means, token usage, and latency. Within each variant, computes the per-case
delta from the baseline thinking level — does thinking compensate for poor
schema order?
"""

from __future__ import annotations

import csv
import json
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..paths import analysis_dir, judgments_dir, raw_dir
from ..rubric import WEIGHTS, case_id
from .load import VARIANT_MAP, VARIANT_SUFFIX, load_thinking_level

CRITERIA = list(WEIGHTS.keys())

THINKING_COLORS = {
    "minimal": "#2d5a87",
    "low": "#4a90c4",
    "medium": "#d4a055",
    "high": "#a83232",
}


def _load_all(
    levels: list[str], variants: list[str]
) -> pd.DataFrame:
    frames = []
    for level in levels:
        df = load_thinking_level(level, variants, strict=False)
        if not df.empty:
            frames.append(df)
    if not frames:
        raise FileNotFoundError(
            f"No data for thinking levels {levels} variants {variants}"
        )
    return pd.concat(frames, ignore_index=True)


def _summary_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (variant, level), grp in df.groupby(["variant", "thinking_level"]):
        row = {
            "variant": variant,
            "thinking_level": level,
            "n": len(grp),
            "weighted_mean": round(float(grp["weighted_score"].mean()), 4),
            "weighted_sd": round(float(grp["weighted_score"].std()), 4) if len(grp) > 1 else 0.0,
            "mean_latency_ms": round(float(grp["latency_ms"].mean())),
            "mean_thinking_tokens": round(float(grp["thinking_tokens"].mean())),
            "mean_output_tokens": round(float(grp["output_tokens"].mean())),
        }
        for c in CRITERIA:
            row[f"{c}_mean"] = round(float(grp[c].mean()), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def _paired_deltas(
    df: pd.DataFrame, baseline: str, levels: list[str], variants: list[str]
) -> list[dict]:
    """For each non-baseline level, compute per-case (level - baseline) delta per variant."""
    out_dir = analysis_dir()
    summaries: list[dict] = []

    for variant in variants:
        v_df = df[df["variant"] == variant]
        if v_df.empty:
            continue
        pivot = v_df.pivot_table(
            values="weighted_score", index="case_id", columns="thinking_level"
        )
        if baseline not in pivot.columns:
            continue

        for level in levels:
            if level == baseline or level not in pivot.columns:
                continue
            diffs = (pivot[level] - pivot[baseline]).dropna()
            if diffs.empty:
                continue

            tag = f"{variant}_{level}_vs_{baseline}"
            per_case = pd.DataFrame({"case_id": diffs.index, "difference": diffs.values})
            per_case.to_csv(
                out_dir / f"04_thinking_{tag}_per_case.csv",
                index=False, float_format="%.4f",
            )

            summaries.append({
                "variant": variant,
                "comparison": f"{level} - {baseline}",
                "n": int(len(diffs)),
                "mean_diff": round(float(diffs.mean()), 4),
                "median_diff": round(float(diffs.median()), 4),
                "level_wins": int((diffs > 0).sum()),
                "baseline_wins": int((diffs < 0).sum()),
                "ties": int((diffs == 0).sum()),
            })

    return summaries


def _make_chart(summary: pd.DataFrame, levels: list[str], out_path: str) -> None:
    """Grouped bar chart: one group per variant, one bar per thinking level."""
    canonical = [v for v in VARIANT_MAP.values() if v in set(summary["variant"])]
    if not canonical:
        return

    pivot = summary.pivot_table(
        values="weighted_mean", index="variant", columns="thinking_level"
    ).reindex(canonical)
    present_levels = [lvl for lvl in levels if lvl in pivot.columns]

    fig, ax = plt.subplots(figsize=(max(8, 1.6 * len(canonical) + 3), 6))
    x = np.arange(len(canonical))
    width = 0.8 / max(1, len(present_levels))

    for i, level in enumerate(present_levels):
        offset = (i - (len(present_levels) - 1) / 2) * width
        vals = pivot[level].values
        bars = ax.bar(
            x + offset, vals, width,
            label=f"{level}",
            color=THINKING_COLORS.get(level, "#888888"),
            edgecolor="white", linewidth=0.5,
        )
        for bar, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, v + 0.03, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=7, color="#444444",
                )

    ax.set_xticks(x)
    ax.set_xticklabels(canonical, fontsize=9, rotation=20, ha="right")
    ax.set_ylim(0, 5.0)
    ax.set_ylabel("Weighted Score (1–5 scale)", fontsize=10)
    ax.set_title(
        "Effect of Thinking Level on Schema Variant Quality",
        fontsize=12, fontweight="bold", pad=12,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color="#e0e0e0", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(title="Thinking level", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _cost_per_quality(summary: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """One row per (variant, level): weighted_mean, costs, lift vs baseline."""
    rows: list[dict] = []
    baseline_lookup: dict[str, float] = {}
    for _, r in summary[summary["thinking_level"] == baseline].iterrows():
        baseline_lookup[r["variant"]] = float(r["weighted_mean"])

    for _, r in summary.iterrows():
        variant = r["variant"]
        baseline_mean = baseline_lookup.get(variant)
        lift = (
            round(float(r["weighted_mean"]) - baseline_mean, 4)
            if baseline_mean is not None
            else None
        )
        rows.append({
            "variant": variant,
            "thinking_level": r["thinking_level"],
            "n": int(r["n"]),
            "weighted_mean": float(r["weighted_mean"]),
            "lift_vs_baseline": lift,
            "mean_thinking_tokens": int(r["mean_thinking_tokens"]),
            "mean_output_tokens": int(r["mean_output_tokens"]),
            "mean_latency_ms": int(r["mean_latency_ms"]),
        })
    return pd.DataFrame(rows)


def _criterion_lift(summary: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """One row per (variant, level, criterion) with delta vs same-variant baseline."""
    baseline_means: dict[tuple[str, str], float] = {}
    base_rows = summary[summary["thinking_level"] == baseline]
    for _, r in base_rows.iterrows():
        for c in CRITERIA:
            baseline_means[(r["variant"], c)] = float(r[f"{c}_mean"])

    rows: list[dict] = []
    for _, r in summary.iterrows():
        for c in CRITERIA:
            base = baseline_means.get((r["variant"], c))
            mean = float(r[f"{c}_mean"])
            rows.append({
                "variant": r["variant"],
                "thinking_level": r["thinking_level"],
                "criterion": c,
                "weight": WEIGHTS[c],
                "mean_score": round(mean, 3),
                "lift_vs_baseline": round(mean - base, 3) if base is not None else None,
            })
    return pd.DataFrame(rows)


def _load_entries(thinking: str, variant: str) -> dict[str, dict]:
    """Load (raw + judgment) per case_id for one (thinking, variant) cell."""
    if variant not in VARIANT_SUFFIX:
        raise ValueError(f"Unknown variant {variant!r}")
    exec_id = f"{thinking}_{VARIANT_SUFFIX[variant]}"
    raw_paths = sorted(raw_dir().glob(f"{exec_id}_*.json"))
    judge_paths = sorted(judgments_dir().glob(f"{exec_id}_*.json"))
    if not raw_paths or not judge_paths:
        return {}
    if len(raw_paths) != len(judge_paths):
        raise ValueError(f"File count mismatch for {exec_id}")

    entries: dict[str, dict] = {}
    weight_sum = sum(WEIGHTS.values())
    for raw_path, judge_path in zip(raw_paths, judge_paths):
        raws = json.loads(raw_path.read_text())
        judges = json.loads(judge_path.read_text())
        for raw, judge in zip(raws, judges):
            cid = case_id(raw["case"])
            scores = judge["judgment"]["scores"]
            weighted = sum(scores[c]["score"] * WEIGHTS[c] for c in CRITERIA) / weight_sum
            entries[cid] = {
                "case": raw["case"],
                "normalized": raw["normalized"],
                "judgment": judge["judgment"],
                "weighted_score": weighted,
            }
    return entries


def failure_mode_report(
    target_variant: str = "flat_alpha",
    reference_variant: str = "nested_narrative",
    new_levels: Iterable[str] = ("low", "medium", "high"),
    baseline: str = "minimal",
    baseline_threshold: float = 3.5,
    fixed_threshold: float = 4.0,
    top_n: int = 3,
) -> dict:
    """For each new level, classify cases where target@baseline fell below threshold.

    Buckets per case (target_variant @ {level} vs target_variant @ baseline):
      - fixed: new score >= fixed_threshold
      - improved: new > baseline but < fixed_threshold
      - still_broken: new <= baseline

    Writes 04_failure_mode_{level}.md with a per-case table and top-N
    side-by-side normalized JSON for fixed and still_broken cases. The
    reference_variant @ baseline is included for context in each markdown.
    """
    target_baseline = _load_entries(baseline, target_variant)
    reference_baseline = _load_entries(baseline, reference_variant)
    if not target_baseline:
        raise FileNotFoundError(
            f"No baseline data for {target_variant} @ {baseline}"
        )

    failing_cases = {
        cid: data for cid, data in target_baseline.items()
        if data["weighted_score"] < baseline_threshold
    }

    out_dir = analysis_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths_written: dict[str, str] = {}
    counts_by_level: dict[str, dict[str, int]] = {}

    for level in new_levels:
        target_at_level = _load_entries(level, target_variant)
        if not target_at_level:
            continue

        rows: list[dict] = []
        for cid, base_data in failing_cases.items():
            new_data = target_at_level.get(cid)
            if not new_data:
                continue
            base_score = base_data["weighted_score"]
            new_score = new_data["weighted_score"]
            delta = new_score - base_score
            if new_score >= fixed_threshold:
                bucket = "fixed"
            elif new_score > base_score:
                bucket = "improved"
            else:
                bucket = "still_broken"
            rows.append({
                "case_id": cid,
                "bucket": bucket,
                "baseline_score": round(base_score, 3),
                "new_score": round(new_score, 3),
                "delta": round(delta, 3),
                "base_data": base_data,
                "new_data": new_data,
                "reference_data": reference_baseline.get(cid),
            })

        rows.sort(key=lambda r: r["delta"], reverse=True)
        counts = {
            "fixed": sum(1 for r in rows if r["bucket"] == "fixed"),
            "improved": sum(1 for r in rows if r["bucket"] == "improved"),
            "still_broken": sum(1 for r in rows if r["bucket"] == "still_broken"),
            "total_failing_at_baseline": len(failing_cases),
            "matched": len(rows),
        }
        counts_by_level[level] = counts

        md_path = out_dir / f"04_failure_mode_{level}.md"
        md_path.write_text(_render_failure_md(
            target_variant, reference_variant, level, baseline,
            baseline_threshold, fixed_threshold, counts, rows, top_n,
        ))
        paths_written[level] = str(md_path)

    return {"counts": counts_by_level, "paths": paths_written}


def _render_failure_md(
    target: str, reference: str, level: str, baseline: str,
    base_threshold: float, fixed_threshold: float,
    counts: dict, rows: list[dict], top_n: int,
) -> str:
    lines = [
        f"# Failure-mode pull: {target} @ {level} vs {target} @ {baseline}",
        "",
        f"- Baseline threshold (failing at {baseline}): < {base_threshold}",
        f"- Fixed threshold (at {level}): ≥ {fixed_threshold}",
        f"- Reference variant (shown for context): `{reference}` @ {baseline}",
        "",
        "## Bucket counts",
        "",
        f"- Total cases failing at baseline: {counts['total_failing_at_baseline']}",
        f"- Matched at {level}: {counts['matched']}",
        f"- **Fixed**: {counts['fixed']}",
        f"- **Improved (but not fixed)**: {counts['improved']}",
        f"- **Still broken**: {counts['still_broken']}",
        "",
        "## Per-case table",
        "",
        "| case_id | bucket | baseline | new | delta |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['case_id']} | {r['bucket']} | "
            f"{r['baseline_score']:.2f} | {r['new_score']:.2f} | "
            f"{r['delta']:+.2f} |"
        )

    def section(title: str, picks: list[dict]) -> None:
        lines.append("")
        lines.append(f"## {title}")
        if not picks:
            lines.append("")
            lines.append("_(none)_")
            return
        for r in picks:
            lines.append("")
            lines.append(f"### {r['case_id']} ({r['bucket']}, "
                         f"{r['baseline_score']:.2f} → {r['new_score']:.2f})")
            for label, data in [
                (f"{target} @ {baseline}", r["base_data"]),
                (f"{target} @ {level}", r["new_data"]),
                (f"{reference} @ {baseline}", r["reference_data"]),
            ]:
                if data is None:
                    continue
                lines.append("")
                lines.append(f"**{label}**")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(data["normalized"], indent=2))
                lines.append("```")

    fixed_picks = [r for r in rows if r["bucket"] == "fixed"][:top_n]
    still_picks = sorted(
        [r for r in rows if r["bucket"] == "still_broken"],
        key=lambda r: r["new_score"],
    )[:top_n]
    section(f"Top {top_n} fixed", fixed_picks)
    section(f"Top {top_n} still broken", still_picks)
    return "\n".join(lines)


def run(
    levels: Iterable[str],
    variants: Iterable[str],
    *,
    baseline: str = "minimal",
) -> dict:
    """Compare variant(s) across thinking levels.

    Args:
        levels: thinking levels to include (must include baseline).
        variants: variants to compare across thinking levels.
        baseline: the reference thinking level for per-case deltas.

    Returns a dict with summary table + paired deltas + output paths.
    """
    levels = list(levels)
    variants = list(variants)
    if baseline not in levels:
        levels = [baseline, *levels]

    df = _load_all(levels, variants)

    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    summary = _summary_table(df)
    summary_path = out / "04_thinking_summary.csv"
    summary.to_csv(summary_path, index=False)

    deltas = _paired_deltas(df, baseline, levels, variants)
    deltas_path = out / "04_thinking_paired_summary.csv"
    if deltas:
        with open(deltas_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(deltas[0].keys()))
            w.writeheader()
            w.writerows(deltas)

    chart_path = out / "04_thinking_chart.png"
    _make_chart(summary, levels, str(chart_path))

    cpq = _cost_per_quality(summary, baseline)
    cpq_path = out / "04_thinking_cost_per_quality.csv"
    cpq.to_csv(cpq_path, index=False)

    lift = _criterion_lift(summary, baseline)
    lift_path = out / "04_thinking_criterion_lift.csv"
    lift.to_csv(lift_path, index=False)

    return {
        "summary": summary,
        "deltas": deltas,
        "cost_per_quality": cpq,
        "criterion_lift": lift,
        "_paths": {
            "summary": str(summary_path),
            "deltas": str(deltas_path),
            "chart": str(chart_path),
            "cost_per_quality": str(cpq_path),
            "criterion_lift": str(lift_path),
        },
    }
