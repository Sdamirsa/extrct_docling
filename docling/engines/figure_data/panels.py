# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Split a figure into its panels (sub-charts).

0. **Axes.** A chart has tick labels: a run of at least three numbers in a
   column (right edges aligned) or in a row (same baseline) whose values
   are linear or logarithmic in their position is an axis. Two or more
   charts found this way are separated by cutting the figure, recursively,
   along the widest ink-free band between them. Papers pack panels far
   closer than any fixed gutter width, so this comes first; the steps
   below apply when fewer than two axes are found (pies, a single chart).
1. **Gutters.** The background colour is the median of the image border;
   rows (then columns, recursively) whose ink stays near zero for at least
   :data:`GUTTER_FRACTION` of the image side cut the figure into blocks
   (an XY-cut).
2. **Graphic blocks.** A block is a panel when it holds a long straight
   ink run or a large connected component (axes, a plot background, a pie)
   and is not a solid wordless block (a bar of a chart without axis lines);
   text-only blocks
   (legends, shared axis titles, panel letters on their own line) are not,
   and a text block close to exactly one panel (title, side legend) joins it.
3. **Letters.** Single letters a-h / A-H (``(a)`` too) from the words name
   the panels: a panel takes the alphabetically last letter above-left of
   its centre, several panels under one letter become ``a1, a2, ...``.
4. **Grid fit.** When letters and gutters disagree (fewer panels than
   letters), the letters' own grid splits the figure.

When a vision model has listed the charts of the figure,
:func:`cut_from_list` decides between this split and a cut made from the
model's list.

Everything is in work-image pixels.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal, NamedTuple

import numpy as np
from pydantic import BaseModel
from scipy import ndimage

from docling.engines.figure_data.evidence import fit_axis, parse_number
from docling.engines.figure_data.schema import Box, PanelSplit, Word

GUTTER_FRACTION = 0.01
_GUTTER_MAX_INK = 0.002
_INK_DIFF = 40
_MAX_DEPTH = 4
_GRAPHIC_SPAN = 0.3
_GRAPHIC_MIN_SIDE = 0.06
_MIN_PANEL_AREA = 0.02
_MAX_ASPECT = 10.0
_SOLID = 0.85
_ALIGN = 0.75
_BAND_MAX_INK = 0.01
_BOX_MARGIN = 0.15
_LETTER = re.compile(r"^\(?([a-hA-H])\)?\.?$")
# The longest chart id of a model that names a chart and its crop (a, B2, 12).
_ID_LENGTH = 4
# More listed charts than this is a reply that repeats itself.
_MAX_LISTED = 64
# The shortest side of a chart, of the image's: under it a box is a sliver.
_MIN_SIDE = 0.02
# Listed boxes that touch or overlap a little are tried again this much
# smaller on every side before they count as not separable.
_LIST_SHRINK = (0.0, 0.03, 0.08)
# The text height taken for a figure without words, of its height.
_TEXT_HEIGHT = 0.015
# A run of tick labels this long is an axis. Two were tried as weak
# evidence when a model lists that many charts: no gain on 51 figures.
_MIN_TICKS = 3


class PanelBox(BaseModel):
    id: str
    bbox: Box
    letter: str | None = None


class PanelSplitResult(BaseModel):
    panels: list[PanelBox]
    method: str
    letters: list[str] = []
    notes: list[str] = []
    # Set by :func:`cut_from_list`: the charts the rule splitter found and
    # the charts the model listed.
    rule_charts: int | None = None
    listed_charts: int | None = None


