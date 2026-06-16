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


# generate-suite

@cli.command("generate-suite")
@click.option(
    "--thinking", "thinking_levels", multiple=True,
    type=click.Choice(["minimal", "low", "medium", "high"]),
    default=("low", "medium", "high"),
    help="Thinking levels to run (repeatable). Default: low, medium, high.",
)
@click.option(
    "--variants", multiple=True,
    help="Variant names (default: all six).",
)
@click.option("--cases", type=int, default=None, help="Limit to first N cases.")
@click.option(
    "--force", is_flag=True, default=False,
    help="Re-run pairs whose output files already exist (default: skip).",
)
def generate_suite(
    thinking_levels: tuple[str, ...],
    variants: tuple[str, ...],
    cases: int | None,
    force: bool,
):
    """Loop generate over (thinking_level, variant) pairs.

    Names each exec_id as f"{thinking}_{suffix}" where suffix is the
    canonical variant index (1=flat_alpha .. 6=nested_narrative). This is
    the file naming the analyzer expects. Idempotent by default: pairs
    whose raw output already exists are skipped unless --force is passed.
    """
    from .analysis.load import VARIANT_MAP, VARIANT_SUFFIX
    from .run import run_variants

    all_cases = json.loads(paths.cases_path().read_text())
    if cases:
        all_cases = all_cases[:cases]

    if variants:
        unknown = set(variants) - set(VARIANT_SUFFIX)
        if unknown:
            raise click.BadParameter(f"Unknown variants: {sorted(unknown)}")
        selected_variants = [v for v in VARIANT_MAP.values() if v in set(variants)]
    else:
        selected_variants = list(VARIANT_MAP.values())

    pairs: list[tuple[str, str, str]] = []  # (thinking, suffix, variant)
    for thinking in thinking_levels:
        for variant in selected_variants:
            suffix = VARIANT_SUFFIX[variant]
            pairs.append((thinking, suffix, variant))

    skipped: list[str] = []
    to_run: list[tuple[str, str, str]] = []
    for thinking, suffix, variant in pairs:
        exec_id = f"{thinking}_{suffix}"
        existing = list(paths.raw_dir().glob(f"{exec_id}_*.json"))
        if existing and not force:
            skipped.append(f"{exec_id} ({variant})")
        else:
            to_run.append((thinking, suffix, variant))

    if skipped:
        console.print(f"[yellow]Skipping {len(skipped)} existing pair(s):[/] "
                      + ", ".join(skipped))

    if not to_run:
        console.print("[green]Nothing to do.[/]")
        return

    total_calls = len(to_run) * len(all_cases)
    console.print(
        f"[bold]Running {len(to_run)} pair(s), {total_calls} generations[/]"
    )

    grand_total = 0
    for i, (thinking, suffix, variant) in enumerate(to_run, 1):
        exec_id = f"{thinking}_{suffix}"
        console.print(
            f"\n[bold cyan]({i}/{len(to_run)}) {exec_id}[/] — "
            f"{variant} @ thinking={thinking}"
        )

        with Progress(
            SpinnerColumn(), TextColumn("[bold]{task.description}"),
            BarColumn(), MofNCompleteColumn(), console=console,
        ) as progress:
            task = progress.add_task(exec_id, total=0)

            def on_progress(current: int, total: int, label: str) -> None:
                progress.update(task, total=total, completed=current, description=label)

            n = run_variants(exec_id, all_cases, [variant], thinking, on_progress)
            grand_total += n

    console.print(
        f"\n[green]{grand_total} total generations[/] saved to {paths.raw_dir()}"
    )


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


THINKING_CHOICES = ["minimal", "low", "medium", "high"]


@analyze.command("variants")
@click.option(
    "--thinking", type=click.Choice(THINKING_CHOICES), default="minimal",
    help="Thinking level to analyze.",
)
@click.option("--variants", multiple=True, help="Variant names (default: all six).")
@click.option(
    "--reference", default="nested_narrative",
    help="Reference variant for paired comparisons.",
)
@click.option(
    "--comparator", multiple=True,
    help="Comparator variants for paired comparisons (default: flat_alpha, ui_contract, "
         "alpha_nested).",
)
@click.option(
    "--striking-pair", nargs=2, default=("nested_narrative", "flat_alpha"),
    metavar="VARIANT_A VARIANT_B",
    help="Two variants to dump striking-case diffs for.",
)
@click.option(
    "--expected-n", type=int, default=64,
    help="Expected case count per variant. Pass 0 to skip the check.",
)
def analyze_variants(
    thinking: str, variants: tuple[str, ...], reference: str,
    comparator: tuple[str, ...], striking_pair: tuple[str, str], expected_n: int,
):
    """Full analysis of the schema variant experiment at one thinking level."""
    from .analysis.chart import run as run_chart
    from .analysis.paired import DEFAULT_COMPARATORS
    from .analysis.paired import run as run_paired
    from .analysis.striking import run as run_striking
    from .analysis.summary import run as run_summary

    variant_list = list(variants) if variants else None
    comparators = list(comparator) if comparator else list(DEFAULT_COMPARATORS)
    expected = expected_n if expected_n > 0 else None

    console.print(f"[bold]Summary statistics[/] (thinking={thinking})")
    df = run_summary(thinking, variant_list, expected_n=expected)
    table = Table()
    for col in df.columns:
        table.add_column(col, justify="right" if col != "variant" else "left")
    for _, row in df.iterrows():
        table.add_row(*[str(v) for v in row])
    console.print(table)
    console.print(f"  -> {paths.analysis_dir() / f'01_summary_stats_{thinking}.csv'}")
    console.print()

    console.print("[bold]Paired comparisons[/]")
    summaries = run_paired(thinking, reference, comparators)
    for s in summaries:
        console.print(
            f"  {s['pair']}: {s['mean_diff']:+.4f} "
            f"({s['reference_wins']}-{s['comparator_wins']}-{s['ties']})"
        )
    console.print()

    console.print("[bold]Striking pairs[/]")
    a, b = striking_pair
    top = run_striking(thinking, a, b)
    for cid, diff in top:
        console.print(f"  {cid}: {diff:+.2f}")
    console.print()

    console.print("[bold]Chart[/]")
    out_path = run_chart(thinking, variant_list, expected_n=expected)
    console.print(f"  -> {out_path}")

    console.print(f"\n[green]All outputs written to {paths.analysis_dir()}[/]")


