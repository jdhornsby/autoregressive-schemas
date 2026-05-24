"""Model head-to-head analysis: scoring, tokens, latency, reliability."""

from __future__ import annotations

import json
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..paths import analysis_dir, judgments_dir, raw_dir
from ..rubric import WEIGHTS, case_id

TOTAL_WEIGHT = sum(WEIGHTS.values())
CRITERIA = list(WEIGHTS.keys())


def _weighted(scores: dict) -> float:
    return sum(scores[c]["score"] * WEIGHTS[c] for c in WEIGHTS) / TOTAL_WEIGHT


def _load_raw(prefix: str) -> list[dict]:
    entries: list[dict] = []
    for f in sorted(raw_dir().glob(f"{prefix}_*.json")):
        entries.extend(json.loads(f.read_text()))
    return entries


def _load_judgments(prefix: str) -> dict[str, list[dict]]:
    by_case: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(judgments_dir().glob(f"{prefix}_*.json")):
        for row in json.loads(f.read_text()):
            cid = case_id(row["case"])
            by_case[cid].append(row["judgment"])
    return dict(by_case)


def _stats(vals: list[float]) -> dict:
    a = np.array(vals)
    return {
        "mean": round(float(np.mean(a)), 1),
        "median": round(float(np.median(a)), 1),
        "sd": round(float(np.std(a, ddof=1)), 1) if len(a) > 1 else 0.0,
        "min": int(np.min(a)),
        "max": int(np.max(a)),
    }


def _stats_with_percentiles(vals: list[float]) -> dict:
    s = _stats(vals)
    a = np.array(vals)
    s["p5"] = round(float(np.percentile(a, 5)))
    s["p95"] = round(float(np.percentile(a, 95)))
    s["n"] = len(vals)
    # round mean/median to int for latency
    s["mean"] = round(s["mean"])
    s["median"] = round(s["median"])
    s["sd"] = round(s["sd"])
    return s


# Scoring

def _scoring_analysis(judgments_a, judgments_b, shared):
    criteria = {}
    for c in CRITERIA:
        a_vals = [j["scores"][c]["score"] for cid in shared for j in judgments_a[cid]]
        b_vals = [j["scores"][c]["score"] for cid in shared for j in judgments_b[cid]]
        a_mean, b_mean = round(np.mean(a_vals), 3), round(np.mean(b_vals), 3)
        criteria[c] = {
            "weight": WEIGHTS[c],
            "a_mean": float(a_mean),
            "b_mean": float(b_mean),
            "diff": round(float(a_mean - b_mean), 3),
        }

    a_weighted = [_weighted(j["scores"]) for cid in shared for j in judgments_a[cid]]
    b_weighted = [_weighted(j["scores"]) for cid in shared for j in judgments_b[cid]]

    a_wins = b_wins = ties = 0
    for cid in shared:
        a_m = np.mean([_weighted(j["scores"]) for j in judgments_a[cid]])
        b_m = np.mean([_weighted(j["scores"]) for j in judgments_b[cid]])
        if a_m > b_m:
            a_wins += 1
        elif b_m > a_m:
            b_wins += 1
        else:
            ties += 1

    return {
        "a_mean": round(float(np.mean(a_weighted)), 3),
        "b_mean": round(float(np.mean(b_weighted)), 3),
        "diff": round(float(np.mean(a_weighted) - np.mean(b_weighted)), 3),
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "criteria": criteria,
    }


# Tokens

def _token_analysis(raw_a, raw_b):
    result = {}
    for field in ["prompt_tokens", "output_tokens", "thinking_tokens"]:
        result[field] = {
            "a": _stats([e["stats"][field] for e in raw_a]),
            "b": _stats([e["stats"][field] for e in raw_b]),
        }
    return result


# Latency

def _latency_analysis(raw_a, raw_b):
    a_lat = [e["stats"]["latency_ms"] for e in raw_a]
    b_lat = [e["stats"]["latency_ms"] for e in raw_b]
    return {
        "a": _stats_with_percentiles(a_lat),
        "b": _stats_with_percentiles(b_lat),
        "diff_mean_ms": round(float(np.mean(a_lat) - np.mean(b_lat))),
        "diff_median_ms": round(float(np.median(a_lat) - np.median(b_lat))),
    }


# Reliability

def _reliability_analysis(raw_a, raw_b):
    def summarize(entries):
        retries = [e["stats"]["retries"] for e in entries]
        n = len(entries)
        with_retries = sum(1 for r in retries if r > 0)
        return {
            "n": n,
            "total_retries": sum(retries),
            "requests_with_retries": with_retries,
            "retry_rate_pct": round(100 * with_retries / n, 1) if n else 0,
            "mean_retries": round(float(np.mean(retries)), 2),
            "max_retries": max(retries) if retries else 0,
        }

    return {"a": summarize(raw_a), "b": summarize(raw_b)}