def split_panels(
    image: np.ndarray,
    words: list[Word],
    *,
    mode: PanelSplit = "auto",
) -> PanelSplitResult:
    """Panels of *image* (H x W x 3, uint8) as the rules alone find them;
    a single full-image panel when nothing splits it. Mode ``gutters`` is
    the splitter without the axes step."""
    height, width = image.shape[:2]
    full: Box = (0.0, 0.0, float(width), float(height))
    if mode == "off":
        return PanelSplitResult(panels=[PanelBox(id="1", bbox=full)], method="off")

    mask = ink_mask(image)
    if mode != "gutters":
        charts = split_by_axes(mask, words)
        if charts is not None:
            return PanelSplitResult(
                panels=_name(charts, []),
                method="axes",
                notes=[f"{len(charts)} charts found by their tick labels"],
            )
    blocks = _xy_cut(mask, (0, 0, width, height), depth=0)
    graphic = [b for b in blocks if _is_graphic(mask, b, width, height)]
    graphic = [b for b in graphic if _area(b) >= _MIN_PANEL_AREA * width * height]
    # A solid block without text is a bar of a chart drawn without axis
    # lines (the gutters between bars cut it out), not a panel.
    graphic = [
        b
        for b in graphic
        if any(_centre_in(w, b) for w in words) or _ink_density(mask, b) < _SOLID
    ]
    texts = [b for b in blocks if b not in graphic]
    graphic = _attach_text(graphic, texts, width, height)
    letters = [
        (c, w) for c, w in _letters(words) if _heads_a_block(w, graphic, width, height)
    ]
    notes: list[str] = []
    if not graphic:
        return PanelSplitResult(
            panels=[PanelBox(id="1", bbox=full)],
            method="none",
            letters=[c for c, _ in letters],
        )

    named = _with_letters(_name(graphic, letters), dict(letters), width, height)
    unused = {c for c, _ in letters} - {p.letter for p in named if p.letter}
    if len(letters) >= 2 and (unused or len(graphic) < len(letters)):
        notes.append(
            f"letters {''.join(sorted(c for c, _ in letters))} and "
            f"{len(graphic)} gutter block(s) disagree"
        )
        if len(graphic) < len(letters):
            return PanelSplitResult(
                panels=_letter_grid(letters, width, height),
                method="letters",
                letters=[c for c, _ in letters],
                notes=notes,
            )
    return PanelSplitResult(
        panels=named,
        method="gutters" if len(named) > 1 else "single",
        letters=[c for c, _ in letters],
        notes=notes,
    )


def cut_from_list(
    image: np.ndarray,
    words: list[Word],
    listed: list[tuple[str, Box]],
    *,
    rules: PanelSplitResult | None = None,
) -> PanelSplitResult:
    """The charts of *image* given the charts a vision model lists, each
    ``(id, box)`` with the box in pixels.

    A model has the number of charts right far more often than the rules,
    and their edges far less often (51 figures, 2026-11-19: the count right
    on 42 to 51 against 26, the chart whole in its box for 53 to 145 of 236
    against 220 once the rules are told where the charts are). So the
    model's count decides and the rules draw the edges:

    - the rule splitter's own cut (*rules*; made here when not given)
      stands when it has as many charts as the model lists;
    - when it has not, the image is cut between the listed boxes along the
      widest ink-free bands and every cell is trimmed to its ink
      (``method`` ``listed``); one listed chart is the whole image;
    - when no straight cut separates the listed boxes, they are returned as
      they are (``listed-boxes``) and the caller decides whether to read
      from them.
    """
    height, width = image.shape[:2]
    full: Box = (0.0, 0.0, float(width), float(height))
    if rules is None:
        rules = split_panels(image, words)
    charts = [
        (
            name,
            (
                max(0.0, min(b[0], b[2])),
                max(0.0, min(b[1], b[3])),
                min(float(width), max(b[0], b[2])),
                min(float(height), max(b[1], b[3])),
            ),
        )
        for name, b in listed
    ]
    counts = {"rule_charts": len(rules.panels), "listed_charts": len(charts)}
    if not charts or len(charts) == len(rules.panels):
        return rules.model_copy(update=counts)
    note = (
        f"the rule splitter finds {len(rules.panels)} chart(s), the model "
        f"lists {len(charts)}"
    )
    if len(charts) > _MAX_LISTED:
        # A reply that repeats itself, not a figure.
        return rules.model_copy(
            update={**counts, "notes": [*rules.notes, f"{note}: too many, not taken"]}
        )
    # The count is the model's whatever its boxes are worth; a box without
    # width or height says a chart is there and not where.
    seeds = [(name, b) for name, b in charts if _wide_enough(b, width, height)]
    if len(seeds) < len(charts):
        note += f" ({len(charts) - len(seeds)} without a usable box)"
    if not seeds:
        return rules.model_copy(
            update={**counts, "notes": [*rules.notes, f"{note}: no box to cut by"]}
        )
    if len(seeds) == 1:
        return PanelSplitResult(
            panels=[PanelBox(id="1", bbox=full)],
            method="listed",
            notes=[f"{note}: read whole"],
            **counts,
        )
    mask = ink_mask(image)
    heights = [w.bbox[3] - w.bbox[1] for w in words]
    size = float(np.median(heights)) if heights else _TEXT_HEIGHT * height
    for shrink in _LIST_SHRINK:
        shrunk = [
            _Seed(
                (
                    b[0] + shrink * (b[2] - b[0]),
                    b[1] + shrink * (b[3] - b[1]),
                    b[2] - shrink * (b[2] - b[0]),
                    b[3] - shrink * (b[3] - b[1]),
                ),
                (True, True),
            )
            for _, b in seeds
        ]
        cells = _cut_between(shrunk, full, mask, size)
        if cells is not None:
            trimmed = [_ink_box(mask, cell) for cell in cells]
            kept = [b for b in trimmed if _wide_enough(b, width, height)]
            return PanelSplitResult(
                panels=_named_as_listed(kept or trimmed, seeds),
                method="listed",
                notes=[f"{note}: cut between the listed charts"],
                **counts,
            )
    return PanelSplitResult(
        panels=_named_as_listed([b for _, b in seeds], seeds),
        method="listed-boxes",
        notes=[f"{note}; no straight cut separates them"],
        **counts,
    )


