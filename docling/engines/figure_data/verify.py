# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Checks on read chart data, per-value ``confidence`` and ``issues``.

Base confidence by how a value was obtained (:data:`BASE_CONFIDENCE`):

========================  =====  ==========================================
basis                     conf.  meaning
========================  =====  ==========================================
``printed_confirmed``     0.95   the printed label is among the figure's words
``vector``                0.90   PDF path geometry through a fitted axis map
``printed``               0.85   a printed label the model read, not in words
``raster_snapped``        0.80   pointed mark snapped to a pixel edge + axis
``raster``                0.70   model-pointed position through the axis map
``vlm``                   0.50   the model's own number
========================  =====  ==========================================

Printed labels: for a single-series bar panel the number printed on each
category's line (found by position among the figure's words) becomes the
value's ``label_printed``, overriding the model's attribution; a printed
label then replaces the measured value.

Each failed check on a value subtracts :data:`PENALTY`: a printed label
that disagrees with the measured value (> 5 % of the axis range: the label
may belong to another mark), a value outside the axis range (± 5 %), a
CI / error bar that does not contain its estimate, a category the figure
does not print (when most of a panel's are not). Panel checks: stacked
segments per category sum to 100 (or the axis maximum) within 3 %; pie
slices sum to 100 within 2 when they are percentages; Kaplan-Meier curves
never rise. With several samples a value's confidence is scaled by
``0.5 + 0.5 * agreement`` (share of samples within 2 % of the range of the
median).
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from itertools import pairwise

from docling.engines.figure_data.evidence import PanelAxes, closest_label, parse_number
from docling.engines.figure_data.schema import Panel, Value, Word

BASE_CONFIDENCE = {
    "printed_confirmed": 0.95,
    "vector": 0.90,
    "printed": 0.85,
    "raster_snapped": 0.80,
    "raster": 0.70,
    "vlm": 0.50,
}
PENALTY = 0.25
_SPACE = re.compile(r"\s+")
PRINTED_TOLERANCE = 0.05
RANGE_SLACK = 0.05
STACK_TOLERANCE = 0.03
AGREEMENT_TOLERANCE = 0.02


def value_axis(panel: Panel) -> str:
    return "x" if panel.orientation == "horizontal" or panel.kind == "forest" else "y"


def axis_span(panel: Panel) -> tuple[float, float] | None:
    """The value axis range: the axis ``range``, else the data's own."""
    axis = None
    if panel.axes is not None:
        axis = panel.axes.x if value_axis(panel) == "x" else panel.axes.y
    if axis is not None and axis.range is not None and len(axis.range) == 2:
        lo, hi = sorted(axis.range)
        if hi > lo:
            return lo, hi
    values = [v.value for v in panel.data if v.value is not None]
    if len(values) >= 2 and max(values) > min(values):
        return min(min(values), 0.0), max(values)
    return None


def pair_printed_labels(panel: Panel, words: list[Word], axes: PanelAxes) -> int:
    """Give each value of a single-series bar panel the number printed on
    its category's line (the row of a horizontal bar, the column of a
    vertical one), found by position among the words: the model may hand a
    label to the wrong bar. Returns how many values got one."""
    horizontal = panel.orientation == "horizontal"
    axis = axes.y if horizontal else axes.x
    if (
        panel.kind not in {"bar", "stacked_bar", "grouped_bar"}
        or axis is None
        or axis.scale != "categorical"
        or len({r.series for r in panel.data}) > 1
        or len(axis.ticks) < 2
    ):
        return 0
    positions = sorted(pos for pos, _ in axis.ticks)
    half = 0.4 * statistics.median(b - a for a, b in pairwise(positions))
    tick_words = {str(label) for _, label in axis.ticks}
    numbers = [
        w
        for w in words
        if parse_number(w.text) is not None and w.text not in tick_words
    ]
    paired = 0
    for row in panel.data:
        if row.category is None:
            continue
        index = closest_label(row.category, [str(label) for _, label in axis.ticks])
        if index is None:
            continue
        tick = axis.ticks[index][0]
        on_line = [
            w for w in numbers if abs((w.cy if horizontal else w.cx) - tick) <= half
        ]
        if len(on_line) == 1:
            row.label_printed = on_line[0].text
            paired += 1
    return paired


def apply_printed(panel: Panel, words: list[Word]) -> list[str]:
    """Replace measured values by the numbers printed at their marks."""
    issues: list[str] = []
    printed = {n for w in words if (n := parse_number(w.text)) is not None}
    span = axis_span(panel)
    for row in panel.data:
        if row.label_printed is None:
            continue
        number = parse_number(row.label_printed)
        if number is None:
            continue
        confirmed = number in printed
        confidence = BASE_CONFIDENCE["printed_confirmed" if confirmed else "printed"]
        if (
            row.value is not None
            and row.source != "vlm"
            and span is not None
            and abs(row.value - number) > PRINTED_TOLERANCE * (span[1] - span[0])
        ):
            issues.append(
                f"panel {panel.id}: printed {row.label_printed} vs measured "
                f"{row.value:g} ({_key(row)})"
            )
            confidence -= PENALTY
        row.value = number
        row.source = "printed"
        row.confidence = round(confidence, 3)
    return issues


def check_labels(panel: Panel, words: list[Word]) -> list[str]:
    """Categories and series names the figure does not print (a model's
    invention, or junk from a degenerate read) lower their values'
    confidence when they are most of the panel's."""
    printed = _SPACE.sub(" ", " ".join(w.text for w in words)).casefold()

    def unprinted(label: str | None) -> bool:
        return label is not None and _SPACE.sub(" ", label).casefold() not in printed

    labels = {r.category for r in panel.data if r.category is not None}
    missing = {label for label in labels if unprinted(label)}
    if len(labels) < 2 or len(missing) <= len(labels) / 2:
        return []
    for row in panel.data:
        if row.category in missing and row.source != "printed":
            _penalise(row)
    return [
        f"panel {panel.id}: {len(missing)} of {len(labels)} categories are not "
        f"printed in the figure (e.g. {sorted(missing)[0]!r})"
    ]


def verify_panel(panel: Panel) -> list[str]:
    """Range, interval, stack, pie and survival checks; lowers the
    confidence of the values that fail and returns the issues."""
    issues: list[str] = []
    span = axis_span(panel)
    stacked = panel.kind == "stacked_bar"
    for row in panel.data:
        if row.value is None:
            continue
        if span is not None and panel.kind != "pie":
            lo, hi = span
            slack = RANGE_SLACK * (hi - lo)
            low_limit = -slack if stacked else lo - slack
            high_limit = (hi - lo) + slack if stacked else hi + slack
            if not low_limit <= row.value <= high_limit:
                issues.append(
                    f"panel {panel.id}: {row.value:g} outside the axis range "
                    f"[{lo:g}, {hi:g}] ({_key(row)})"
                )
                _penalise(row)
        if row.err_lo is not None and row.err_hi is not None:
            lo_e, hi_e = sorted((row.err_lo, row.err_hi))
            if not lo_e - 1e-9 <= row.value <= hi_e + 1e-9:
                issues.append(
                    f"panel {panel.id}: interval [{lo_e:g}, {hi_e:g}] misses "
                    f"{row.value:g} ({_key(row)})"
                )
                _penalise(row)
    if stacked:
        issues.extend(_check_stacks(panel, span))
    if panel.kind == "pie":
        values = [r.value for r in panel.data if r.value is not None]
        total = sum(values)
        if values and 50 < total < 150 and abs(total - 100) > 2:
            issues.append(f"panel {panel.id}: slices sum to {total:g}, not 100")
    if panel.kind == "kaplan_meier":
        issues.extend(_check_survival(panel, span))
    return issues


def _check_stacks(panel: Panel, span: tuple[float, float] | None) -> list[str]:
    totals: dict[str, float] = defaultdict(float)
    for row in panel.data:
        if row.value is not None:
            totals[_category(row)] += row.value
    target = 100.0
    if span is not None and not 95 <= span[1] <= 105:
        target = span[1]
    off = [
        f"{c} sums to {t:g}"
        for c, t in totals.items()
        if abs(t - target) > STACK_TOLERANCE * target
    ]
    if not off:
        return []
    return [
        f"panel {panel.id}: stacked segments do not sum to {target:g}: "
        + "; ".join(off[:5])
    ]


def _check_survival(panel: Panel, span: tuple[float, float] | None) -> list[str]:
    tol = 0.01 * ((span[1] - span[0]) if span else 1.0)
    issues: list[str] = []
    by_series: dict[str, list[tuple[float, Value]]] = defaultdict(list)
    for row in panel.data:
        if isinstance(row.x, float) and row.value is not None:
            by_series[row.series or ""].append((row.x, row))
    for series, points in by_series.items():
        points.sort(key=lambda p: p[0])
        for (_, prev), (x, row) in pairwise(points):
            if (
                row.value is not None
                and prev.value is not None
                and row.value > prev.value + tol
            ):
                issues.append(
                    f"panel {panel.id}: survival rises in {series or 'series'} at x={x:g}"
                )
                _penalise(row)
    return issues


def merge_samples(samples: list[list[Panel]]) -> list[Panel]:
    """Per-cell median of several reads of the same figure (panels matched
    by id, values by category/x/series); confidence scaled by agreement."""
    if len(samples) == 1:
        return samples[0]
    base = max(samples, key=lambda panels: sum(len(p.data) for p in panels))
    merged: list[Panel] = []
    for panel in base:
        reads = [p for panels in samples for p in panels if p.id == panel.id]
        span = axis_span(panel)
        cells: dict[str, list[Value]] = defaultdict(list)
        for read in reads:
            for row in read.data:
                cells[_key(row)].append(row)
        out = panel.model_copy(deep=True)
        for row in out.data:
            values = [r.value for r in cells[_key(row)] if r.value is not None]
            if not values:
                continue
            median = statistics.median(values)
            tol = AGREEMENT_TOLERANCE * (
                (span[1] - span[0]) if span else abs(median) or 1.0
            )
            agreement = sum(abs(v - median) <= tol for v in values) / len(samples)
            row.value = median
            if row.confidence is not None:
                row.confidence = round(row.confidence * (0.5 + 0.5 * agreement), 3)
        merged.append(out)
    return merged


def _penalise(row: Value) -> None:
    if row.confidence is not None:
        row.confidence = round(max(0.0, row.confidence - PENALTY), 3)


def _category(row: Value) -> str:
    return row.category if row.category is not None else str(row.x)


def _key(row: Value) -> str:
    return f"{_category(row)}/{row.series or ''}"