# Chart

def _make_chart(report, model_a, model_b, raw_a, raw_b, out_path):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    a_color, b_color = "#2d5a87", "#d4a055"
    label_a = model_a.replace("flash_v1_", "").replace("_", " ")
    label_b = model_b.replace("flash_v1_", "").replace("_", " ")

    # Scoring
    ax = axes[0, 0]
    scoring = report["scoring"]
    labels = [c.replace("_", "\n") for c in CRITERIA]
    a_vals = [scoring["criteria"][c]["a_mean"] for c in CRITERIA]
    b_vals = [scoring["criteria"][c]["b_mean"] for c in CRITERIA]
    x = np.arange(len(labels))
    w = 0.35
    ax.bar(x - w / 2, a_vals, w, label=label_a, color=a_color)
    ax.bar(x + w / 2, b_vals, w, label=label_b, color=b_color)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, 5.5)
    ax.set_ylabel("Mean Score (1-5)")
    ax.set_title(
        f"Rubric Scores  ({label_a} {scoring['a_mean']:.2f} vs "
        f"{label_b} {scoring['b_mean']:.2f})",
        fontsize=10, fontweight="bold",
    )
    ax.legend(fontsize=8)
    ax.yaxis.grid(True, color="#e0e0e0", linewidth=0.5)
    ax.set_axisbelow(True)

    # Output tokens
    ax = axes[0, 1]
    ax.hist([e["stats"]["output_tokens"] for e in raw_a],
            bins=25, alpha=0.7, label=label_a, color=a_color)
    ax.hist([e["stats"]["output_tokens"] for e in raw_b],
            bins=25, alpha=0.7, label=label_b, color=b_color)
    ax.set_xlabel("Output Tokens")
    ax.set_ylabel("Frequency")
    ax.set_title("Output Token Distribution", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)

    # Latency
    ax = axes[1, 0]
    ax.hist([e["stats"]["latency_ms"] for e in raw_a],
            bins=30, alpha=0.7, label=label_a, color=a_color)
    ax.hist([e["stats"]["latency_ms"] for e in raw_b],
            bins=30, alpha=0.7, label=label_b, color=b_color)
    ax.set_xlabel("Latency (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title("Latency Distribution", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)

    # Reliability
    ax = axes[1, 1]
    rel = report["reliability"]
    categories = ["Success Rate %", "Mean Retries", "Max Retries"]
    a_rel = [100 - rel["a"]["retry_rate_pct"], rel["a"]["mean_retries"], rel["a"]["max_retries"]]
    b_rel = [100 - rel["b"]["retry_rate_pct"], rel["b"]["mean_retries"], rel["b"]["max_retries"]]
    x = np.arange(len(categories))
    ax.bar(x - w / 2, a_rel, w, label=label_a, color=a_color)
    ax.bar(x + w / 2, b_rel, w, label=label_b, color=b_color)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_title("Reliability", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)

    for a in axes.flat:
        a.spines["top"].set_visible(False)
        a.spines["right"].set_visible(False)

    fig.suptitle(
        f"Model Comparison: {label_a} vs {label_b}",
        fontsize=13, fontweight="bold", y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# Public API

def run(model_a: str, model_b: str) -> dict:
    """Run full model comparison. Returns the report dict."""
    raw_a = _load_raw(model_a)
    raw_b = _load_raw(model_b)

    if not raw_a:
        raise FileNotFoundError(f"No raw files for {model_a}")
    if not raw_b:
        raise FileNotFoundError(f"No raw files for {model_b}")

    judgments_a = _load_judgments(model_a)
    judgments_b = _load_judgments(model_b)
    shared = sorted(set(judgments_a) & set(judgments_b))

    report = {
        "model_a": model_a,
        "model_b": model_b,
        "n_raw_a": len(raw_a),
        "n_raw_b": len(raw_b),
        "n_judged_cases": len(shared),
        "scoring": _scoring_analysis(judgments_a, judgments_b, shared),
        "tokens": _token_analysis(raw_a, raw_b),
        "latency": _latency_analysis(raw_a, raw_b),
        "reliability": _reliability_analysis(raw_a, raw_b),
    }

    out = analysis_dir()
    out.mkdir(parents=True, exist_ok=True)

    tag = f"{model_a}_vs_{model_b}"
    report_path = out / f"{tag}_report.json"
    report_path.write_text(json.dumps(report, indent=2))

    chart_path = str(out / f"{tag}_chart.png")
    _make_chart(report, model_a, model_b, raw_a, raw_b, chart_path)

    report["_paths"] = {"report": str(report_path), "chart": chart_path}
    return report