def _wide_enough(box: Box, width: int, height: int) -> bool:
    """A chart is never a sliver: both sides reach :data:`_MIN_SIDE` of the
    image's."""
    return (
        box[2] - box[0] >= _MIN_SIDE * width and box[3] - box[1] >= _MIN_SIDE * height
    )


def _named_as_listed(boxes: list[Box], charts: list[tuple[str, Box]]) -> list[PanelBox]:
    """*boxes* in reading order, each under the id of the listed chart it
    overlaps most, else 1, 2, 3, ...: the ids are kept when each, without
    its brackets and dots, is a short word of its own (a, B2, 12). A chart's
    crop is named by its id, and a model sometimes writes a title where an
    id is asked."""
    ordered = _reading_order(boxes)
    names = []
    for box in ordered:
        overlap = [
            max(0.0, min(box[2], b[2]) - max(box[0], b[0]))
            * max(0.0, min(box[3], b[3]) - max(box[1], b[1]))
            for _, b in charts
        ]
        names.append(re.sub(r"[\W_]+", "", charts[int(np.argmax(overlap))][0]))
    distinct = len({name.casefold() for name in names}) == len(names)
    if not distinct or not all(0 < len(name) <= _ID_LENGTH for name in names):
        names = [str(index + 1) for index in range(len(ordered))]
    return [
        PanelBox(id=name, bbox=box, letter=name if _LETTER.match(name) else None)
        for name, box in zip(names, ordered)
    ]


def split_by_axes(mask: np.ndarray, words: list[Word]) -> list[Box] | None:
    """The boxes of the charts whose axes the tick labels show, or None
    when fewer than two are found or they cannot be told apart by straight
    cuts (one chart inside another)."""
    height, width = mask.shape
    seeds, size = _chart_seeds(words, _MIN_TICKS)
    if len(seeds) < 2:
        return None
    cells = _cut_between(seeds, (0.0, 0.0, float(width), float(height)), mask, size)
    if cells is None:
        return None
    boxes = [_ink_box(mask, cell) for cell in cells]
    boxes = [b for b in boxes if _area(b) >= _MIN_PANEL_AREA * width * height]
    return boxes if len(boxes) >= 2 else None


class _Seed(NamedTuple):
    """The tick labels of one chart; ``spans`` says along which image axes
    (0 = x, 1 = y) the box covers the plot, not only a line of labels."""

    box: Box
    spans: tuple[bool, bool]


