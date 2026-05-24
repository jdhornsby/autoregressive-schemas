# Autoregressive Schemas

Does field ordering in a JSON tool-call schema affect what a small LLM actually generates? This repo tests that with Gemini's structured output: six schema variants, same prompt, same 39 fields, 64 input cases. A rubric-based judge scores each output; analysis scripts crunch the results.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A GCP project with the Vertex AI API enabled
- Application Default Credentials configured: `gcloud auth application-default login`

## Setup

```bash
git clone <repo-url>
cd autoregressive-schemas
uv sync
cp .env.example .env
# Edit .env with your GCP project ID
```

## Running the eval

The eval has three phases.

### Phase 1: Generate

Generate game levels for all 6 variants x 64 cases. This calls Vertex AI (Gemini) with forced structured output.

```bash
source .env

# Full run (384 generations)
uv run python -m src.run_eval my_run

# First 10 cases only
uv run python -m src.run_eval my_run --cases 10

# Specific variants
uv run python -m src.run_eval my_run --variants flat_alpha nested_narrative

# With a specific thinking level
uv run python -m src.run_eval my_run --thinking minimal
```

Raw results are saved to `results/raw/` and normalized (judge-safe) versions to `results/normalized/`, both in batches of 16.

### Phase 2: Judge

Judging is performed by Claude Code sub-agents reading `judge_prompt.md`, not by the Python code. Each sub-agent evaluates normalized levels from `results/normalized/` and writes structured judgments to `results/judgments/`.

### Phase 3: Score

Aggregate the raw judgments into weighted scores.

```bash
uv run python -m src.score my_run
```

## The six variants

| Variant | Structure | Field order | What it represents |
|---------|-----------|-------------|-------------------|
| flat_alpha | flat (39 fields) | alphabetical | Auto-generated from a spec |
| grouped_by_type | nested | by data type | Numbers first, then strings |
| append_order | nested | git-blame order | Fields added across sprints |
| ui_contract | nested | frontend render order | Shaped by the UI, not the model |
| alpha_nested | nested | alphabetical within objects | Linter-sorted keys |
| nested_narrative | nested | decision order | The way a designer would think |

## Analysis

The analysis scripts cover minimum-thinking results only and support the first blog post. Each script runs independently.

```bash
uv run python -m analysis.a01_summary_stats
uv run python -m analysis.a02_paired_comparisons
uv run python -m analysis.a03_striking_pairs
```

- `01_summary_stats` - mean, SD, SE, min, max weighted score per variant (CSV)
- `02_paired_comparisons` - per-case score differences between nested_narrative and the three weakest variants (CSV)
- `03_striking_pairs` - the 5 input cases where flat_alpha and nested_narrative diverge most, with full outputs for side-by-side review (markdown in `results/analysis/03_striking_pairs/`)

## Tests

```bash
uv run pytest
```

## License

MIT
