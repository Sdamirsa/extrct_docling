# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Score predicted chart data against ground truth (both
``extrct.figure-data/1``).

Per figure: panels match one-to-one by box IoU ≥ 0.5 (a single panel on
both sides always matches); per matched panel the kind, series and
categories are compared (strings normalised, equal when their Levenshtein
distance is ≤ 0.2 of the longer), values are matched by (category or x,
series) and scored as the axis-normalised error ``|pred - true| / range``
(range: the truth's value axis, else the truth values' span) with hits at
≤ 0.02 and ≤ 0.05; values printed in the figure (truth ``label_printed`` or
source ``printed``) also give a MAPE; missing and extra values are counted.
Totals add up per prediction source; ``timing.json`` of a prediction folder
(written by ``amir-figdata run``) adds wall time and GPU memory per figure.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

from docling.engines.figure_data.evidence import normalise_label, same_label
from docling.engines.figure_data.schema import SCHEMA_ID, ChartData, Panel, Value
from docling.engines.figure_data.verify import axis_span

PANEL_IOU = 0.5
HIT_TIGHT = 0.02
HIT_LOOSE = 0.05


class ValueTotals(BaseModel):
    matched: int = 0
    hits_02: int = 0
    hits_05: int = 0
    error_sum: float = 0.0
    printed: int = 0
    printed_ape_sum: float = 0.0


class FigureScore(BaseModel):
    figure: str
    truth_panels: int
    pred_panels: int
    panels_matched: int
    panel_precision: float
    panel_recall: float
    kind_matches: int
    series_f1: float | None = None
    category_f1: float | None = None
    truth_values: int = 0
    pred_values: int = 0
    matched_values: int = 0
    missing_values: int = 0
    extra_values: int = 0
    hits_02: int = 0
    hits_05: int = 0
    mean_norm_error: float | None = None
    printed_mape: float | None = None
    by_source: dict[str, ValueTotals] = Field(default_factory=dict)
    seconds: float | None = None
    gpu_bytes: int | None = None


class ScoreReport(BaseModel):
    figures: list[FigureScore]
    totals: dict[str, float | int | None]
    by_source: dict[str, dict[str, float | int | None]]


def score_figure(truth: ChartData, pred: ChartData, name: str = "") -> FigureScore:
    pairs = match_panels(truth.panels, pred.panels)
    totals = ValueTotals()
    by_source: dict[str, ValueTotals] = defaultdict(ValueTotals)
    kind_matches = 0
    series_f1: list[float] = []
    category_f1: list[float] = []
    truth_values = sum(len(p.data) for p in truth.panels)
    pred_values = sum(len(p.data) for p in pred.panels)
    matched_rows = 0
    for t_panel, p_panel in pairs:
        kind_matches += t_panel.kind == p_panel.kind
        truth_series = {s.name for s in t_panel.series} | {
            v.series for v in t_panel.data if v.series
        }
        if truth_series:
            series_f1.append(
                _f1(
                    truth_series,
                    {s.name for s in p_panel.series}
                    | {v.series for v in p_panel.data if v.series},
                )
            )
        category_f1.append(
            _f1(
                {_row_key(v) for v in t_panel.data}, {_row_key(v) for v in p_panel.data}
            )
        )
        span = axis_span(t_panel)
        width = (span[1] - span[0]) if span else None
        matches = _match_values(t_panel.data, p_panel.data)
        matched_rows += len(matches)
        for t_value, p_value in matches:
            if t_value.value is None or p_value.value is None:
                continue
            error = abs(p_value.value - t_value.value) / (
                width or max(abs(t_value.value), 1e-9)
            )
            source = by_source[p_value.source or "unknown"]
            for bucket in (totals, source):
                bucket.matched += 1
                bucket.error_sum += error
                bucket.hits_02 += error <= HIT_TIGHT
                bucket.hits_05 += error <= HIT_LOOSE
                if t_value.label_printed is not None or t_value.source == "printed":
                    bucket.printed += 1
                    bucket.printed_ape_sum += abs(p_value.value - t_value.value) / max(
                        abs(t_value.value), 1e-9
                    )
    return FigureScore(
        figure=name,
        truth_panels=len(truth.panels),
        pred_panels=len(pred.panels),
        panels_matched=len(pairs),
        panel_precision=round(len(pairs) / len(pred.panels), 3) if pred.panels else 0.0,
        panel_recall=round(len(pairs) / len(truth.panels), 3) if truth.panels else 0.0,
        kind_matches=kind_matches,
        series_f1=_mean(series_f1),
        category_f1=_mean(category_f1),
        truth_values=truth_values,
        pred_values=pred_values,
        matched_values=matched_rows,
        missing_values=truth_values - matched_rows,
        extra_values=pred_values - matched_rows,
        hits_02=totals.hits_02,
        hits_05=totals.hits_05,
        mean_norm_error=round(totals.error_sum / totals.matched, 4)
        if totals.matched
        else None,
        printed_mape=round(totals.printed_ape_sum / totals.printed, 4)
        if totals.printed
        else None,
        by_source=dict(by_source),
    )