def _chart_seeds(words: list[Word], min_ticks: int) -> tuple[list[_Seed], float]:
    """One seed per chart: its tick labels (a y run and the x run that
    starts at its foot together; either alone otherwise), a y run widened
    by the rotated axis title left of it. Also the labels' text height."""
    numeric = [
        w for w in words if len(w.text) <= 8 and parse_number(w.text) is not None
    ]
    if len(numeric) < min_ticks:
        return [], 0.0
    size = float(np.median([w.bbox[3] - w.bbox[1] for w in numeric]))
    # A label is a tick of one axis: the longer run keeps it (two numbers
    # that happen to share a row are no x axis when each heads a column).
    runs = [
        (axis, run)
        for axis in ("y", "x")
        for run in _tick_runs(numeric, axis, tol=_ALIGN * size, min_ticks=min_ticks)
    ]
    taken: set[int] = set()
    boxes: dict[str, list[Box]] = {"y": [], "x": []}
    for axis, run in sorted(runs, key=lambda r: -len(r[1])):
        if taken.isdisjoint(id(w) for w in run):
            taken.update(id(w) for w in run)
            boxes[axis].append(_bounds(run))
    seeds: list[_Seed] = []
    free = boxes["x"]
    for y_run in sorted(boxes["y"]):
        for word in words:
            tall = word.bbox[3] - word.bbox[1] > 1.5 * (word.bbox[2] - word.bbox[0])
            if (
                tall
                and y_run[0] - 4 * size <= word.bbox[2] <= y_run[0]
                and y_run[1] <= word.cy <= y_run[3]
            ):
                y_run = (min(y_run[0], word.bbox[0]), *y_run[1:])
        foot = [
            x
            for x in free
            if abs(x[1] - y_run[3]) <= 4 * size and -2 * size <= x[0] - y_run[2]
            if x[0] - y_run[2] <= 6 * size
        ]
        if foot:
            x_run = min(foot, key=lambda x: abs(x[0] - y_run[2]) + abs(x[1] - y_run[3]))
            free.remove(x_run)
            box = (y_run[0], y_run[1], max(y_run[2], x_run[2]), max(y_run[3], x_run[3]))
            seeds.append(_Seed(box, (True, True)))
        else:
            seeds.append(_Seed(y_run, (False, True)))
    return seeds + [_Seed(x_run, (True, False)) for x_run in free], size


def _bounds(words: list[Word]) -> Box:
    return (
        min(w.bbox[0] for w in words),
        min(w.bbox[1] for w in words),
        max(w.bbox[2] for w in words),
        max(w.bbox[3] for w in words),
    )


def _tick_runs(
    numeric: list[Word], axis: str, *, tol: float, min_ticks: int
) -> list[list[Word]]:
    """The tick-label runs along *axis*: labels aligned on their right
    edge (y) or centre line (x), strictly monotone, at least *min_ticks*,
    on a line or a log scale."""
    key, pos = (
        (lambda w: w.bbox[2], lambda w: w.cy)
        if axis == "y"
        else (lambda w: w.cy, lambda w: w.cx)
    )
    lines: list[list[Word]] = []
    for word in sorted(numeric, key=key):
        if lines and key(word) - key(lines[-1][-1]) <= tol:
            lines[-1].append(word)
        else:
            lines.append([word])
    runs: list[list[Word]] = []
    for line in lines:
        run: list[Word] = []
        for word in [*sorted(line, key=pos), None]:
            if word is not None and _continues(run, word):
                run.append(word)
                continue
            ticks = _fitted(run, pos, "y" if axis == "y" else "x", min_ticks)
            if ticks:
                runs.append(ticks)
            run = [word] if word is not None else []
    return runs


def _continues(run: list[Word], word: Word) -> bool:
    """*word* is the next tick of *run*: its value keeps the run's direction."""
    if not run:
        return True
    value, last = parse_number(word.text), parse_number(run[-1].text)
    assert value is not None and last is not None
    if value == last:
        return False
    if len(run) == 1:
        return True
    first = parse_number(run[0].text)
    assert first is not None
    return (value > last) == (last > first)


