"""Head-to-head: Gemini 3 Flash Preview vs Gemini 3.5 Flash (stable).

Runs nested_narrative only, n=72 cases per model. Saves raw + normalized
results tagged with model name for later head-to-head judging.

Usage:
    uv run python -m src.run_flash my_run
    uv run python -m src.run_flash my_run --cases 10
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import VARIANTS, Variant
from .generate import generate
from .normalize import normalize

MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
]

VARIANT_NAME = "nested_narrative"

INPUTS_PATH = Path("inputs/cases.json")
RAW_DIR = Path("results/raw")
NORM_DIR = Path("results/normalized")
BATCH_SIZE = 16


def _get_variant() -> Variant:
    by_name = {v.name: v for v in VARIANTS}
    return by_name[VARIANT_NAME]


def run_one(variant: Variant, case: dict, model: str) -> dict:
    """Generate one level for a specific model. Returns the full result dict."""
    result, stats = generate(
        schema=variant.schema,
        prompt=variant.prompt,
        thinking_level="minimal",
        model=model,
        **case,
    )
    raw = json.loads(result.model_dump_json())
    return {
        "model": model,
        "variant": variant.name,
        "case": case,
        "output": raw,
        "normalized": normalize(variant.name, raw),
        "stats": stats,
    }


def _flush(batch: list[dict], exec_id: str, part: int) -> None:
    raw_path = RAW_DIR / f"{exec_id}_{part}.json"
    raw_path.write_text(json.dumps(batch, indent=2))

    norm_batch = [
        {"case": entry["case"], "level": entry["normalized"]}
        for entry in batch
    ]
    norm_path = NORM_DIR / f"{exec_id}_{part}.json"
    norm_path.write_text(json.dumps(norm_batch, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Head-to-head: Gemini 3 Flash vs 3.5 Flash"
    )
    parser.add_argument("exec_id", help="Execution identifier (used in output filenames)")
    parser.add_argument("--cases", type=int, help="Number of cases to run (default: all 72)")
    parser.add_argument("--passes", type=int, default=1, help="Number of passes through the case list (default: 1)")
    args = parser.parse_args()

    base_cases = json.loads(INPUTS_PATH.read_text())
    if args.cases:
        base_cases = base_cases[: args.cases]

    cases = base_cases * args.passes

    variant = _get_variant()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_DIR.mkdir(parents=True, exist_ok=True)

    total = len(MODELS) * len(cases)
    n = 0

    for model in MODELS:
        tag = model.replace(".", "").replace("-", "_")
        batch: list[dict] = []
        part = 0

        print(f"\n{'=' * 60}")
        print(f"Model: {model}  ({len(cases)} generations, {args.passes} pass(es))")
        print(f"{'=' * 60}\n")

        for case in cases:
            n += 1
            print(
                f"[{n}/{total}] {model} / {case['player_class']} ({case['genre']})...",
                flush=True,
            )
            result = run_one(variant, case, model)
            batch.append(result)

            if len(batch) >= BATCH_SIZE:
                _flush(batch, f"{args.exec_id}_{tag}", part)
                part += 1
                batch = []

        if batch:
            _flush(batch, f"{args.exec_id}_{tag}", part)

    print(f"\n{n} generations saved to {RAW_DIR} and {NORM_DIR}")


if __name__ == "__main__":
    main()
