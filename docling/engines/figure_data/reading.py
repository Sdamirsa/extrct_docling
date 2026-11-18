# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""What a cloud model or an agent returns for a figure, and how it becomes
``extrct.figure-data/1``.

The reply names its values (category, x, series are always written, null
where they do not apply: a model leaves out whatever it may) and carries no
positions: a strong vision model reads a value against the axis more
precisely than it points at the mark. The conventions are the ones the
measured engine's prompt states, so the three methods return the same
shape of table for the same chart.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from docling.engines.figure_data.evidence import (
    AxisMap,
    find_axes,
    parse_number,
    words_in,
)
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.schema import (
    Axes,
    Axis,
    AxisScale,
    Box,
    ChartData,
    Labeler,
    Orientation,
    Panel,
    PanelKind,
    Series,
    Value,
    ValueSource,
)
from docling.engines.figure_data.verify import (
    BASE_CONFIDENCE,
    apply_printed,
    axis_span,
    check_labels,
    verify_panel,
)

GRID = 1000

CONVENTIONS = """How a chart becomes points
- One chart per plot with its own axes, and one per pie, also when charts sit in a grid, share a legend or stand under one panel letter. Use the chart ids you were given when they match what you see; otherwise number the charts 1, 2, 3, ... in reading order and give each a box.
- One point per (category or x value, series), each once.
- category = the tick label of the mark, exactly as printed (line breaks as spaces); null on a numeric x axis. x = the mark's position on a numeric x axis, as a number; null otherwise. series = the legend entry, exactly as printed; null only when the chart has no legend. Never repeat the category as the series.
- value = the number the mark stands for, in axis units, read against the nearest tick labels to the precision the axis allows. Do not round to a tick.
- label = the number printed at the mark, exactly as printed, when one is printed. A printed number is the value: it beats a reading against the axis.
- Bar: the bar's end. Grouped bar: one point per bar, category = the tick label, series = the bar's legend entry.
- Stacked bar: one point per segment, value = the segment's own length, not the cumulative edge. category names the bar, series the segment's legend entry. When one tick label carries several stacked bars (a pair per item, one per group), each bar is its own category, written "<tick label> - <group>". A segment the legend implies but the bar does not show is written with value 0.
- Box plot: value = the median, err_lo and err_hi = the whisker ends; quartiles and outliers go into the chart's notes.
- Interval, error bar or forest plot: value = the centre, err_lo and err_hi = the two ends as axis values, not as distances from the centre.
- Line or scatter: one point per marker; a line without markers: one point per x tick. When the x axis prints no tick labels, x = 1, 2, 3, ... in order.
- A curve with a statistic printed for it (a ROC curve with its AUC in the legend): one point per curve, category = the curve's name, series = the statistic's name (AUC, AUROC), value and label = the printed number. Do not trace the curve.
- Pie: one point per slice, value = its percentage, series null.
- Heatmap: one point per cell, category = the row label, series = the column label.

What must hold
- A figure that plots or prints no data values that could go into a table (a diagram, workflow, architecture, photo, screenshot, or a raw signal trace such as an ECG) has no data: has_data false, no charts. Never turn a diagram's labels into values.
- Never invent a value. A value you cannot read is null. Anything the figure shows that you did not write down (a chart, a series, the individual dots behind a box) is named in not_read, with the reason and how much it is.
- Completeness counts as much as precision: before you answer, count the marks of each chart and the points you wrote for it."""


def _with_nulls(data: Any, names: tuple[str, ...]) -> Any:
    """*data* with the always-written fields a reader left out set to null.
    The schema a model is given marks them required, so that it writes
    them; a reply without one is still read, and the checks say what is
    missing."""
    if isinstance(data, dict):
        return {**dict.fromkeys(names), **data}
    return data


class ReadAxis(BaseModel):
    name: str | None
    unit: str | None = None
    scale: AxisScale | None = None
    min: float | None = None
    max: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _nulls(cls, data: Any) -> Any:
        return _with_nulls(data, ("name",))


class ReadPoint(BaseModel):
    """One data mark; the naming fields are always written."""

    category: str | None
    x: str | None
    series: str | None
    value: float | None
    err_lo: float | None = None
    err_hi: float | None = None
    label: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _nulls(cls, data: Any) -> Any:
        return _with_nulls(data, ("category", "x", "series", "value"))

    @field_validator("category", "x", "series", "label", mode="before")
    @classmethod
    def _as_text(cls, value: Any) -> Any:
        # A model writes x = 3 as readily as x = "3".
        if isinstance(value, bool) or value is None:
            return value
        return f"{value:g}" if isinstance(value, int | float) else value