def _fitted(
    run: list[Word],
    pos: Callable[[Word], float],
    axis: Literal["x", "y"],
    min_ticks: int,
) -> list[Word]:
    """The labels of *run* that lie on one numeric axis: all of them, or
    all but one (OCR reads "0.8" as "80" now and then); empty when fewer
    than three do."""
    candidates = [run, *(run[:i] + run[i + 1 :] for i in range(len(run)))]
    for ticks in candidates:
        if len(ticks) < min_ticks:
            continue
        fitted = fit_axis(((pos(w), w.text) for w in ticks), axis)
        if fitted is not None and fitted.scale != "categorical":
            return ticks
    return []


def _cut_between(
    seeds: list[_Seed], region: Box, mask: np.ndarray, size: float
) -> list[Box] | None:
    """Cut *region* into one cell per seed: among the straight lines that
    separate the seeds into two groups, the one through the widest free
    band (:func:`_free_band`), then the same within each side."""
    if len(seeds) == 1:
        return [region]
    best: tuple[float, int, float, list[_Seed], list[_Seed]] | None = None
    for axis in (0, 1):
        order = sorted(seeds, key=lambda s: s.box[axis])
        reach = order[0].box[axis + 2]
        for index in range(1, len(order)):
            start = order[index].box[axis]
            if start > reach:
                near, far = order[:index], order[index:]
                # Tick labels stand left of and below their plot: a seed
                # that is only a line of labels has its plot between itself
                # and the next chart (side by side) or the one before
                # (stacked), and the cut belongs on the other side of it.
                side = (
                    1
                    if axis == 0 and not all(s.spans[0] for s in near)
                    else -1
                    if axis == 1 and not all(s.spans[1] for s in far)
                    else 0
                )
                # An OCR box is a little larger than its glyphs: the band
                # may reach into the far labels' box.
                band = _free_band(
                    mask, region, axis, reach, start + _BOX_MARGIN * size, side, size
                )
                if best is None or band[1] > best[0]:
                    best = (band[1], axis, band[0], near, far)
            reach = max(reach, order[index].box[axis + 2])
    if best is None:
        return None
    _, axis, at, near, far = best
    near_region = list(region)
    far_region = list(region)
    near_region[axis + 2] = far_region[axis] = at
    first = _cut_between(near, tuple(near_region), mask, size)  # type: ignore[arg-type]
    second = _cut_between(far, tuple(far_region), mask, size)  # type: ignore[arg-type]
    return None if first is None or second is None else first + second


def _free_band(
    mask: np.ndarray,
    region: Box,
    axis: int,
    lo: float,
    hi: float,
    side: int,
    size: float,
) -> tuple[float, float]:
    """``(centre, width)`` of the band of *region* to cut along between
    *lo* and *hi*: a run of columns (*axis* 0) or rows (1) with next to no
    ink (an axis line may cross it). With *side* 0 the widest run. With
    *side* +1 / -1 a plot lies between the two charts, and a plot has free
    runs of its own: the run next to the labels at the far / near end that
    is at least half a text height (*size*) wide, the widest when there is
    none. The midpoint with width 0 when nothing is free."""
    x0, y0, x1, y1 = (round(v) for v in region)
    a, b = round(lo), max(round(hi), round(lo) + 1)
    sub = mask[y0:y1, a:b] if axis == 0 else mask[a:b, x0:x1]
    profile = sub.sum(axis=axis)
    free = np.flatnonzero(profile <= max(1, _BAND_MAX_INK * sub.shape[axis]))
    if free.size == 0:
        return (lo + hi) / 2, 0.0
    breaks = np.flatnonzero(np.diff(free) > 1)
    starts = free[np.concatenate(([0], breaks + 1))]
    ends = free[np.concatenate((breaks, [free.size - 1]))]
    widths = ends - starts + 1
    wide = np.flatnonzero(widths >= 0.5 * size)
    if side == 0 or wide.size == 0:
        pick = int(widths.argmax())
        return a + (starts[pick] + ends[pick] + 1) / 2, float(widths[pick])
    # The run may continue into the plot (columns that hold nothing but an
    # axis line): cut at its labels' end, not in its middle.
    pick = int(wide[-1] if side > 0 else wide[0])
    inset = min(float(widths[pick]), size) / 2
    at = ends[pick] + 1 - inset if side > 0 else starts[pick] + inset
    return a + at, float(widths[pick])


