"""CLI smoke tests using click's CliRunner."""

from __future__ import annotations

import json

from click.testing import CliRunner

from src.cli import cli

from .conftest import SAMPLE_CASE, make_judgment

runner = CliRunner()


def test_help():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "compare" in result.output
    assert "score" in result.output
    assert "analyze" in result.output


def test_generate_help():
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--cases" in result.output
    assert "--variants" in result.output


def test_score_variants_help():
    result = runner.invoke(cli, ["score", "variants", "--help"])
    assert result.exit_code == 0


def test_score_models_help():
    result = runner.invoke(cli, ["score", "models", "--help"])
    assert result.exit_code == 0


def test_analyze_help():
    result = runner.invoke(cli, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "variants" in result.output
    assert "models" in result.output


def test_score_variants_with_data(project_dir):
    judgment = make_judgment()
    data = [{"variant": "flat_alpha", "case": SAMPLE_CASE, "judgment": judgment}]
    (project_dir / "results" / "judgments" / "test_1_0.json").write_text(json.dumps(data))

    result = runner.invoke(cli, ["--project-dir", str(project_dir), "score", "variants", "test"])
    assert result.exit_code == 0
    assert "flat_alpha" in result.output


def test_generate_with_mock(project_dir, mock_genai):
    cases = [SAMPLE_CASE]
    (project_dir / "inputs" / "cases.json").write_text(json.dumps(cases))

    result = runner.invoke(
        cli,
        ["--project-dir", str(project_dir), "generate", "test_run",
         "--cases", "1", "--variants", "flat_alpha"],
    )
    assert result.exit_code == 0

    raw_files = list((project_dir / "results" / "raw").glob("test_run_*.json"))
    assert len(raw_files) == 1

    norm_files = list((project_dir / "results" / "normalized").glob("test_run_*.json"))
    assert len(norm_files) == 1