class ReadPanel(BaseModel):
    id: str
    title: str | None
    kind: PanelKind
    orientation: Orientation | None = None
    x_axis: ReadAxis | None = None
    y_axis: ReadAxis | None = None
    series: list[str] = Field(default_factory=list)
    points: list[ReadPoint]
    # [x0, y0, x1, y1] on a 0-1000 grid of the figure; only for a chart the
    # layout analysis did not list.
    box: list[int] | None = None
    notes: list[str] = Field(default_factory=list)

    # What is accepted is wider than what is asked for: a reader that writes
    # one note as text, or its legend as objects, has still read the chart.
    @model_validator(mode="before")
    @classmethod
    def _nulls(cls, data: Any) -> Any:
        return _with_nulls(data, ("title",))

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, value: Any) -> Any:
        return _text_list(value)

    @field_validator("series", mode="before")
    @classmethod
    def _series(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [
                str(item.get("name")) if isinstance(item, dict) else item
                for item in value
            ]
        return _text_list(value)

    @field_validator("id", mode="before")
    @classmethod
    def _id(cls, value: Any) -> Any:
        return str(value) if isinstance(value, int) else value


class FigureReading(BaseModel):
    """A whole figure as a cloud model or an agent returns it."""

    description: str
    has_data: bool
    panels: list[ReadPanel] = Field(default_factory=list)
    not_read: list[str] = Field(default_factory=list)

    @field_validator("not_read", mode="before")
    @classmethod
    def _not_read(cls, value: Any) -> Any:
        return _text_list(value)


def _text_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return value


Reader = Literal["cloud", "agent"]


def chart_from_reading(
    reading: FigureReading,
    prepared: PreparedFigure,
    *,
    reader: Reader,
    labeler: str,
    frontier: bool,
) -> tuple[ChartData, list[str]]:
    """*reading* as ``extrct.figure-data/1`` plus what the checks found.
    A chart that carries the id of a prepared chart takes that chart's box
    and tick labels. *frontier* is whether a cloud model read it (its
    values start at the confidence measured for such a read) or a local
    one."""
    source: ValueSource = "agent" if reader == "agent" else "vlm"
    base = BASE_CONFIDENCE["vlm_cloud" if frontier else "vlm"]
    uncertain = list(reading.not_read)
    if not reading.has_data or not reading.panels:
        reason = (
            f"not a data chart: {reading.description}"
            if not reading.has_data
            else f"no chart returned: {reading.description}"
        )
        chart = ChartData(
            figure=prepared.figure,
            source_kind=prepared.source_kind,
            labeler=_labeler(reader, labeler),
            description=reading.description or None,
            uncertain=[reason, *uncertain],
        )
        return chart, []
    panels: list[Panel] = []
    issues: list[str] = []
    seen: dict[str, int] = {}
    for read in reading.panels:
        count = seen.get(read.id, 0) + 1
        seen[read.id] = count
        panel_id = read.id if count == 1 else f"{read.id}{count}"
        known = prepared.panel(read.id) if count == 1 else None
        if known is None and len(prepared.panels) == 1 and len(reading.panels) == 1:
            known = prepared.panels[0]
        region: Box | None = (
            known.bbox if known is not None else _grid_box(read.box, prepared)
        )
        words = (
            words_in(prepared.words, region) if region is not None else prepared.words
        )
        axes = find_axes(words, known.bbox) if known is not None else None
        # The schema's forest plot has its values on the x axis; the same
        # plot drawn upright is an interval plot of kind "other".
        upright = read.kind == "forest" and read.orientation == "vertical"
        panel = Panel(
            id=panel_id,
            bbox_px=prepared.to_crop(region or prepared.full),
            title=read.title,
            kind="other" if upright else read.kind,
            orientation=read.orientation,
            axes=Axes(
                x=_axis(read.x_axis, axes.x if axes is not None else None),
                y=_axis(read.y_axis, axes.y if axes is not None else None),
            ),
            series=[Series(name=name) for name in read.series],
            data=_values(read.points, source, base),
            notes=list(read.notes),
        )
        issues.extend(apply_printed(panel, words))
        issues.extend(check_labels(panel, prepared.words))
        issues.extend(verify_panel(panel))
        panels.append(panel)
    chart = ChartData(
        figure=prepared.figure,
        source_kind=prepared.source_kind,
        panels=panels,
        labeler=_labeler(reader, labeler),
        description=reading.description or None,
        uncertain=uncertain,
    )
    return chart, issues


class PanelChecks(BaseModel):
    """What the checks say about one chart as an agent recorded it. A
    naming problem is the reader's to fix whatever the values are; a value
    check says where to look again and can itself be wrong."""

    naming: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)