def _ink_box(mask: np.ndarray, cell: Box) -> Box:
    """*cell* shrunk to the ink inside it."""
    x0, y0, x1, y1 = (round(v) for v in cell)
    sub = mask[y0:y1, x0:x1]
    if not sub.any():
        return cell
    rows = np.flatnonzero(sub.any(axis=1))
    cols = np.flatnonzero(sub.any(axis=0))
    return (
        float(x0 + cols[0]),
        float(y0 + rows[0]),
        float(x0 + cols[-1] + 1),
        float(y0 + rows[-1] + 1),
    )


def ink_mask(image: np.ndarray) -> np.ndarray:
    """Pixels that differ from the background."""
    difference = np.abs(image.astype(int) - background_colour(image))
    return difference.max(axis=2) > _INK_DIFF


def background_colour(image: np.ndarray) -> np.ndarray:
    """The median colour of the image border."""
    border = np.concatenate(
        [image[0], image[-1], image[:, 0], image[:, -1]], axis=0
    ).astype(int)
    return np.median(border, axis=0)


def _xy_cut(mask: np.ndarray, box: tuple[int, int, int, int], depth: int) -> list[Box]:
    x0, y0, x1, y1 = box
    sub = mask[y0:y1, x0:x1]
    if not sub.any():
        return []
    rows = np.flatnonzero(sub.any(axis=1))
    cols = np.flatnonzero(sub.any(axis=0))
    x0, x1 = x0 + int(cols[0]), x0 + int(cols[-1]) + 1
    y0, y1 = y0 + int(rows[0]), y0 + int(rows[-1]) + 1
    if depth >= _MAX_DEPTH:
        return [(float(x0), float(y0), float(x1), float(y1))]
    height, width = mask.shape
    for axis in (1, 0) if depth % 2 == 0 else (0, 1):
        profile = mask[y0:y1, x0:x1].sum(axis=axis)
        side = height if axis == 1 else width
        length = (x1 - x0) if axis == 1 else (y1 - y0)
        runs = _content_runs(
            profile > max(1, _GUTTER_MAX_INK * length),
            max(3, round(GUTTER_FRACTION * side)),
        )
        if len(runs) > 1:
            out: list[Box] = []
            for start, end in runs:
                child = (
                    (x0, y0 + start, x1, y0 + end)
                    if axis == 1
                    else (x0 + start, y0, x0 + end, y1)
                )
                out.extend(_xy_cut(mask, child, depth + 1))
            return out
    return [(float(x0), float(y0), float(x1), float(y1))]


def _content_runs(filled_rows: np.ndarray, min_gap: int) -> list[tuple[int, int]]:
    """Spans of *filled_rows* separated by at least *min_gap* empty entries."""
    filled = np.flatnonzero(filled_rows)
    if filled.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = prev = int(filled[0])
    for index in filled[1:]:
        if index - prev - 1 >= min_gap:
            runs.append((start, prev + 1))
            start = int(index)
        prev = int(index)
    runs.append((start, prev + 1))
    return runs


def _is_graphic(mask: np.ndarray, box: Box, width: int, height: int) -> bool:
    """A chart block holds a long straight ink run (an axis, a frame, a
    filled area) or one large connected component (a pie, a plot
    background); text and legends hold neither. Very elongated blocks
    (a framed legend row) are not panels."""
    x0, y0, x1, y1 = (round(v) for v in box)
    bw, bh = x1 - x0, y1 - y0
    if bw <= 0 or bh <= 0 or max(bw / bh, bh / bw) > _MAX_ASPECT:
        return False
    sub = mask[y0:y1, x0:x1]
    min_w = max(_GRAPHIC_SPAN * bw, _GRAPHIC_MIN_SIDE * width)
    min_h = max(_GRAPHIC_SPAN * bh, _GRAPHIC_MIN_SIDE * height)
    if _longest_run(sub) >= min_h or _longest_run(sub.T) >= min_w:
        return True
    labels, count = ndimage.label(sub)
    for sl in ndimage.find_objects(labels) if count else []:
        if sl is None:
            continue
        if sl[1].stop - sl[1].start >= min_w or sl[0].stop - sl[0].start >= min_h:
            return True
    return False


