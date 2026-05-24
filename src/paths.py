"""Project directory layout. Call set_root() to change the project root."""

from __future__ import annotations

from pathlib import Path

_root: Path = Path.cwd()


def set_root(path: Path) -> None:
    global _root
    _root = path.resolve()


def root() -> Path:
    return _root


def cases_path() -> Path:
    return _root / "inputs" / "cases.json"


def raw_dir() -> Path:
    return _root / "results" / "raw"


def normalized_dir() -> Path:
    return _root / "results" / "normalized"


def judgments_dir() -> Path:
    return _root / "results" / "judgments"


def scores_dir() -> Path:
    return _root / "results" / "scores"


def analysis_dir() -> Path:
    return _root / "results" / "analysis"
