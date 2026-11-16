# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Read a vector panel from its PDF paths: exact values, no model.

- **Bars**: filled axis-aligned rectangles. Equal widths and varying
  heights make vertical bars (else horizontal); a fill colour is a series;
  rectangles at one position along the category axis are a stack, adjacent
  positions a group; the far end along the value axis goes through the
  axis map (a stacked segment: far end minus near end).
- **Lines**: stroke-only polylines with three or more vertices; a stroke
  colour is a series, each vertex a point (categorical x snaps to the
  nearest tick, numeric x and y go through the axis maps).
- **Pies**: closed filled paths with curved edges around a shared centre;
  a slice's value is its sweep angle as a percentage.

Series names come from legend swatches: a small rectangle or line sample
of the series colour with words right of it. Anything else (error bars,
markers-only scatter, box plots) returns None, so the VLM path reads it.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

import numpy as np

from docling.engines.figure_data.evidence import AxisMap, PanelAxes
from docling.engines.figure_data.schema import (
    Box,
    PanelRead,
    PlacedValue,
    Series,
    Value,
    VectorMark,
    Word,
)

_LIGHT = 235
_SWATCH_MAX = 0.1
_MAX_LINE_POINTS = 200

_T = TypeVar("_T")


def read_vector_panel(
    marks: list[VectorMark], words: list[Word], region: Box, axes: PanelAxes
) -> PanelRead | None:
    inside = [m for m in marks if _centre_in(m.bbox, region)]
    return (
        _read_bars(inside, words, region, axes)
        or _read_pies(inside, words, region)
        or _read_lines(inside, words, region, axes)
    )


def _read_bars(
    marks: list[VectorMark], words: list[Word], region: Box, axes: PanelAxes
) -> PanelRead | None:
    width, height = region[2] - region[0], region[3] - region[1]
    rects = [
        m
        for m in marks
        if m.is_rect
        and m.fill is not None
        and not _is_light(m.fill)
        and 1.5 <= _w(m.bbox) < 0.9 * width
        and 1.5 <= _h(m.bbox) < 0.9 * height
    ]
    names = _legend(rects, words, region, colour=lambda m: m.fill)
    legend_names = {m.fill: names[id(m)] for m in rects if id(m) in names and m.fill}
    bars = [m for m in rects if id(m) not in names]
    if len(bars) < 2:
        return None
    widths = np.array([_w(m.bbox) for m in bars])
    heights = np.array([_h(m.bbox) for m in bars])
    vertical = _cv(widths) <= _cv(heights)
    value_map = axes.y if vertical else axes.x
    category_map = axes.x if vertical else axes.y
    if value_map is None or value_map.scale == "categorical":
        return None

    def along(m: VectorMark) -> tuple[float, float]:
        """(near, far) edges along the value axis, in pixels."""
        lo, hi = (m.bbox[1], m.bbox[3]) if vertical else (m.bbox[0], m.bbox[2])
        zero = value_map.pos_of(0.0)
        base = zero if zero is not None else (hi if vertical else lo)
        return (lo, hi) if abs(lo - base) < abs(hi - base) else (hi, lo)

    def centre(m: VectorMark) -> float:
        return (m.bbox[0] + m.bbox[2]) / 2 if vertical else (m.bbox[1] + m.bbox[3]) / 2

    thickness = float(np.median(widths if vertical else heights))
    positions = _clusters(sorted(bars, key=centre), centre, 0.3 * thickness)
    groups: list[list[list[VectorMark]]] = []
    for stack in positions:
        colours = {m.fill for m in stack}
        if (
            groups
            and centre(stack[0]) - centre(groups[-1][-1][0]) <= 1.5 * thickness
            and not colours & {m.fill for s in groups[-1] for m in s}
        ):
            groups[-1].append(stack)
        else:
            groups.append([stack])
    series_names = {
        colour: legend_names.get(colour, colour)
        for colour in dict.fromkeys(m.fill for m in bars if m.fill)
    }
    values: list[PlacedValue] = []
    stacked = grouped = False
    for index, group in enumerate(groups):
        group_centre = float(np.mean([centre(s[0]) for s in group]))
        category = (
            (
                category_map.category_at(group_centre)
                if category_map is not None
                else None
            )
            or _label_near(words, group_centre, vertical, region)
            or str(index + 1)
        )
        grouped = grouped or len(group) > 1
        for stack in group:
            stacked = stacked or len(stack) > 1
            for mark in stack:
                near, far = along(mark)
                v_far, v_near = value_map.value_at(far), value_map.value_at(near)
                if v_far is None or v_near is None:
                    continue
                value = v_far - v_near if len(stack) > 1 else v_far
                x_px, y_px = (centre(mark), far) if vertical else (far, centre(mark))
                values.append(
                    PlacedValue(
                        value=Value(
                            category=category,
                            series=series_names.get(mark.fill or "", mark.fill),
                            value=_round(value),
                            source="vector",
                        ),
                        x_px=x_px,
                        y_px=y_px,
                    )
                )
    return PanelRead(
        kind="stacked_bar" if stacked else "grouped_bar" if grouped else "bar",
        orientation="vertical" if vertical else "horizontal",
        series=[Series(name=n, color=c) for c, n in series_names.items()],
        values=values,
    )


