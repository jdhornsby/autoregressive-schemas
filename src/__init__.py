"""Schema-order experiment: six structural variants of the same game level schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from pydantic import BaseModel

from .prompts import PROMPT
from .schemas import (
    AlphaNestedLevel,
    AppendOrderLevel,
    FlatAlphaLevel,
    NarrativeLevel,
    TypeGroupedLevel,
    UIContractLevel,
)


@dataclass(frozen=True)
class Variant:
    name: str
    note: str
    schema: Type[BaseModel]
    prompt: str


VARIANTS: list[Variant] = [
    Variant(
        "flat_alpha",
        "Flat, alphabetical. The database dump.",
        FlatAlphaLevel,
        PROMPT,
    ),
    Variant(
        "grouped_by_type",
        "Nested, fields sorted by type/length.",
        TypeGroupedLevel,
        PROMPT,
    ),
    Variant(
        "append_order",
        "Nested, fields in git-blame order.",
        AppendOrderLevel,
        PROMPT,
    ),
    Variant(
        "ui_contract",
        "Nested, fields in frontend render order.",
        UIContractLevel,
        PROMPT,
    ),
    Variant(
        "alpha_nested",
        "Nested properly, alphabetical within objects.",
        AlphaNestedLevel,
        PROMPT,
    ),
    Variant(
        "nested_narrative",
        "Nested, natural decision order. The ideal.",
        NarrativeLevel,
        PROMPT,
    ),
]