def panel_checks(read: ReadPanel, prepared: PreparedFigure) -> PanelChecks:
    """The feedback an agent gets when it records a chart. Each naming
    problem says how the points are to be named instead: a check that only
    says what is wrong leaves a reader that trusts its numbers nothing to
    do."""
    reading = FigureReading(description="", has_data=True, panels=[read])
    chart, issues = chart_from_reading(
        reading, prepared, reader="agent", labeler="", frontier=True
    )
    checks = PanelChecks(values=issues)
    points = read.points
    unnamed = [p for p in points if p.category is None and p.x is None]
    if unnamed and len(points) > 1:
        if read.kind == "pie":
            checks.naming.append(
                f"{len(unnamed)} slice(s) have no category: the name of a pie "
                "slice is its category, and series stays null"
            )
        else:
            checks.naming.append(
                f"{len(unnamed)} point(s) have neither a category nor an x: the "
                "tick label (or the bar, row or curve name) of a mark is its "
                "category; series is only for its legend entry"
            )
    keys = [(p.category, p.x, p.series) for p in points]
    repeated = len(keys) - len(set(keys))
    if repeated:
        checks.naming.append(
            f"{repeated} point(s) repeat a (category or x, series) pair: every "
            "point needs its own"
        )
    if read.kind != "pie" and read.series and any(p.series is None for p in points):
        missing = sum(p.series is None for p in points)
        checks.naming.append(
            f"{missing} point(s) have no series though the chart has a legend: "
            "give each point its legend entry, exactly as printed"
        )
    doubled = _bars_per_category(chart.panels[0]) if chart.panels else 1
    if doubled > 1:
        checks.naming.append(
            f"each category holds the segments of {doubled} bars (they sum to "
            f"{doubled} times a full bar): when one tick label carries several "
            'stacked bars, each bar is its own category, written "<tick label> '
            "- <group>\", and series is the segment's legend entry alone"
        )
        checks.values = [i for i in checks.values if "do not sum to" not in i]
    return checks


def _bars_per_category(panel: Panel) -> int:
    """How many stacked bars most categories of *panel* hold, judged by
    what their segments add up to (1: one bar each, as it should be)."""
    if panel.kind != "stacked_bar":
        return 1
    totals: dict[str, float] = {}
    for row in panel.data:
        if row.value is not None and row.category is not None:
            totals[row.category] = totals.get(row.category, 0.0) + row.value
    span = axis_span(panel)
    full = span[1] if span is not None and not 95 <= span[1] <= 105 else 100.0
    multiples = [round(total / full) for total in totals.values() if full > 0]
    several = [
        k
        for k, total in zip(multiples, totals.values())
        if k >= 2 and abs(total - k * full) <= 0.05 * k * full
    ]
    if not several or len(several) < len(totals) / 2:
        return 1
    return max(set(several), key=several.count)


def _values(points: list[ReadPoint], source: ValueSource, base: float) -> list[Value]:
    values: list[Value] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for point in points:
        key = (point.category, point.x, point.series)
        if key in seen and any(part is not None for part in key):
            continue
        seen.add(key)
        values.append(
            Value(
                category=point.category,
                x=_x_value(point.x),
                series=point.series,
                value=_round(point.value),
                err_lo=_round(point.err_lo),
                err_hi=_round(point.err_hi),
                label_printed=point.label,
                source=source,
                confidence=base,
            )
        )
    return values


def _axis(read: ReadAxis | None, calibrated: AxisMap | None) -> Axis | None:
    """The reader's axis (name, unit, range) with the scale, ticks and range
    of the tick labels where the layout analysis calibrated them."""
    if read is None and calibrated is None:
        return None
    axis = Axis()
    if read is not None:
        axis = Axis(
            name=read.name,
            unit=read.unit,
            scale=read.scale,
            range=[read.min, read.max]
            if read.min is not None and read.max is not None
            else None,
        )
    if calibrated is not None:
        axis.scale = calibrated.scale
        axis.ticks = [label for _, label in calibrated.ticks]
        span = calibrated.value_range
        # The reader saw where the axis ends; the tick labels only where
        # its first and last labels stand.
        if span is not None and axis.range is None:
            axis.range = [span[0], span[1]]
    return axis


def _grid_box(box: list[int] | None, prepared: PreparedFigure) -> Box | None:
    if box is None or len(box) != 4:
        return None
    x0, y0, x1, y1 = (min(max(v, 0), GRID) / GRID for v in box)
    if x1 <= x0 or y1 <= y0:
        return None
    return (
        x0 * prepared.width,
        y0 * prepared.height,
        x1 * prepared.width,
        y1 * prepared.height,
    )


def _labeler(reader: Reader, name: str) -> Labeler:
    return Labeler(
        kind="agent" if reader == "agent" else "engine",
        name=name,
        date=time.strftime("%Y-%m-%d"),
    )


def _x_value(text: str | None) -> float | str | None:
    if text is None:
        return None
    number = parse_number(text)
    return number if number is not None else text


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
