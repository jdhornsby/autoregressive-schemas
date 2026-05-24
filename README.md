# Autoregressive Schemas

Does field ordering in a JSON tool-call schema affect what a small LLM generates?

This repo tests that hypothesis using Gemini's structured output mode. Six schema variants — same 39 fields, same prompt, 64 input cases — are judged on a rubric by Claude and compared statistically. A second experiment compares Gemini 3 Flash Preview vs 3.5 Flash head-to-head.

## Setup

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and a GCP project with Vertex AI enabled.

```bash
uv sync
cp .env.example .env   # add your GCP project ID
source .env
```

## Usage

```bash
# Generate levels (calls Vertex AI)
uv run ars generate my_run
uv run ars generate my_run --cases 10 --variants flat_alpha --thinking minimal

# Model head-to-head (nested_narrative only, two Gemini models)
uv run ars compare my_run

# Score judgments
uv run ars score variants minimal
uv run ars score models flash_v1_gemini_35_flash flash_v1_gemini_3_flash_preview

# Analyze
uv run ars analyze variants   # summary stats, paired comparisons, striking pairs, chart
uv run ars analyze models flash_v1_gemini_35_flash flash_v1_gemini_3_flash_preview
```

Judging is done out-of-band by Claude Code sub-agents using `judge_prompt.md`.

## The six variants

| Variant | Structure | Field order | What it represents |
|---------|-----------|-------------|-------------------|
| flat_alpha | flat (39 fields) | alphabetical | Auto-generated from a spec |
| grouped_by_type | nested | by data type | Numbers first, then strings |
| append_order | nested | git-blame order | Fields added across sprints |
| ui_contract | nested | frontend render order | Shaped by the UI, not the model |
| alpha_nested | nested | alphabetical within objects | Linter-sorted keys |
| nested_narrative | nested | decision order | The way a designer would think |

## Tests

```bash
uv run pytest
```

## License

MIT
