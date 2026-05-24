"""Find input cases where nested_narrative and flat_alpha diverge most.

Identifies the top N cases with the largest positive score difference
(nested_narrative much better than flat_alpha) at minimum thinking.
Writes a markdown file for each with full outputs and scores.
"""

from __future__ import annotations

import json

from ..paths import analysis_dir, judgments_dir, raw_dir
from ..rubric import WEIGHTS, case_id

TOP_N = 5
CRITERIA = list(WEIGHTS.keys())
WEIGHT_SUM = sum(WEIGHTS.values())

NARRATIVE_EXEC = "minimal_6"
FLAT_EXEC = "minimal_1"


def _load_entries(exec_id: str) -> dict[str, dict]:
    """Load all entries for an exec_id, keyed by case_id."""
    entries: dict[str, dict] = {}
    for part in range(4):
        raw_path = raw_dir() / f"{exec_id}_{part}.json"
        judge_path = judgments_dir() / f"{exec_id}_{part}.json"

        if not raw_path.exists():
            raise FileNotFoundError(f"Missing: {raw_path}")
        if not judge_path.exists():
            raise FileNotFoundError(f"Missing: {judge_path}")

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


def _render_md(rank: int, cid: str, case: dict, flat: dict, narrative: dict) -> str:
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
        "| Criterion | flat_alpha | nested_narrative |",
        "|-----------|-----------|-----------------|",
    ]
    for c in CRITERIA:
        fs = flat["judgment"]["scores"][c]["score"]
        ns = narrative["judgment"]["scores"][c]["score"]
        lines.append(f"| {c} | {fs} | {ns} |")
    lines.append(
        f"| **weighted** | **{flat['weighted_score']:.2f}** "
        f"| **{narrative['weighted_score']:.2f}** |"
    )
    lines.append("")

    for variant_name, data in [("flat_alpha", flat), ("nested_narrative", narrative)]:
        j = data["judgment"]
        lines.append(f"## {variant_name} judge notes")
        lines.append("")
        if "best_element" in j:
            lines.append(f"**Best element:** {j['best_element']}")
        if "worst_element" in j:
            lines.append(f"**Worst element:** {j['worst_element']}")
        lines.append("")

    for label, data in [("flat_alpha", flat), ("nested_narrative", narrative)]:
        lines.append(f"## {label} full output")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(data["normalized"], indent=2))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def run() -> list[tuple[str, float]]:
    """Find and write striking pairs. Returns list of (case_id, diff)."""
    narrative_entries = _load_entries(NARRATIVE_EXEC)
    flat_entries = _load_entries(FLAT_EXEC)

    diffs: list[tuple[str, float]] = []
    for cid in narrative_entries:
        if cid not in flat_entries:
            raise ValueError(f"Case {cid} missing from flat_alpha results")
        diff = narrative_entries[cid]["weighted_score"] - flat_entries[cid]["weighted_score"]
        diffs.append((cid, diff))

    diffs.sort(key=lambda x: x[1], reverse=True)
    top = diffs[:TOP_N]

    out = analysis_dir() / "03_striking_pairs"
    out.mkdir(parents=True, exist_ok=True)

    for rank, (cid, diff) in enumerate(top, 1):
        narrative = narrative_entries[cid]
        flat = flat_entries[cid]
        md = _render_md(rank, cid, narrative["case"], flat, narrative)
        path = out / f"{rank:02d}_{cid}.md"
        path.write_text(md)

    return top
