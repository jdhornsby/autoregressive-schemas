"""Generate levels and write results to disk."""

from __future__ import annotations

import json
from typing import Any, Callable

from . import VARIANTS, Variant
from .generate import generate
from .normalize import normalize
from .paths import normalized_dir, raw_dir

MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
]

BATCH_SIZE = 16


def _resolve_variant(name: str) -> Variant:
    by_name = {v.name: v for v in VARIANTS}
    if name not in by_name:
        raise ValueError(f"Unknown variant {name!r}. Choose from: {list(by_name)}")
    return by_name[name]


def _run_one(
    variant: Variant,
    case: dict,
    *,
    thinking_level: str | None = None,
    model: str | None = None,
) -> dict:
    """Generate one level. Returns the full result dict."""
    kwargs: dict[str, Any] = {}
    if model:
        kwargs["model"] = model
    result, stats = generate(
        schema=variant.schema,
        prompt=variant.prompt,
        thinking_level=thinking_level,
        **kwargs,
        **case,
    )
    raw = json.loads(result.model_dump_json())
    entry: dict[str, Any] = {
        "variant": variant.name,
        "case": case,
        "output": raw,
        "normalized": normalize(variant.name, raw),
        "stats": stats,
    }
    if model:
        entry["model"] = model
    return entry


def _flush(batch: list[dict], exec_id: str, part: int) -> None:
    raw_dir().mkdir(parents=True, exist_ok=True)
    normalized_dir().mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir() / f"{exec_id}_{part}.json"
    raw_path.write_text(json.dumps(batch, indent=2))

    norm_batch = [{"case": e["case"], "level": e["normalized"]} for e in batch]
    norm_path = normalized_dir() / f"{exec_id}_{part}.json"
    norm_path.write_text(json.dumps(norm_batch, indent=2))


def run_variants(
    exec_id: str,
    cases: list[dict],
    variant_names: list[str] | None = None,
    thinking_level: str | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> int:
    """Generate levels for all variants x cases. Returns total count."""
    variants = [_resolve_variant(n) for n in variant_names] if variant_names else VARIANTS

    batch: list[dict] = []
    part = 0
    total = len(variants) * len(cases)
    n = 0

    for case in cases:
        for variant in variants:
            n += 1
            label = f"{variant.name} / {case['player_class']}"
            if on_progress:
                on_progress(n, total, label)
            result = _run_one(variant, case, thinking_level=thinking_level)
            batch.append(result)

            if len(batch) >= BATCH_SIZE:
                _flush(batch, exec_id, part)
                part += 1
                batch = []

    if batch:
        _flush(batch, exec_id, part)

    return n


def run_models(
    exec_id: str,
    cases: list[dict],
    models: list[str],
    passes: int = 1,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> int:
    """Generate levels for one variant across multiple models. Returns total count."""
    variant = _resolve_variant("nested_narrative")
    all_cases = cases * passes
    total = len(models) * len(all_cases)
    n = 0

    for model in models:
        tag = model.replace(".", "").replace("-", "_")
        batch: list[dict] = []
        part = 0

        for case in all_cases:
            n += 1
            label = f"{model} / {case['player_class']} ({case['genre']})"
            if on_progress:
                on_progress(n, total, label)
            result = _run_one(variant, case, thinking_level="minimal", model=model)
            batch.append(result)

            if len(batch) >= BATCH_SIZE:
                _flush(batch, f"{exec_id}_{tag}", part)
                part += 1
                batch = []

        if batch:
            _flush(batch, f"{exec_id}_{tag}", part)

    return n