@analyze.command("thinking")
@click.option(
    "--level", "levels", multiple=True, type=click.Choice(THINKING_CHOICES),
    default=("minimal", "low", "medium"),
    help="Thinking levels to compare (repeatable).",
)
@click.option(
    "--variants", multiple=True,
    default=("flat_alpha", "nested_narrative"),
    help="Variants to compare across thinking levels (repeatable).",
)
@click.option(
    "--baseline", type=click.Choice(THINKING_CHOICES), default="minimal",
    help="Baseline thinking level for per-case deltas.",
)
@click.option(
    "--failure-mode-report", is_flag=True, default=False,
    help="Also generate 04_failure_mode_{level}.md for each non-baseline level.",
)
@click.option(
    "--failure-target", default="flat_alpha", show_default=True,
    help="Variant whose baseline failures to track for --failure-mode-report.",
)
@click.option(
    "--failure-reference", default="nested_narrative", show_default=True,
    help="Variant shown for context in failure-mode markdown.",
)
@click.option(
    "--failure-baseline-threshold", type=float, default=3.5, show_default=True,
    help="Cases scoring below this at baseline count as 'failing'.",
)
@click.option(
    "--failure-fixed-threshold", type=float, default=4.0, show_default=True,
    help="Failing cases that reach this at a new level count as 'fixed'.",
)
def analyze_thinking(
    levels: tuple[str, ...], variants: tuple[str, ...], baseline: str,
    failure_mode_report: bool, failure_target: str, failure_reference: str,
    failure_baseline_threshold: float, failure_fixed_threshold: float,
):
    """Compare variant(s) across thinking levels.

    The core follow-up: does turning on thinking compensate for poor schema order?
    """
    from .analysis import thinking as thinking_mod

    report = thinking_mod.run(list(levels), list(variants), baseline=baseline)

    summary = report["summary"]
    table = Table(title="Per-variant × thinking-level summary")
    for col in ["variant", "thinking_level", "n", "weighted_mean",
                "weighted_sd", "mean_latency_ms", "mean_thinking_tokens"]:
        table.add_column(col, justify="right" if col != "variant" else "left")
    for _, row in summary.iterrows():
        table.add_row(
            row["variant"], row["thinking_level"], str(row["n"]),
            f"{row['weighted_mean']:.3f}", f"{row['weighted_sd']:.3f}",
            str(row["mean_latency_ms"]), str(row["mean_thinking_tokens"]),
        )
    console.print(table)
    console.print()

    if report["deltas"]:
        console.print(f"[bold]Per-case deltas vs {baseline}[/]")
        for d in report["deltas"]:
            console.print(
                f"  {d['variant']} {d['comparison']}: "
                f"mean {d['mean_diff']:+.4f} "
                f"({d['level_wins']}-{d['baseline_wins']}-{d['ties']})"
            )
        console.print()

    console.print(f"Summary:          {report['_paths']['summary']}")
    console.print(f"Deltas:           {report['_paths']['deltas']}")
    console.print(f"Chart:            {report['_paths']['chart']}")
    console.print(f"Cost-per-quality: {report['_paths']['cost_per_quality']}")
    console.print(f"Criterion lift:   {report['_paths']['criterion_lift']}")

    if failure_mode_report:
        non_baseline = [lvl for lvl in levels if lvl != baseline]
        console.print()
        console.print(f"[bold]Failure-mode pull[/] ({failure_target} @ {baseline} → new levels)")
        fm = thinking_mod.failure_mode_report(
            target_variant=failure_target,
            reference_variant=failure_reference,
            new_levels=non_baseline,
            baseline=baseline,
            baseline_threshold=failure_baseline_threshold,
            fixed_threshold=failure_fixed_threshold,
        )
        for level, counts in fm["counts"].items():
            console.print(
                f"  {level}: fixed={counts['fixed']} "
                f"improved={counts['improved']} "
                f"still_broken={counts['still_broken']} "
                f"(of {counts['matched']} matched / "
                f"{counts['total_failing_at_baseline']} failing at baseline)"
            )
        for level, path in fm["paths"].items():
            console.print(f"  {level} report: {path}")


@analyze.command("reachability")
def analyze_reachability():
    """Per-encounter weakness-reachability rates × condition (uses reachability_*.json)."""
    import pandas as pd

    from .analysis.reachability import run as run_reachability

    report = run_reachability()
    wide = report["wide"]

    table = Table(title="Encounter break rate (%) by variant × condition")
    table.add_column("variant")
    for col in wide.columns:
        table.add_column(col, justify="right")
    for variant, row in wide.iterrows():
        cells = [variant]
        for col in wide.columns:
            v = row[col]
            cells.append("—" if pd.isna(v) else f"{v:.1f}")
        table.add_row(*cells)

    console.print(table)
    console.print()
    console.print(f"Wide CSV: {report['_paths']['wide']}")
    console.print(f"Long CSV: {report['_paths']['long']}")
    console.print(f"Chart:    {report['_paths']['chart']}")


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
