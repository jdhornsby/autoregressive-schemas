"""CLI for the autoregressive-schemas experiment suite."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import paths

console = Console()


@click.group()
@click.option(
    "--project-dir", type=click.Path(exists=True, file_okay=False),
    default=".", help="Project root directory.",
)
def cli(project_dir: str) -> None:
    """ars -- autoregressive schema experiments."""
    paths.set_root(Path(project_dir))


# generate

@cli.command()
@click.argument("exec_id")
@click.option("--cases", type=int, default=None, help="Limit to first N cases.")
@click.option("--variants", multiple=True, help="Variant names (default: all).")
@click.option(
    "--thinking", type=click.Choice(["minimal", "low", "medium", "high"]),
    default=None, help="Thinking level.",
)
def generate(exec_id: str, cases: int | None, variants: tuple[str, ...], thinking: str | None):
    """Generate game levels for all variants x cases."""
    from .run import run_variants

    all_cases = json.loads(paths.cases_path().read_text())
    if cases:
        all_cases = all_cases[:cases]

    variant_list = list(variants) if variants else None

    with Progress(
        SpinnerColumn(), TextColumn("[bold]{task.description}"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:
        task = progress.add_task("Generating...", total=0)

        def on_progress(current: int, total: int, label: str) -> None:
            progress.update(task, total=total, completed=current, description=label)

        n = run_variants(exec_id, all_cases, variant_list, thinking, on_progress)

    console.print(f"\n[green]{n} generations[/] saved to {paths.raw_dir()}")


# compare

@cli.command()
@click.argument("exec_id")
@click.option("--cases", type=int, default=None, help="Limit to first N cases.")
@click.option("--passes", type=int, default=1, help="Passes through the case list.")
def compare(exec_id: str, cases: int | None, passes: int):
    """Run head-to-head model comparison (nested_narrative only)."""
    from .run import MODELS, run_models

    all_cases = json.loads(paths.cases_path().read_text())
    if cases:
        all_cases = all_cases[:cases]

    with Progress(
        SpinnerColumn(), TextColumn("[bold]{task.description}"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:
        task = progress.add_task("Comparing...", total=0)

        def on_progress(current: int, total: int, label: str) -> None:
            progress.update(task, total=total, completed=current, description=label)

        n = run_models(exec_id, all_cases, MODELS, passes, on_progress)

    console.print(f"\n[green]{n} generations[/] saved to {paths.raw_dir()}")


# score

@cli.group()
def score():
    """Aggregate judgment scores."""


@score.command("variants")
@click.argument("exec_id")
def score_variants(exec_id: str):
    """Aggregate judgments by schema variant."""
    from .scoring import aggregate_variants

    result = aggregate_variants(exec_id)
    if result is None:
        console.print(f"[red]No judgment files found for {exec_id!r}[/]")
        raise SystemExit(1)

    table = Table(title=f"Scores: {exec_id}")
    table.add_column("Variant")
    table.add_column("N", justify="right")
    table.add_column("Weighted", justify="right")

    for name, data in sorted(result["variants"].items(), key=lambda x: x[1]["weighted_total"],
                              reverse=True):
        table.add_row(name, str(data["n"]), f"{data['weighted_total']:.2f}")

    console.print(table)
    console.print(f"Written to {paths.scores_dir() / f'{exec_id}_scores.json'}")


@score.command("models")
@click.argument("model_a")
@click.argument("model_b")
def score_models(model_a: str, model_b: str):
    """Head-to-head model comparison."""
    from .scoring import compare_models

    result = compare_models(model_a, model_b)

    table = Table(title=f"{model_a} vs {model_b}")
    table.add_column("Criterion")
    table.add_column("Weight", justify="right")
    table.add_column(model_a, justify="right")
    table.add_column(model_b, justify="right")
    table.add_column("Diff", justify="right")

    from .rubric import WEIGHTS
    for c in WEIGHTS:
        cr = result["criteria"][c]
        style = "green" if cr["diff"] > 0 else ("red" if cr["diff"] < 0 else "")
        table.add_row(c, str(WEIGHTS[c]), f"{cr['a']:.3f}", f"{cr['b']:.3f}",
                      f"{cr['diff']:+.3f}", style=style)

    console.print(table)
    console.print()

    a, b = result["model_a"], result["model_b"]
    console.print(f"  {a['name']}: [bold]{a['mean']:.3f}[/] (n={a['n']})")
    console.print(f"  {b['name']}: [bold]{b['mean']:.3f}[/] (n={b['n']})")
    console.print(
        f"  Wins: {result['a_wins']}-{result['b_wins']}-{result['ties']} "
        f"(mean diff {result['mean_diff']:+.3f})"
    )
    console.print(f"\nCSVs written to {paths.scores_dir()}")


# analyze

@cli.group()
def analyze():
    """Run analysis and produce reports."""


@analyze.command("variants")
def analyze_variants():
    """Full analysis of the schema variant experiment."""
    from .analysis.chart import run as run_chart
    from .analysis.paired import run as run_paired
    from .analysis.striking import run as run_striking
    from .analysis.summary import run as run_summary

    console.print("[bold]Summary statistics[/]")
    df = run_summary()
    table = Table()
    for col in df.columns:
        table.add_column(col, justify="right" if col != "variant" else "left")
    for _, row in df.iterrows():
        table.add_row(*[str(v) for v in row])
    console.print(table)
    console.print(f"  -> {paths.analysis_dir() / '01_summary_stats.csv'}")
    console.print()

    console.print("[bold]Paired comparisons[/]")
    summaries = run_paired()
    for s in summaries:
        console.print(
            f"  {s['pair']}: {s['mean_diff']:+.4f} "
            f"({s['narrative_wins']}-{s['comparator_wins']}-{s['ties']})"
        )
    console.print()

    console.print("[bold]Striking pairs[/]")
    top = run_striking()
    for cid, diff in top:
        console.print(f"  {cid}: {diff:+.2f}")
    console.print()

    console.print("[bold]Chart[/]")
    out_path = run_chart()
    console.print(f"  -> {out_path}")

    console.print(f"\n[green]All outputs written to {paths.analysis_dir()}[/]")


@analyze.command("models")
@click.argument("model_a")
@click.argument("model_b")
def analyze_models(model_a: str, model_b: str):
    """Full analysis of a model head-to-head experiment."""
    from .analysis.models import run
    from .rubric import WEIGHTS

    report = run(model_a, model_b)
    scoring = report["scoring"]
    tokens = report["tokens"]
    latency = report["latency"]
    rel = report["reliability"]

    console.print("[bold]1. Scoring[/]")
    table = Table()
    table.add_column("Criterion")
    table.add_column("Weight", justify="right")
    table.add_column(model_a, justify="right")
    table.add_column(model_b, justify="right")
    table.add_column("Diff", justify="right")

    for c in WEIGHTS:
        cr = scoring["criteria"][c]
        style = "green" if cr["diff"] > 0 else ("red" if cr["diff"] < 0 else "")
        table.add_row(c, str(cr["weight"]), f"{cr['a_mean']:.3f}", f"{cr['b_mean']:.3f}",
                      f"{cr['diff']:+.3f}", style=style)

    console.print(table)
    console.print(
        f"  Weighted: [bold]{scoring['a_mean']:.3f}[/] vs [bold]{scoring['b_mean']:.3f}[/] "
        f"({scoring['diff']:+.3f})"
    )
    console.print(f"  Wins: {scoring['a_wins']}-{scoring['b_wins']}-{scoring['ties']}")
    console.print()

    console.print("[bold]2. Token Usage[/]")
    table = Table()
    table.add_column("Metric")
    table.add_column(model_a, justify="right")
    table.add_column(model_b, justify="right")

    for field in ["prompt_tokens", "output_tokens", "thinking_tokens"]:
        a_t, b_t = tokens[field]["a"], tokens[field]["b"]
        label = field.replace("_", " ").title()
        table.add_row(f"{label} (mean)", f"{a_t['mean']:.0f}", f"{b_t['mean']:.0f}")
        table.add_row(f"{label} (sd)", f"{a_t['sd']:.0f}", f"{b_t['sd']:.0f}")

    console.print(table)
    console.print()

    console.print("[bold]3. Latency[/]")
    table = Table()
    table.add_column("Metric")
    table.add_column(model_a, justify="right")
    table.add_column(model_b, justify="right")

    a_l, b_l = latency["a"], latency["b"]
    table.add_row("Mean (ms)", str(a_l["mean"]), str(b_l["mean"]))
    table.add_row("Median (ms)", str(a_l["median"]), str(b_l["median"]))
    table.add_row("SD (ms)", str(a_l["sd"]), str(b_l["sd"]))
    table.add_row("P5-P95 (ms)", f"{a_l['p5']}-{a_l['p95']}", f"{b_l['p5']}-{b_l['p95']}")

    console.print(table)
    console.print(
        f"  Diff: {latency['diff_mean_ms']:+d}ms mean, "
        f"{latency['diff_median_ms']:+d}ms median"
    )
    console.print()

    console.print("[bold]4. Reliability[/]")
    table = Table()
    table.add_column("Metric")
    table.add_column(model_a, justify="right")
    table.add_column(model_b, justify="right")

    a_r, b_r = rel["a"], rel["b"]
    table.add_row("Requests", str(a_r["n"]), str(b_r["n"]))
    table.add_row("Total retries", str(a_r["total_retries"]), str(b_r["total_retries"]))
    table.add_row("Requests w/ retries", str(a_r["requests_with_retries"]),
                  str(b_r["requests_with_retries"]))
    table.add_row("Retry rate", f"{a_r['retry_rate_pct']}%", f"{b_r['retry_rate_pct']}%")
    table.add_row("Max retries", str(a_r["max_retries"]), str(b_r["max_retries"]))

    console.print(table)
    console.print()

    console.print(f"Report: {report['_paths']['report']}")
    console.print(f"Chart:  {report['_paths']['chart']}")