def _longest_run(mask: np.ndarray) -> int:
    """Longest run of ink down any column of *mask*."""
    padded = np.zeros((mask.shape[0] + 2, mask.shape[1]), dtype=np.int8)
    padded[1:-1] = mask
    edges = np.diff(padded, axis=0)
    starts = np.argwhere(edges == 1)
    ends = np.argwhere(edges == -1)
    if starts.size == 0:
        return 0
    order_s = np.lexsort((starts[:, 0], starts[:, 1]))
    order_e = np.lexsort((ends[:, 0], ends[:, 1]))
    return int((ends[order_e, 0] - starts[order_s, 0]).max())


def _attach_text(
    graphic: list[Box], texts: list[Box], width: int, height: int
) -> list[Box]:
    """Grow a panel by a text block next to it (its title, axis title or
    side legend): the block lies within a small gap above, below or beside
    exactly one panel, or much closer to one than to any other."""
    out = list(graphic)
    for text in texts:
        gaps: list[tuple[float, int]] = []
        reach = 3 * GUTTER_FRACTION * max(width, height)
        for index, g in enumerate(out):
            x_overlap = _overlap(text, g, 0) / max(text[2] - text[0], 1.0)
            y_overlap = _overlap(text, g, 1) / max(text[3] - text[1], 1.0)
            vertical_gap = max(g[1] - text[3], text[1] - g[3])
            side_gap = max(g[0] - text[2], text[0] - g[2])
            if x_overlap >= 0.5 and y_overlap >= 0.5:
                gaps.append((0.0, index))
            elif x_overlap >= 0.6 and 0 <= vertical_gap <= reach:
                gaps.append((vertical_gap, index))
            elif y_overlap >= 0.5 and 0 <= side_gap <= reach:
                gaps.append((side_gap, index))
        gaps.sort()
        if not gaps or (len(gaps) > 1 and gaps[1][0] < 2 * gaps[0][0] + 2):
            continue
        g = out[gaps[0][1]]
        out[gaps[0][1]] = (
            min(g[0], text[0]),
            min(g[1], text[1]),
            max(g[2], text[2]),
            max(g[3], text[3]),
        )
    return out


def _letters(words: list[Word]) -> list[tuple[str, Word]]:
    found: dict[str, Word] = {}
    for word in words:
        match = _LETTER.match(word.text.strip())
        if match is None:
            continue
        letter = match.group(1).lower()
        if letter not in found or (word.cy, word.cx) < (
            found[letter].cy,
            found[letter].cx,
        ):
            found[letter] = word
    return sorted(found.items())


def _heads_a_block(word: Word, blocks: list[Box], width: int, height: int) -> bool:
    """A panel letter sits at the top-left of a panel (inside or just
    outside it); a single-letter category label under an axis does not."""
    reach = 6 * GUTTER_FRACTION * max(width, height)
    return any(
        b[0] - reach <= word.cx <= b[0] + 0.5 * (b[2] - b[0])
        and b[1] - reach <= word.cy <= b[1] + 0.2 * (b[3] - b[1])
        for b in blocks
    )