def _read_lines(
    marks: list[VectorMark], words: list[Word], region: Box, axes: PanelAxes
) -> PanelRead | None:
    if axes.y is None or axes.y.scale == "categorical" or axes.x is None:
        return None
    lines = [
        m
        for m in marks
        if m.fill is None
        and m.stroke is not None
        and not m.is_rect
        and len(m.points) >= 3
        and _w(m.bbox) > 1.0
        and _h(m.bbox) > 1.0
    ]
    if not lines:
        return None
    samples = [
        m
        for m in marks
        if m.fill is None and m.stroke is not None and len(m.points) == 2
    ]
    names = _legend(samples, words, region, colour=lambda m: m.stroke)
    by_colour: dict[str, list[VectorMark]] = defaultdict(list)
    for line in lines:
        by_colour[line.stroke or ""].append(line)
    values: list[PlacedValue] = []
    series: list[Series] = []
    for colour, group in by_colour.items():
        name = next(
            (names[id(s)] for s in samples if s.stroke == colour and id(s) in names),
            colour,
        )
        series.append(Series(name=name, color=colour))
        seen: set[tuple[str, float]] = set()
        for line in group:
            for px, py in line.points[:_MAX_LINE_POINTS]:
                x = _x_value(axes.x, px)
                y = axes.y.value_at(py)
                if x is None or y is None or (str(x), round(y, 6)) in seen:
                    continue
                seen.add((str(x), round(y, 6)))
                values.append(
                    PlacedValue(
                        value=Value(
                            category=x if isinstance(x, str) else None,
                            x=None if isinstance(x, str) else _round(x),
                            series=name,
                            value=_round(y),
                            source="vector",
                        ),
                        x_px=px,
                        y_px=py,
                    )
                )
    if not values:
        return None
    return PanelRead(kind="line", orientation="vertical", series=series, values=values)


def _read_pies(
    marks: list[VectorMark], words: list[Word], region: Box
) -> PanelRead | None:
    wedges = [
        m
        for m in marks
        if m.fill is not None and not m.is_rect and m.closed and len(m.points) >= 3
    ]
    if len(wedges) < 2:
        return None
    swatches = [m for m in marks if m.is_rect and m.fill is not None]
    names = _legend(swatches, words, region, colour=lambda m: m.fill)
    by_colour = {m.fill: names[id(m)] for m in swatches if id(m) in names and m.fill}
    centre = _shared_centre(wedges)
    if centre is None:
        return None
    cx, cy = centre
    radius = max(_w(m.bbox) for m in wedges)
    values: list[PlacedValue] = []
    total = 0.0
    for wedge in wedges:
        arc = _arc(wedge.points, centre, 0.2 * radius)
        if len(arc) < 2:
            continue
        angles = np.unwrap([math.atan2(y - cy, x - cx) for x, y in arc])
        sweep = abs(float(angles[-1] - angles[0]))
        if sweep <= 0:
            continue
        total += sweep
        mid = float(angles[0] + angles[-1]) / 2
        r = float(np.mean([math.dist(p, centre) for p in arc]))
        values.append(
            PlacedValue(
                value=Value(
                    category=by_colour.get(wedge.fill or "", wedge.fill),
                    value=_round(sweep / (2 * math.pi) * 100, 2),
                    source="vector",
                ),
                x_px=cx + 0.6 * r * math.cos(mid),
                y_px=cy + 0.6 * r * math.sin(mid),
            )
        )
    if len(values) < 2 or not 0.9 * 2 * math.pi <= total <= 1.1 * 2 * math.pi:
        return None
    return PanelRead(
        kind="pie",
        series=[],
        values=values,
        notes=["slice values are sweep angles as % of the full circle"],
    )


