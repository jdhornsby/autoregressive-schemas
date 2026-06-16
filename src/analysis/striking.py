"""Find input cases where two variants diverge most.

Identifies the top N cases with the largest positive score difference
(variant A minus variant B) at a given thinking level, and writes a
markdown file for each with full outputs and scores.
"""

from __future__ import annotations

import json

from ..paths import analysis_dir, judgments_dir, raw_dir
from ..rubric import WEIGHTS, case_id
from .load import VARIANT_SUFFIX

TOP_N = 5
CRITERIA = list(WEIGHTS.keys())
WEIGHT_SUM = sum(WEIGHTS.values())


def _exec_id(thinking: str, variant: str) -> str:
    if variant not in VARIANT_SUFFIX:
        raise ValueError(f"Unknown variant {variant!r}")
    return f"{thinking}_{VARIANT_SUFFIX[variant]}"


def _load_entries(exec_id: str) -> dict[str, dict]:
    """Load all entries for an exec_id, keyed by case_id."""
    entries: dict[str, dict] = {}
    raw_paths = sorted(raw_dir().glob(f"{exec_id}_*.json"))
    judge_paths = sorted(judgments_dir().glob(f"{exec_id}_*.json"))

    if not raw_paths:
        raise FileNotFoundError(f"No raw files for {exec_id}")
    if not judge_paths:
        raise FileNotFoundError(f"No judgment files for {exec_id}")
    if len(raw_paths) != len(judge_paths):
        raise ValueError(
            f"File count mismatch for {exec_id}: "
            f"{len(raw_paths)} raw vs {len(judge_paths)} judgments"
        )

    for raw_path, judge_path in zip(raw_paths, judge_paths):
        raws = json.loads(raw_path.read_text())
        judges = json.loads(judge_path.read_text())

        for raw, judge in zip(raws, judges):
            cid = case_id(raw["case"])
            scores = judge["judgment"]["scores"]
            weighted = sum(scores[c]["score"] * WEIGHTS[c] for c in CRITERIA) / WEIGHT_SUM
            entries[cid] = {
                "case": raw["case"],
                "normalized": raw["normalized"],
                "judgment": judge["judgment"],
                "weighted_score": weighted,
            }
    return entries


def _render_md(
    rank: int, cid: str, case: dict,
    variant_a: str, variant_b: str,
    data_a: dict, data_b: dict,
) -> str:
    lines = [
        f"# Striking pair {rank}: {cid}",
        "",
        "## Input",
        "",
        f"- Genre: {case['genre']}",
        f"- Mood: {case['mood']}",
        f"- Player class: {case['player_class']}",
        f"- Target difficulty: {case['target_difficulty']}",
        "",
        "## Scores",
        "",
        f"| Criterion | {variant_b} | {variant_a} |",
        "|-----------|-----------|-----------------|",
    ]
    for c in CRITERIA:
        bs = data_b["judgment"]["scores"][c]["score"]
        as_ = data_a["judgment"]["scores"][c]["score"]
        lines.append(f"| {c} | {bs} | {as_} |")
    lines.append(
        f"| **weighted** | **{data_b['weighted_score']:.2f}** "
        f"| **{data_a['weighted_score']:.2f}** |"
    )
    lines.append("")

    for variant_name, data in [(variant_b, data_b), (variant_a, data_a)]:
        j = data["judgment"]
        lines.append(f"## {variant_name} judge notes")
        lines.append("")
        if "best_element" in j:
            lines.append(f"**Best element:** {j['best_element']}")
        if "worst_element" in j:
            lines.append(f"**Worst element:** {j['worst_element']}")
        lines.append("")

    for label, data in [(variant_b, data_b), (variant_a, data_a)]:
        lines.append(f"## {label} full output")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(data["normalized"], indent=2))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def run(
    thinking: str = "minimal",
    variant_a: str = "nested_narrative",
    variant_b: str = "flat_alpha",
    top_n: int = TOP_N,
) -> list[tuple[str, float]]:
    """Find and write striking pairs. Returns list of (case_id, diff)."""
    entries_a = _load_entries(_exec_id(thinking, variant_a))
    entries_b = _load_entries(_exec_id(thinking, variant_b))

    diffs: list[tuple[str, float]] = []
    for cid in entries_a:
        if cid not in entries_b:
            continue
        diff = entries_a[cid]["weighted_score"] - entries_b[cid]["weighted_score"]
        diffs.append((cid, diff))

    diffs.sort(key=lambda x: x[1], reverse=True)
    top = diffs[:top_n]

    tag = f"{thinking}_{variant_a}_vs_{variant_b}"
    out = analysis_dir() / f"03_striking_pairs_{tag}"
    out.mkdir(parents=True, exist_ok=True)

    for rank, (cid, _diff) in enumerate(top, 1):
        data_a = entries_a[cid]
        data_b = entries_b[cid]
        md = _render_md(rank, cid, data_a["case"], variant_a, variant_b, data_a, data_b)
        path = out / f"{rank:02d}_{cid}.md"
        path.write_text(md)

    return top
