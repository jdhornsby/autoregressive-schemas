"""Shared data loading for analysis scripts.

Reads raw generation results and judgment files, joins them by
(thinking_level, variant, case_id), and returns a DataFrame.
"""

from __future__ import annotations

import json

import pandas as pd

from ..paths import judgments_dir, raw_dir
from ..rubric import WEIGHTS, case_id

VARIANT_MAP: dict[str, str] = {
    "1": "flat_alpha",
    "2": "grouped_by_type",
    "3": "append_order",
    "4": "ui_contract",
    "5": "alpha_nested",
    "6": "nested_narrative",
}

THINKING_LEVELS = ["minimal", "low", "medium", "high"]
CRITERIA = list(WEIGHTS.keys())
WEIGHT_SUM = sum(WEIGHTS.values())


def load_thinking_level(thinking: str) -> pd.DataFrame:
    """Load all data for a single thinking level. Returns a DataFrame."""
    rows: list[dict] = []

    for suffix, variant in VARIANT_MAP.items():
        exec_id = f"{thinking}_{suffix}"
        for part in range(4):
            raw_path = raw_dir() / f"{exec_id}_{part}.json"
            judge_path = judgments_dir() / f"{exec_id}_{part}.json"

            if not raw_path.exists():
                raise FileNotFoundError(f"Missing raw file: {raw_path}")
            if not judge_path.exists():
                raise FileNotFoundError(f"Missing judgment file: {judge_path}")

            raw_entries = json.loads(raw_path.read_text())
            judge_entries = json.loads(judge_path.read_text())

            if len(raw_entries) != len(judge_entries):
                raise ValueError(
                    f"Length mismatch: {raw_path} ({len(raw_entries)}) "
                    f"vs {judge_path} ({len(judge_entries)})"
                )

            for raw, judge in zip(raw_entries, judge_entries):
                scores = judge["judgment"]["scores"]
                row: dict = {
                    "thinking_level": thinking,
                    "variant": variant,
                    "case_id": case_id(raw["case"]),
                    "genre": raw["case"]["genre"],
                    "mood": raw["case"]["mood"],
                    "player_class": raw["case"]["player_class"],
                    "target_difficulty": raw["case"]["target_difficulty"],
                    "latency_ms": raw["stats"]["latency_ms"],
                    "thinking_tokens": raw["stats"]["thinking_tokens"],
                    "output_tokens": raw["stats"]["output_tokens"],
                    "prompt_tokens": raw["stats"]["prompt_tokens"],
                }
                for c in CRITERIA:
                    row[c] = scores[c]["score"]
                row["weighted_score"] = (
                    sum(row[c] * WEIGHTS[c] for c in CRITERIA) / WEIGHT_SUM
                )
                rows.append(row)

    return pd.DataFrame(rows)


def load_minimal() -> pd.DataFrame:
    """Load all data for thinking_level=minimal."""
    return load_thinking_level("minimal")
