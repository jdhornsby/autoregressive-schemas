"""Entry point: generate game levels for all variants x cases and save to disk.

Writes two outputs per batch:
  results/raw/        - full results with raw output, stats, variant name
  results/normalized/ - judge-safe: only case + normalized level, no variant

Usage:
    uv run python -m src.run_eval my_run
    uv run python -m src.run_eval my_run --cases 10
    uv run python -m src.run_eval my_run --variants flat_alpha nested_narrative
    uv run python -m src.run_eval my_run --thinking minimal
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import VARIANTS, Variant
from .generate import generate
from .normalize import normalize

INPUTS_PATH = Path("inputs/cases.json")
RAW_DIR = Path("results/raw")
NORM_DIR = Path("results/normalized")
BATCH_SIZE = 16


def run_one(variant: Variant, case: dict, thinking_level: str | None = None) -> dict:
    """Generate one level. Returns the full result dict."""
    result, stats = generate(
        schema=variant.schema,
        prompt=variant.prompt,
        thinking_level=thinking_level,
        **case,
    )
    raw = json.loads(result.model_dump_json())
    return {
        "variant": variant.name,
        "case": case,
        "output": raw,
        "normalized": normalize(variant.name, raw),
        "stats": stats,
    }


def _flush(batch: list[dict], exec_id: str, part: int) -> None:
    raw_path = RAW_DIR / f"{exec_id}_{part}.json"
    raw_path.write_text(json.dumps(batch, indent=2))

    norm_batch = [{"case": entry["case"], "level": entry["normalized"]} for entry in batch]
    norm_path = NORM_DIR / f"{exec_id}_{part}.json"
    norm_path.write_text(json.dumps(norm_batch, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate game levels (no judging).")
    parser.add_argument("exec_id", help="Execution identifier (used in output filenames)")
    parser.add_argument("--cases", type=int, help="Number of cases to run (default: all 64)")
    parser.add_argument("--variants", nargs="*", help="Variant names (default: all)")
    parser.add_argument(
        "--thinking",
        choices=["minimal", "low", "medium", "high"],
        default=None,
        help="Thinking level (default: model default)",
    )
    args = parser.parse_args()

    cases = json.loads(INPUTS_PATH.read_text())
    if args.cases:
        cases = cases[: args.cases]

    variants = VARIANTS
    if args.variants:
        by_name = {v.name: v for v in VARIANTS}
        variants = [by_name[name] for name in args.variants]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_DIR.mkdir(parents=True, exist_ok=True)

    batch: list[dict] = []
    part = 0
    total = len(variants) * len(cases)
    n = 0

    for case in cases:
        for variant in variants:
            n += 1
            print(f"[{n}/{total}] {variant.name} / {case['player_class']}...", flush=True)
            result = run_one(variant, case, thinking_level=args.thinking)
            batch.append(result)

            if len(batch) >= BATCH_SIZE:
                _flush(batch, args.exec_id, part)
                part += 1
                batch = []

    if batch:
        _flush(batch, args.exec_id, part)

    print(f"\n{n} generations saved to {RAW_DIR} and {NORM_DIR}")


if __name__ == "__main__":
    main()