def match_panels(truth: list[Panel], pred: list[Panel]) -> list[tuple[Panel, Panel]]:
    if len(truth) == 1 and len(pred) == 1:
        return [(truth[0], pred[0])]
    candidates = sorted(
        (
            (_iou(t.bbox_px, p.bbox_px), i, j)
            for i, t in enumerate(truth)
            for j, p in enumerate(pred)
        ),
        reverse=True,
    )
    used_t: set[int] = set()
    used_p: set[int] = set()
    pairs: list[tuple[Panel, Panel]] = []
    for iou, i, j in candidates:
        if iou < PANEL_IOU:
            break
        if i in used_t or j in used_p:
            continue
        used_t.add(i)
        used_p.add(j)
        pairs.append((truth[i], pred[j]))
    return pairs


def score_dirs(truth_dir: Path, pred_dir: Path) -> ScoreReport:
    """Score every truth file of *truth_dir* against the prediction for the
    same figure (bundle name + self_ref) found under *pred_dir*."""
    preds = {_figure_key(c): c for c in _load_charts(pred_dir)}
    timing = _load_timing(pred_dir)
    scores: list[FigureScore] = []
    for truth in _load_charts(truth_dir):
        key = _figure_key(truth)
        pred = preds.get(key)
        score = score_figure(truth, pred or ChartData(), name=f"{key[0]} {key[1]}")
        if key in timing:
            score.seconds, score.gpu_bytes = timing[key]
        scores.append(score)
    return ScoreReport(
        figures=scores, totals=_totals(scores), by_source=_source_totals(scores)
    )