def _name(blocks: list[Box], letters: list[tuple[str, Word]]) -> list[PanelBox]:
    ordered = _reading_order(blocks)
    owners: list[str | None] = []
    for block in ordered:
        cx, cy = (block[0] + block[2]) / 2, (block[1] + block[3]) / 2
        above_left = [c for c, w in letters if w.cx <= cx and w.cy <= cy]
        owners.append(max(above_left) if above_left else None)
    if len(ordered) == 1 and not letters:
        return [PanelBox(id="1", bbox=ordered[0])]
    # OCR often loses the "a" in the very corner: panels before the first
    # letter found belong to the letter before it.
    if letters and letters[0][0] not in "aA":
        first = chr(ord(letters[0][0]) - 1)
        owners = [first if o is None else o for o in owners]
    panels: list[PanelBox] = []
    for index, (block, owner) in enumerate(zip(ordered, owners)):
        if owner is None:
            panels.append(PanelBox(id=str(index + 1), bbox=block))
            continue
        siblings = [i for i, o in enumerate(owners) if o == owner]
        panel_id = (
            owner if len(siblings) == 1 else f"{owner}{siblings.index(index) + 1}"
        )
        panels.append(PanelBox(id=panel_id, bbox=block, letter=owner))
    return panels


def _with_letters(
    panels: list[PanelBox], letters: dict[str, Word], width: int, height: int
) -> list[PanelBox]:
    """Grow a panel named by a letter of its own to take in that letter when
    it sits just outside its top-left corner."""
    reach = 6 * GUTTER_FRACTION * max(width, height)
    for panel in panels:
        word = letters.get(panel.id)
        if word is None:
            continue
        x0, y0, x1, y1 = panel.bbox
        if x0 - reach <= word.bbox[0] <= x1 and y0 - reach <= word.bbox[1] <= y0:
            panel.bbox = (min(x0, word.bbox[0]), word.bbox[1], x1, y1)
    return panels


def _reading_order(blocks: list[Box]) -> list[Box]:
    """Rows of blocks top to bottom (a block joins a row when it overlaps
    the row's vertical span by half its height), each row left to right."""
    rows: list[list[Box]] = []
    for block in sorted(blocks, key=lambda b: b[1]):
        for row in rows:
            top = min(b[1] for b in row)
            bottom = max(b[3] for b in row)
            overlap = min(bottom, block[3]) - max(top, block[1])
            if overlap >= 0.5 * (block[3] - block[1]):
                row.append(block)
                break
        else:
            rows.append([block])
    return [b for row in rows for b in sorted(row, key=lambda b: b[0])]


def _letter_grid(
    letters: list[tuple[str, Word]], width: int, height: int
) -> list[PanelBox]:
    """Cells spanned by the panel letters: rows of letters at the same
    height, each letter's cell reaching to the next letter on the right and
    to the next row."""
    tol = 0.05 * height
    rows: list[list[tuple[str, Word]]] = []
    for letter in sorted(letters, key=lambda lw: lw[1].cy):
        if rows and abs(rows[-1][0][1].cy - letter[1].cy) <= tol:
            rows[-1].append(letter)
        else:
            rows.append([letter])
    panels: list[PanelBox] = []
    for r, row in enumerate(rows):
        top = min(w.bbox[1] for _, w in row)
        bottom = min(w.bbox[1] for _, w in rows[r + 1]) if r + 1 < len(rows) else height
        row.sort(key=lambda lw: lw[1].cx)
        for i, (char, word) in enumerate(row):
            right = row[i + 1][1].bbox[0] if i + 1 < len(row) else width
            panels.append(
                PanelBox(
                    id=char,
                    bbox=(
                        max(0.0, word.bbox[0]),
                        max(0.0, top),
                        float(right),
                        float(bottom),
                    ),
                    letter=char,
                )
            )
    return panels


def _ink_density(mask: np.ndarray, box: Box) -> float:
    x0, y0, x1, y1 = (round(v) for v in box)
    sub = mask[y0:y1, x0:x1]
    return float(sub.mean()) if sub.size else 0.0


def _centre_in(word: Word, box: Box) -> bool:
    return box[0] <= word.cx <= box[2] and box[1] <= word.cy <= box[3]


def _overlap(a: Box, b: Box, axis: int) -> float:
    """Overlap of *a* and *b* along x (*axis* 0) or y (1)."""
    return max(0.0, min(a[2 + axis], b[2 + axis]) - max(a[axis], b[axis]))


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
