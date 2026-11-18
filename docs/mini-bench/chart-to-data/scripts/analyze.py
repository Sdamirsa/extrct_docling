# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Score every model run of the chart-to-data mini bench against the truth.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/analyze.py

Reads ``truth/*.json`` and ``runs/<model>/**`` (figure-data JSON plus the
``timing.json`` of each part) and writes ``metrics/per_figure.csv``,
``metrics/metrics.json`` and ``metrics/summary.md``. Scoring is the engine's
own (:func:`docling.engines.figure_data.scoring.score_figure`): a predicted
value matches a truth value of the same panel, series and category, and
counts as a hit when it is within 2 % / 5 % of the panel's axis range.

Two scorings are reported. *Strict* is the scorer as it is. *Lenient*
(``*_lenient`` columns) first renames the prediction's series to the truth's
in every panel whose truth has a single series: such a series has no legend
entry, the truth names it after the axis or the title, and a model that
calls it something else has read the same numbers.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from statistics import median

from docling.engines.figure_data.schema import SCHEMA_ID, ChartData
from docling.engines.figure_data.scoring import match_panels, score_figure

BENCH = Path(__file__).resolve().parents[1]
# A later round keeps its runs, metrics and judge files in its own folder
# (BENCH_ROUND=round-2); the figures, the test set and the truth are shared.
ROUND = BENCH / os.environ.get("BENCH_ROUND", "")
FIELDS = [
    "model", "figure_id", "bundle", "self_ref", "has_data", "predicted",
    "truth_panels", "pred_panels", "panels_matched", "kind_matches",
    "series_f1", "category_f1", "truth_values", "pred_values", "matched_values",
    "missing_values", "extra_values", "hits_02", "hits_05", "mean_norm_error",
    "printed_mape", "matched_lenient", "hits_02_lenient", "hits_05_lenient",
    "mean_norm_error_lenient", "seconds", "gpu_gb", "eval_tokens",
]  # fmt: skip


def series_lenient(truth: ChartData, pred: ChartData) -> ChartData:
    """*pred* with the series of every panel whose truth has one series
    renamed to that series."""
    lenient = pred.model_copy(deep=True)
    for truth_panel, pred_panel in match_panels(truth.panels, lenient.panels):
        names = {value.series for value in truth_panel.data}
        if len(names) == 1:
            for value in pred_panel.data:
                value.series = next(iter(names))
    return lenient


def load_charts(folder: Path) -> dict[tuple[str, str], ChartData]:
    charts: dict[tuple[str, str], ChartData] = {}
    for path in sorted(folder.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema") == SCHEMA_ID:
            chart = ChartData.model_validate(data)
            if chart.figure is not None:
                charts[Path(chart.figure.bundle).name, chart.figure.self_ref] = chart
    return charts


def load_timing(folder: Path) -> dict[tuple[str, str], dict]:
    timing: dict[tuple[str, str], dict] = {}
    for path in sorted(folder.rglob("timing.json")):
        for row in json.loads(path.read_text(encoding="utf-8")):
            if "self_ref" in row:
                timing[Path(row["bundle"]).name, row["self_ref"]] = row
    return timing


def ratio(part: float, whole: float) -> float | None:
    return round(part / whole, 4) if whole else None


def main() -> None:
    testset = json.loads((BENCH / "testset.json").read_text(encoding="utf-8"))
    ids = {(Path(f["bundle"]).name, f["self_ref"]): f["id"] for f in testset["figures"]}
    truth = load_charts(BENCH / "truth")
    rows: list[dict] = []
    summary: dict[str, dict] = {}
    for model_dir in sorted(p for p in (ROUND / "runs").iterdir() if p.is_dir()):
        preds, timing = load_charts(model_dir), load_timing(model_dir)
        model_rows = []
        for key, chart in sorted(truth.items(), key=lambda kv: ids.get(kv[0], "")):
            pred = preds.get(key)
            score = score_figure(chart, pred or ChartData(), name=ids.get(key, ""))
            lenient = score_figure(
                chart, series_lenient(chart, pred) if pred else ChartData()
            )
            clock = timing.get(key, {})
            model_rows.append(
                {
                    "model": model_dir.name,
                    "figure_id": ids.get(key, ""),
                    "bundle": key[0],
                    "self_ref": key[1],
                    "has_data": any(panel.data for panel in chart.panels),
                    "predicted": pred is not None,
                    **{
                        name: getattr(score, name)
                        for name in FIELDS
                        if name in type(score).model_fields
                    },
                    "matched_lenient": lenient.matched_values,
                    "hits_02_lenient": lenient.hits_02,
                    "hits_05_lenient": lenient.hits_05,
                    "mean_norm_error_lenient": lenient.mean_norm_error,
                    "seconds": clock.get("seconds"),
                    "gpu_gb": round(clock["gpu_bytes"] / 1e9, 1)
                    if clock.get("gpu_bytes")
                    else None,
                    "eval_tokens": clock.get("eval_tokens"),
                }
            )
        rows += model_rows
        data = [r for r in model_rows if r["has_data"]]
        empty = [r for r in model_rows if not r["has_data"]]
        truth_values = sum(r["truth_values"] for r in data)
        matched = sum(r["matched_values"] for r in data)
        errors = [
            (r["mean_norm_error"], r["matched_values"])
            for r in data
            if r["mean_norm_error"] is not None and r["matched_values"]
        ]
        seconds = [r["seconds"] for r in model_rows if r["seconds"] is not None]
        summary[model_dir.name] = {
            "figures_run": sum(1 for r in model_rows if r["predicted"]),
            "data_figures": len(data),
            "truth_values": truth_values,
            "pred_values": sum(r["pred_values"] for r in data),
            "matched_values": matched,
            "value_recall": ratio(matched, truth_values),
            "value_precision": ratio(matched, sum(r["pred_values"] for r in data)),
            "within_2pct_of_truth": ratio(
                sum(r["hits_02"] for r in data), truth_values
            ),
            "within_5pct_of_truth": ratio(
                sum(r["hits_05"] for r in data), truth_values
            ),
            "within_5pct_of_matched": ratio(sum(r["hits_05"] for r in data), matched),
            "matched_lenient": sum(r["matched_lenient"] for r in data),
            "within_2pct_of_truth_lenient": ratio(
                sum(r["hits_02_lenient"] for r in data), truth_values
            ),
            "within_5pct_of_truth_lenient": ratio(
                sum(r["hits_05_lenient"] for r in data), truth_values
            ),
            "data_figures_with_half_within_5pct_lenient": sum(
                1
                for r in data
                if r["truth_values"] and r["hits_05_lenient"] >= 0.5 * r["truth_values"]
            ),
            "mean_norm_error": round(
                sum(e * n for e, n in errors) / sum(n for _e, n in errors), 4
            )
            if errors
            else None,
            "panel_recall": ratio(
                sum(r["panels_matched"] for r in data),
                sum(r["truth_panels"] for r in data),
            ),
            "kind_accuracy": ratio(
                sum(r["kind_matches"] for r in data),
                sum(r["panels_matched"] for r in data),
            ),
            "no_data_figures": len(empty),
            "no_data_figures_with_values": sum(1 for r in empty if r["pred_values"]),
            "values_on_no_data_figures": sum(r["pred_values"] for r in empty),
            "seconds_total": round(sum(seconds), 1) if seconds else None,
            "seconds_median_per_figure": round(median(seconds), 1) if seconds else None,
            "seconds_max_figure": round(max(seconds), 1) if seconds else None,
            "seconds_on_no_data_figures": round(
                sum(r["seconds"] or 0 for r in empty), 1
            ),
            "gpu_gb": max((r["gpu_gb"] or 0 for r in model_rows), default=None),
        }

    metrics = ROUND / "metrics"
    metrics.mkdir(exist_ok=True)
    with (metrics / "per_figure.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (metrics / "metrics.json").write_text(
        json.dumps({"models": summary, "per_figure": rows}, indent=1), encoding="utf-8"
    )
    head = (
        "| model | matched / truth (strict) | within 5 % (strict) | matched (lenient) "
        "| within 2 % (lenient) | within 5 % (lenient) | figures >= half right | kind ok "
        "| values on no-data figures | total s | median s / figure | GPU GB |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = [
        f"| {name} | {m['matched_values']} / {m['truth_values']} "
        f"| {pct(m['within_5pct_of_truth'])} | {m['matched_lenient']} "
        f"| {pct(m['within_2pct_of_truth_lenient'])} "
        f"| {pct(m['within_5pct_of_truth_lenient'])} "
        f"| {m['data_figures_with_half_within_5pct_lenient']} of {m['data_figures']} "
        f"| {pct(m['kind_accuracy'])} | {m['values_on_no_data_figures']} in "
        f"{m['no_data_figures_with_values']} of {m['no_data_figures']} "
        f"| {m['seconds_total']} | {m['seconds_median_per_figure']} | {m['gpu_gb']} |"
        for name, m in summary.items()
    ]
    (metrics / "summary.md").write_text(
        head + "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(head + "\n".join(lines))


def pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


if __name__ == "__main__":
    main()