def markdown_report(report: ScoreReport) -> str:
    header = (
        "| figure | panels t/p/m | kind | series F1 | cat F1 | values t/p/m "
        "| ≤.02 | ≤.05 | mean err | printed MAPE | s | GPU GB |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    lines = [header]
    for s in report.figures:
        lines.append(
            f"| {s.figure} | {s.truth_panels}/{s.pred_panels}/{s.panels_matched} "
            f"| {s.kind_matches}/{s.panels_matched} | {_fmt(s.series_f1)} "
            f"| {_fmt(s.category_f1)} | {s.truth_values}/{s.pred_values}/{s.matched_values} "
            f"| {s.hits_02} | {s.hits_05} | {_fmt(s.mean_norm_error)} "
            f"| {_fmt(s.printed_mape)} | {_fmt(s.seconds)} "
            f"| {_fmt(s.gpu_bytes / 1e9 if s.gpu_bytes else None)} |"
        )
    t = report.totals
    lines.append(
        f"| **total** | {t['truth_panels']}/{t['pred_panels']}/{t['panels_matched']} "
        f"| | | | {t['truth_values']}/{t['pred_values']}/{t['matched_values']} "
        f"| {t['hits_02']} | {t['hits_05']} | {_fmt(t['mean_norm_error'])} "
        f"| {_fmt(t['printed_mape'])} | {_fmt(t['seconds'])} | |"
    )
    if report.by_source:
        lines.append(
            "\n| source | matched | ≤.02 | ≤.05 | mean err |\n|---|---|---|---|---|"
        )
        for source, row in sorted(report.by_source.items()):
            lines.append(
                f"| {source} | {row['matched']} | {row['hits_02']} | {row['hits_05']} "
                f"| {_fmt(row['mean_norm_error'])} |"
            )
    return "\n".join(lines) + "\n"


def _totals(scores: list[FigureScore]) -> dict[str, float | int | None]:
    def total(field: str) -> int:
        return sum(getattr(s, field) for s in scores)

    matched = sum(sum(v.matched for v in s.by_source.values()) for s in scores)
    error_sum = sum(sum(v.error_sum for v in s.by_source.values()) for s in scores)
    printed = sum(sum(v.printed for v in s.by_source.values()) for s in scores)
    ape = sum(sum(v.printed_ape_sum for v in s.by_source.values()) for s in scores)
    seconds = [s.seconds for s in scores if s.seconds is not None]
    return {
        **{
            f: total(f)
            for f in (
                "truth_panels",
                "pred_panels",
                "panels_matched",
                "truth_values",
                "pred_values",
                "matched_values",
                "missing_values",
                "extra_values",
                "hits_02",
                "hits_05",
            )
        },
        "mean_norm_error": round(error_sum / matched, 4) if matched else None,
        "printed_mape": round(ape / printed, 4) if printed else None,
        "seconds": round(sum(seconds), 1) if seconds else None,
    }


def _source_totals(
    scores: list[FigureScore],
) -> dict[str, dict[str, float | int | None]]:
    merged: dict[str, ValueTotals] = defaultdict(ValueTotals)
    for score in scores:
        for source, row in score.by_source.items():
            m = merged[source]
            m.matched += row.matched
            m.hits_02 += row.hits_02
            m.hits_05 += row.hits_05
            m.error_sum += row.error_sum
    return {
        source: {
            "matched": row.matched,
            "hits_02": row.hits_02,
            "hits_05": row.hits_05,
            "mean_norm_error": round(row.error_sum / row.matched, 4)
            if row.matched
            else None,
        }
        for source, row in merged.items()
    }


def _load_charts(folder: Path) -> list[ChartData]:
    charts: list[ChartData] = []
    for path in sorted(folder.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema") == SCHEMA_ID:
            charts.append(ChartData.model_validate(data))
    return charts


def _load_timing(
    folder: Path,
) -> dict[tuple[str, str], tuple[float | None, int | None]]:
    path = folder / "timing.json"
    if not path.is_file():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {
        (Path(r["bundle"]).name, r["self_ref"]): (r.get("seconds"), r.get("gpu_bytes"))
        for r in rows
    }


def _figure_key(chart: ChartData) -> tuple[str, str]:
    if chart.figure is None:
        return "", ""
    return Path(chart.figure.bundle).name, chart.figure.self_ref


def _match_values(truth: list[Value], pred: list[Value]) -> list[tuple[Value, Value]]:
    """Pairs by (category or x, series); series names are ignored when
    both sides have at most one series (a pie, a single-series bar)."""
    pairs: list[tuple[Value, Value]] = []
    used: set[int] = set()
    single = len({v.series for v in truth}) <= 1 and len({v.series for v in pred}) <= 1
    for t in truth:
        for j, p in enumerate(pred):
            if j in used:
                continue
            if _same_x(t, p) and (single or _same(t.series, p.series)):
                pairs.append((t, p))
                used.add(j)
                break
    return pairs


def _same_x(a: Value, b: Value) -> bool:
    if a.category is not None or b.category is not None:
        return (
            _same(a.category, b.category)
            or (a.category is None and _same(str(a.x), b.category))
            or (b.category is None and _same(a.category, str(b.x)))
        )
    if isinstance(a.x, float) and isinstance(b.x, float):
        return abs(a.x - b.x) <= 1e-6 * max(1.0, abs(a.x))
    return _same(None if a.x is None else str(a.x), None if b.x is None else str(b.x))


def _same(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return same_label(a, b)


def _row_key(value: Value) -> str:
    return normalise_label(
        value.category if value.category is not None else str(value.x)
    )


def _f1(truth: set[str], pred: set[str]) -> float:
    if not truth and not pred:
        return 1.0
    truth_n = [normalise_label(t) for t in truth]
    pred_n = [normalise_label(p) for p in pred]
    tp = sum(any(_same(t, p) for p in pred_n) for t in truth_n)
    precision = (
        sum(any(_same(p, t) for t in truth_n) for p in pred_n) / len(pred_n)
        if pred_n
        else 0.0
    )
    recall = tp / len(truth_n) if truth_n else 0.0
    return (
        round(2 * precision * recall / (precision + recall), 3)
        if precision + recall
        else 0.0
    )


def _iou(a: list[float], b: list[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3g}" if isinstance(value, float) else str(value)
