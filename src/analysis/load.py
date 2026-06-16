"""Shared data loading for analysis scripts.

Reads raw generation results and judgment files, joins them by
(thinking_level, variant, case_id), and returns a DataFrame.
"""

from __future__ import annotations

import json
from typing import Iterable

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

VARIANT_SUFFIX: dict[str, str] = {v: k for k, v in VARIANT_MAP.items()}

THINKING_LEVELS = ["minimal", "low", "medium", "high"]
CRITERIA = list(WEIGHTS.keys())
WEIGHT_SUM = sum(WEIGHTS.values())


def _resolve_variants(variants: Iterable[str] | None) -> list[tuple[str, str]]:
    """Return [(suffix, variant_name)] for the requested variants, preserving canonical order."""
    if variants is None:
        return list(VARIANT_MAP.items())
    wanted = set(variants)
    unknown = wanted - set(VARIANT_SUFFIX)
    if unknown:
        raise ValueError(f"Unknown variants: {sorted(unknown)}")
    return [(VARIANT_SUFFIX[v], v) for v in VARIANT_MAP.values() if v in wanted]


def load_thinking_level(
    thinking: str,
    variants: Iterable[str] | None = None,
    *,
    strict: bool = True,
) -> pd.DataFrame:
    """Load all data for a single thinking level.

    Args:
        thinking: thinking level (minimal/low/medium/high).
        variants: variant names to load; None loads all six.
        strict: if True (default), raise on any missing variant files.
            If False, silently skip missing variant exec_ids — useful when
            only a subset of variants was generated for this thinking level.

    Returns a DataFrame with one row per (variant, case_id).
    """
    rows: list[dict] = []

    for suffix, variant in _resolve_variants(variants):
        exec_id = f"{thinking}_{suffix}"
        raw_paths = sorted(raw_dir().glob(f"{exec_id}_*.json"))
        judge_paths = sorted(judgments_dir().glob(f"{exec_id}_*.json"))

        if not raw_paths:
            if strict:
                raise FileNotFoundError(f"No raw files for exec_id {exec_id!r}")
            continue
        if not judge_paths:
            if strict:
                raise FileNotFoundError(f"No judgment files for exec_id {exec_id!r}")
            continue
        if len(raw_paths) != len(judge_paths):
            raise ValueError(
                f"File count mismatch for {exec_id}: "
                f"{len(raw_paths)} raw vs {len(judge_paths)} judgments"
            )

        for raw_path, judge_path in zip(raw_paths, judge_paths):
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
    """Load all data for thinking_level=minimal (all six variants)."""
    return load_thinking_level("minimal")