def _arc(
    points: list[tuple[float, float]], centre: tuple[float, float], min_r: float
) -> list[tuple[float, float]]:
    """A wedge's arc vertices in drawing order, starting after its centre
    vertex (the path may start anywhere on its outline and repeat its
    first point to close)."""
    at = min(range(len(points)), key=lambda i: math.dist(points[i], centre))
    ordered = points[at + 1 :] + points[:at]
    arc: list[tuple[float, float]] = []
    for point in ordered:
        if math.dist(point, centre) <= min_r:
            continue
        if arc and math.dist(point, arc[-1]) < 0.5:
            continue
        arc.append(point)
    return arc


def _shared_centre(wedges: list[VectorMark]) -> tuple[float, float] | None:
    """The vertex most wedges share (a pie's centre)."""
    counts: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    for wedge in wedges:
        for point in {(round(x), round(y)): (x, y) for x, y in wedge.points}.values():
            counts[(round(point[0]), round(point[1]))].append(point)
    if not counts:
        return None
    key, points = max(counts.items(), key=lambda kv: len(kv[1]))
    if len(points) < max(2, len(wedges) // 2):
        return None
    return float(np.mean([p[0] for p in points])), float(
        np.mean([p[1] for p in points])
    )


def _legend(
    marks: list[VectorMark],
    words: list[Word],
    region: Box,
    *,
    colour: Callable[[VectorMark], str | None],
) -> dict[int, str]:
    """Legend swatches among *marks* → their label, keyed by ``id(mark)``."""
    side = min(region[2] - region[0], region[3] - region[1])
    out: dict[int, str] = {}
    for mark in marks:
        w, h = _w(mark.bbox), _h(mark.bbox)
        if max(w, h) > _SWATCH_MAX * side or colour(mark) is None:
            continue
        if mark.is_rect and max(w, h) > 2.5 * max(min(w, h), 1.0):
            continue
        mid = (mark.bbox[1] + mark.bbox[3]) / 2
        size = max(h, 4.0)
        line = _line_right_of(words, mark.bbox[2], mid, size)
        if not line:
            continue
        below = (line[0].bbox[3] + line[-1].bbox[3]) / 2 + 0.7 * size
        continuation = [
            w
            for w in _line_right_of(words, line[0].bbox[0] - 1, below, size)
            if w.bbox[2] <= line[-1].bbox[2] + 2 * size
        ]
        label = line + continuation
        out[id(mark)] = " ".join(w.text for w in label)
    return out


def _line_right_of(
    words: list[Word], left: float, mid: float, size: float
) -> list[Word]:
    """Words on the text line at height *mid* starting within a few
    character sizes right of *left*, up to the first wide gap."""
    candidates = sorted(
        (w for w in words if abs(w.cy - mid) <= 0.6 * size and w.bbox[0] >= left - 1),
        key=lambda w: w.bbox[0],
    )
    if not candidates or candidates[0].bbox[0] > left + 4 * size:
        return []
    line = [candidates[0]]
    for word in candidates[1:]:
        if word.bbox[0] - line[-1].bbox[2] > 1.5 * size:
            break
        line.append(word)
    return line


def _x_value(axis: AxisMap, px: float) -> float | str | None:
    if axis.scale == "categorical":
        return axis.category_at(px)
    return axis.value_at(px)


def _label_near(
    words: list[Word], position: float, vertical: bool, region: Box
) -> str | None:
    """The word under (vertical bars) or left of (horizontal bars) a bar
    group, outside the plotted area."""
    if vertical:
        below = [
            w
            for w in words
            if abs(w.cx - position) <= 0.05 * (region[2] - region[0])
            and w.cy > region[1] + 0.6 * (region[3] - region[1])
        ]
        return max(below, key=lambda w: w.cy).text if below else None
    left = [
        w
        for w in words
        if abs(w.cy - position) <= 0.03 * (region[3] - region[1])
        and w.cx < region[0] + 0.5 * (region[2] - region[0])
    ]
    return min(left, key=lambda w: w.cx).text if left else None


def _clusters(
    items: list[_T], key: Callable[[_T], float], tol: float
) -> list[list[_T]]:
    out: list[list[_T]] = []
    for item in items:
        if out and key(item) - key(out[-1][-1]) <= tol:
            out[-1].append(item)
        else:
            out.append([item])
    return out


def _cv(values: np.ndarray) -> float:
    mean = float(np.mean(values))
    return float(np.std(values)) / mean if mean else math.inf


def _is_light(colour: str) -> bool:
    return all(int(colour[i : i + 2], 16) >= _LIGHT for i in (1, 3, 5))


def _centre_in(box: Box, region: Box) -> bool:
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return region[0] <= cx <= region[2] and region[1] <= cy <= region[3]


def _w(box: Box) -> float:
    return box[2] - box[0]


def _h(box: Box) -> float:
    return box[3] - box[1]


def _round(value: float, digits: int = 4) -> float:
    return round(value, digits)
