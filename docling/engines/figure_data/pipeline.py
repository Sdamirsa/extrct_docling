# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Run one figure through ``simple`` or ``measured`` mode.

``measured``, per panel: the vector reader when the figure is drawn with
paths; otherwise one grounded VLM call whose pointed marks go through the
panel's axis maps (bar ends snapped to pixel edges first), the model's own
number kept where no axis map exists. Printed labels found among the
figure's words then replace measured values, and :mod:`.verify` sets the
confidence. ``simple``: one VLM call on the whole figure.
"""

from __future__ import annotations

import logging
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
from docling_core.types.doc import DoclingDocument
from PIL import Image

from docling.engines.figure_data.eligibility import is_eligible, rows_from_document
from docling.engines.figure_data.evidence import (
    AxisMap,
    BundleSource,
    PanelAxes,
    build_job,
    find_axes,
    parse_number,
    words_in,
)
from docling.engines.figure_data.panels import PanelBox, split_panels
from docling.engines.figure_data.publish import attach_results, write_figure_outputs
from docling.engines.figure_data.readers.raster import refine_edge
from docling.engines.figure_data.readers.vector import read_vector_panel
from docling.engines.figure_data.readers.vlm import (
    GRID,
    PANEL_BOXES_PROMPT,
    GroundedResponse,
    OllamaClient,
    OllamaError,
    PanelBoxesResponse,
    SimpleResponse,
    VlmAxis,
    VlmPanel,
    fit_image,
    grid_to_px,
    grounded_prompt,
    simple_prompt,
)
from docling.engines.figure_data.schema import (
    Axes,
    Axis,
    Box,
    CallTiming,
    ChartData,
    FigureDataOptions,
    FigureDataResult,
    FigureJob,
    Labeler,
    OverlayPoint,
    Panel,
    PanelRead,
    PlacedValue,
    Series,
    Value,
    Word,
)
from docling.engines.figure_data.verify import (
    BASE_CONFIDENCE,
    apply_printed,
    check_labels,
    merge_samples,
    pair_printed_labels,
    verify_panel,
)
from docling.engines.picture_filter import PictureNoiseFlag

_log = logging.getLogger(__name__)

FIGURE_DATA_DIRNAME = "figure_data"
_BAR_KINDS = {"bar", "stacked_bar", "grouped_bar"}
_XY_KINDS = {"line", "scatter", "kaplan_meier"}
_SNAP_WINDOW = 0.04


def eligible_refs(bundle: BundleSource, options: FigureDataOptions) -> list[str]:
    return [ref for ref, row in bundle.rows.items() if is_eligible(row, options)]


def read_bundle(
    bundle: BundleSource,
    refs: list[str],
    options: FigureDataOptions,
    *,
    out_dir: Path,
    client: OllamaClient | None,
    work_dir: Path | None = None,
    on_result: Callable[[FigureDataResult], None] | None = None,
) -> list[FigureDataResult]:
    """Read the figures *refs* of *bundle*; each record and overlay is
    written to *out_dir* as soon as it is read, the work images to
    *work_dir* (default *out_dir*)."""
    results: list[FigureDataResult] = []
    for ref in refs:
        try:
            job = build_job(
                bundle, ref, work_dir=work_dir or out_dir, crop_dpi=options.crop_dpi
            )
        except ValueError as exc:
            _log.warning("figure data: %s skipped: %s", ref, exc)
            continue
        result = read_figure(job, options, client)
        if client is not None:
            try:
                result.ollama_ps = client.ps()
            except OllamaError as exc:
                result.issues.append(f"ollama ps failed: {exc}")
        write_figure_outputs(result, job.crop_path, out_dir)
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results


def read_document(
    doc: DoclingDocument,
    pdf_dir: Path,
    *,
    picture_images: list[Path],
    noise_flags: list[PictureNoiseFlag],
    pdf_path: Path | None,
    options: FigureDataOptions,
) -> list[FigureDataResult]:
    """The conversion-time stage: read the eligible figures of a document
    whose crops are written, store the records under
    ``<pdf_dir>/figure_data/`` and attach them to the pictures of *doc*."""
    rows = rows_from_document(doc, pdf_dir, picture_images, noise_flags)
    bundle = BundleSource(
        dir=pdf_dir, doc=doc, rows={r.self_ref: r for r in rows}, pdf_path=pdf_path
    )
    client = OllamaClient(options.ollama_url, timeout_s=options.request_timeout_s)
    # The work images (up to 3200 px renders) stay out of the bundle.
    with tempfile.TemporaryDirectory(prefix="figure_data_") as work_dir:
        try:
            results = read_bundle(
                bundle,
                eligible_refs(bundle, options),
                options,
                out_dir=pdf_dir / FIGURE_DATA_DIRNAME,
                client=client,
                work_dir=Path(work_dir),
            )
        finally:
            client.close()
    attach_results(doc, results, min_confidence=options.min_confidence_for_markdown)
    return results


def read_figure(
    job: FigureJob, options: FigureDataOptions, client: OllamaClient | None
) -> FigureDataResult:
    """Read *job* in ``options.mode``; a figure the model cannot be asked
    about (no client, Ollama down) keeps what the vector reader found."""
    started = time.perf_counter()
    reader = _Reader(job, options, client)
    if options.mode == "simple":
        panels = reader.simple()
    else:
        panels = reader.measured()
    issues = reader.issues
    for panel in panels:
        region = reader.panel_regions.get(panel.id)
        panel_words = words_in(job.words, region) if region is not None else job.words
        if region is not None:
            pair_printed_labels(panel, panel_words, find_axes(panel_words, region))
        issues.extend(apply_printed(panel, panel_words))
        issues.extend(check_labels(panel, job.words))
        issues.extend(verify_panel(panel))
    chart = ChartData(
        figure=job.figure,
        source_kind=job.source_kind,
        panels=panels,
        labeler=Labeler(
            kind="engine",
            name=f"extrct figure-data {options.mode} ({options.model})",
            date=time.strftime("%Y-%m-%d"),
        ),
    )
    return FigureDataResult(
        chart_data=chart,
        mode=options.mode,
        model=options.model if client is not None else None,
        panel_split=reader.split_method,
        seconds=round(time.perf_counter() - started, 2),
        calls=reader.calls,
        issues=issues,
        overlay=reader.overlay,
    )


class _Reader:
    def __init__(
        self, job: FigureJob, options: FigureDataOptions, client: OllamaClient | None
    ) -> None:
        self.job = job
        self.options = options
        self.client = client
        self.image = Image.open(job.image_path).convert("RGB")
        self.pixels = np.asarray(self.image)
        self.calls: list[CallTiming] = []
        self.issues: list[str] = []
        self.overlay: list[OverlayPoint] = []
        self.panel_regions: dict[str, Box] = {}
        self.split_method: str | None = None
        self.started = time.perf_counter()

    # -- simple ---------------------------------------------------------------

    def simple(self) -> list[Panel]:
        if self.client is None:
            self.issues.append("simple mode needs the VLM; no client")
            return []
        full: Box = (0.0, 0.0, float(self.image.width), float(self.image.height))
        reads: list[list[Panel]] = []
        for sample in range(self.options.samples):
            try:
                response, timing = self.client.chat_json(
                    SimpleResponse,
                    model=self.options.model,
                    prompt=simple_prompt(self.job.words, full),
                    images=[fit_image(self.image, self.options.vlm_max_side_px)],
                    options=self._chat_options(sample),
                    keep_alive=self.options.keep_alive,
                    label="simple",
                )
            except OllamaError as exc:
                self.issues.append(f"simple read failed: {exc}")
                continue
            self.calls.append(timing)
            _unique_ids(response.panels)
            reads.append([self._simple_panel(p, full) for p in response.panels])
        self.split_method = "vlm"
        return merge_samples(reads) if reads else []

    def _simple_panel(self, vlm: VlmPanel, full: Box) -> Panel:
        box = _grid_box(vlm.box, full)
        self.panel_regions[vlm.id] = box
        data = [
            Value(
                category=row.category,
                x=_x_value(row.x),
                series=row.series,
                value=row.value,
                err_lo=row.err_lo,
                err_hi=row.err_hi,
                label_printed=row.label_printed,
                source="vlm",
                confidence=BASE_CONFIDENCE["vlm"],
            )
            for row in vlm.rows
        ]
        return Panel(
            id=vlm.id,
            bbox_px=self.job.to_crop(box),
            title=vlm.title,
            kind=vlm.kind,
            orientation=vlm.orientation,
            axes=Axes(x=_axis(vlm.x_axis, None), y=_axis(vlm.y_axis, None)),
            series=[Series(name=s.name, color=s.color) for s in vlm.series],
            data=data,
        )

    # -- measured -------------------------------------------------------------

    def measured(self) -> list[Panel]:
        split = split_panels(
            self.pixels,
            self.job.words,
            mode=self.options.panel_split,
            box_reader=self._panel_boxes if self.client is not None else None,
        )
        self.split_method = split.method
        self.issues.extend(split.notes)
        inside = [w for p in split.panels for w in words_in(self.job.words, p.bbox)]
        shared = [w.text for w in self.job.words if w not in inside]
        panels: list[Panel] = []
        for panel_box in split.panels:
            self.panel_regions[panel_box.id] = panel_box.bbox
            panels.append(self._measure_panel(panel_box, shared))
        return panels

    def _panel_boxes(self) -> list[tuple[str, Box]]:
        assert self.client is not None
        full: Box = (0.0, 0.0, float(self.image.width), float(self.image.height))
        try:
            response, timing = self.client.chat_json(
                PanelBoxesResponse,
                model=self.options.model,
                prompt=PANEL_BOXES_PROMPT,
                images=[fit_image(self.image, self.options.vlm_max_side_px)],
                options=self._chat_options(0),
                keep_alive=self.options.keep_alive,
                label="panel_boxes",
            )
        except OllamaError as exc:
            self.issues.append(f"panel boxes failed: {exc}")
            return []
        self.calls.append(timing)
        return [(b.id, _grid_box(b.box, full)) for b in response.panels]

    def _measure_panel(self, panel_box: PanelBox, shared: list[str]) -> Panel:
        region = panel_box.bbox
        words = words_in(self.job.words, region)
        axes = find_axes(words, region)
        vector = (
            read_vector_panel(self.job.marks, self.job.words, region, axes)
            if self.job.source_kind in ("vector", "mixed")
            else None
        )
        if vector is not None:
            return self._from_vector(panel_box, vector, axes)
        grounded: list[GroundedResponse] = []
        if self.client is not None and not self._over_budget():
            for sample in range(self.options.samples):
                response = self._grounded(panel_box, words, axes, shared, sample)
                if response is not None:
                    grounded.append(response)
        elif self.client is not None:
            self.issues.append(f"panel {panel_box.id}: time budget spent, VLM skipped")
        reads = [self._from_grounded(panel_box, g, axes) for g in grounded]
        if not reads:
            return Panel(
                id=panel_box.id, bbox_px=self.job.to_crop(region), notes=["not read"]
            )
        return merge_samples([[r] for r in reads])[0]

    def _grounded(
        self,
        panel_box: PanelBox,
        words: list[Word],
        axes: PanelAxes,
        shared: list[str],
        sample: int,
    ) -> GroundedResponse | None:
        assert self.client is not None
        region = panel_box.bbox
        x0, y0, x1, y1 = (round(v) for v in region)
        crop = self.image.crop((x0, y0, x1, y1))
        try:
            response, timing = self.client.chat_json(
                GroundedResponse,
                model=self.options.model,
                prompt=grounded_prompt(
                    words, region, axis_hint=_axis_hint(axes, region), shared=shared
                ),
                images=[fit_image(crop, self.options.vlm_max_side_px)],
                options=self._chat_options(sample),
                keep_alive=self.options.keep_alive,
                label="grounded",
                panel=panel_box.id,
            )
        except OllamaError as exc:
            self.issues.append(f"panel {panel_box.id}: grounded read failed: {exc}")
            return None
        self.calls.append(timing)
        return response

    def _from_grounded(
        self, panel_box: PanelBox, g: GroundedResponse, axes: PanelAxes
    ) -> Panel:
        region = panel_box.bbox
        x0, y0, x1, y1 = region
        width, height = x1 - x0, y1 - y0
        horizontal = g.orientation == "horizontal" or g.kind == "forest"
        value_map = _numeric(axes.x if horizontal else axes.y)
        snap = g.kind in _BAR_KINDS and self.job.source_kind != "vector"
        data: list[Value] = []
        for point in g.points:
            px = grid_to_px(point.px, x0, width)
            py = grid_to_px(point.py, y0, height)
            value: float | None = None
            basis = "vlm"
            err_lo = point.err_lo
            err_hi = point.err_hi
            if (
                value_map is not None
                and px is not None
                and py is not None
                and g.kind != "pie"
            ):
                end = px if horizontal else py
                start = (
                    grid_to_px(
                        point.start_pos,
                        x0 if horizontal else y0,
                        width if horizontal else height,
                    )
                    if point.start_pos is not None
                    else None
                )
                snapped = False
                if snap:
                    end, snapped = self._snap(
                        px, py, end, start, horizontal, width if horizontal else height
                    )
                far = value_map.value_at(end)
                near = value_map.value_at(start) if start is not None else None
                if far is not None:
                    value = (
                        far - near
                        if near is not None and g.kind == "stacked_bar"
                        else far
                    )
                    basis = "raster_snapped" if snapped else "raster"
                origin = x0 if horizontal else y0
                size = width if horizontal else height
                lo = grid_to_px(point.lo_pos, origin, size)
                hi = grid_to_px(point.hi_pos, origin, size)
                ends = [
                    v
                    for v in (
                        value_map.value_at(lo) if lo is not None else None,
                        value_map.value_at(hi) if hi is not None else None,
                    )
                    if v is not None
                ]
                if len(ends) == 2:
                    err_lo, err_hi = min(ends), max(ends)
            if value is None:
                value = point.value
                basis = "vlm"
            category, x = point.category, _x_value(point.x)
            if g.kind in _XY_KINDS and px is not None and axes.x is not None:
                at = _x_from_axis(axes.x, px)
                if isinstance(at, str):
                    category, x = at, None
                elif at is not None:
                    category, x = None, at
            label = category or x or ""
            if px is not None and py is not None:
                self.overlay.append(
                    OverlayPoint(
                        panel=panel_box.id,
                        x=round(px / self.job.px_per_crop, 1),
                        y=round(py / self.job.px_per_crop, 1),
                        label=f"{label}:{_short(value)}",
                    )
                )
            data.append(
                Value(
                    category=category,
                    x=x,
                    series=point.series,
                    value=_round(value),
                    err_lo=_round(err_lo),
                    err_hi=_round(err_hi),
                    label_printed=point.label_printed,
                    source="vlm" if basis == "vlm" else "raster",
                    confidence=BASE_CONFIDENCE[basis],
                )
            )
        notes = []
        if value_map is None and g.kind != "pie":
            notes.append("no axis calibrated from tick labels; values are the model's")
        return Panel(
            id=panel_box.id,
            bbox_px=self.job.to_crop(region),
            title=g.title,
            kind=g.kind,
            orientation=g.orientation,
            axes=Axes(x=_axis(g.x_axis, axes.x), y=_axis(g.y_axis, axes.y)),
            series=[Series(name=s.name, color=s.color) for s in g.series],
            data=data,
            notes=notes,
        )

    def _snap(
        self,
        px: float,
        py: float,
        end: float,
        start: float | None,
        horizontal: bool,
        extent: float,
    ) -> tuple[float, bool]:
        """Snap a bar end to the colour edge it points at; the fill lies on
        the start side (or towards the axis origin)."""
        orientation = "horizontal" if horizontal else "vertical"
        if start is not None:
            inward = 1 if start > end else -1
        else:
            inward = -1 if horizontal else 1
        edge = refine_edge(
            self.pixels,
            px,
            py,
            orientation,
            window=_SNAP_WINDOW * extent,
            inward=inward,
        )
        return (edge, True) if edge is not None else (end, False)

    def _from_vector(
        self,
        panel_box: PanelBox,
        vector: PanelRead,
        axes: PanelAxes,
    ) -> Panel:
        """The vector reader's panel; no model call (the title is the top
        text line of the panel)."""
        data: list[Value] = []
        numbers = [p.value.value for p in vector.values if p.value.value is not None]
        span = (max(numbers) - min(min(numbers), 0.0)) if numbers else 0.0
        for placed in vector.values:
            row = placed.value.model_copy(
                update={"confidence": BASE_CONFIDENCE["vector"]}
            )
            row.label_printed = _printed_near(
                placed, self.job.words, panel_box.bbox, span
            )
            data.append(row)
            self._overlay(panel_box.id, placed)
        return Panel(
            id=panel_box.id,
            bbox_px=self.job.to_crop(panel_box.bbox),
            title=_top_line(words_in(self.job.words, panel_box.bbox), panel_box.bbox),
            kind=vector.kind,
            orientation=vector.orientation,
            axes=None
            if vector.kind == "pie"
            else Axes(x=_calibrated(axes.x, None), y=_calibrated(axes.y, None)),
            series=vector.series,
            data=data,
            notes=vector.notes,
        )

    def _overlay(self, panel: str, placed: PlacedValue) -> None:
        if placed.x_px is None or placed.y_px is None:
            return
        v = placed.value
        self.overlay.append(
            OverlayPoint(
                panel=panel,
                x=round(placed.x_px / self.job.px_per_crop, 1),
                y=round(placed.y_px / self.job.px_per_crop, 1),
                label=f"{v.category or v.x or ''}:{_short(v.value)}",
            )
        )

    def _chat_options(self, sample: int) -> dict[str, object]:
        options: dict[str, object] = {
            "num_ctx": self.options.num_ctx,
            "num_predict": self.options.max_output_tokens,
        }
        if self.options.samples > 1:
            options.update(temperature=0.4, seed=sample + 1)
        else:
            options["temperature"] = 0
        return options

    def _over_budget(self) -> bool:
        return (
            time.perf_counter() - self.started > self.options.time_budget_s_per_figure
        )


def _x_from_axis(axis: AxisMap, px: float) -> float | str | None:
    """The x of a pointed mark from the calibrated x axis: the categorical
    tick under it, or the numeric value, snapped to a tick within a quarter
    of the tick spacing (line charts plot at their ticks)."""
    if axis.scale == "categorical":
        return axis.category_at(px)
    value = axis.value_at(px)
    if value is None:
        return None
    positions = sorted(pos for pos, _ in axis.ticks)
    spacing = float(np.median(np.diff(positions))) if len(positions) > 1 else 0.0
    tick_pos, tick = min(axis.ticks, key=lambda t: abs(t[0] - px))
    if isinstance(tick, float) and abs(tick_pos - px) <= 0.25 * spacing:
        return tick
    return round(value, 4)


def _top_line(words: list[Word], region: Box) -> str | None:
    """The text in the top tenth of a panel (its title, when it has one)."""
    top = region[1] + 0.1 * (region[3] - region[1])
    line = sorted(
        (w for w in words if w.cy <= top), key=lambda w: (round(w.cy / 4), w.cx)
    )
    return " ".join(w.text for w in line) or None


def _unique_ids(panels: list[VlmPanel]) -> None:
    """Number repeated panel ids (a small model calls every panel "a")."""
    seen: dict[str, int] = {}
    for panel in panels:
        count = seen.get(panel.id, 0) + 1
        seen[panel.id] = count
        if count > 1:
            panel.id = f"{panel.id}{count}"


def _printed_near(
    placed: PlacedValue, words: list[Word], region: Box, span: float
) -> str | None:
    """A number printed near a measured mark that agrees with it (within
    3 % of the data span, at least 1 unit on spans of 10 or more): the
    label the figure prints for it."""
    if placed.x_px is None or placed.y_px is None or placed.value.value is None:
        return None
    reach = 0.3 * min(region[2] - region[0], region[3] - region[1])
    tolerance = max(0.03 * span, 1.0) if span >= 10 else 0.03 * max(span, 1e-9)
    best: tuple[float, str] | None = None
    for word in words:
        number = parse_number(word.text)
        if number is None or abs(number - placed.value.value) > tolerance:
            continue
        distance = ((word.cx - placed.x_px) ** 2 + (word.cy - placed.y_px) ** 2) ** 0.5
        if distance <= reach and (best is None or distance < best[0]):
            best = (distance, word.text)
    return best[1] if best is not None else None


def _grid_box(box: list[int], full: Box) -> Box:
    x0, y0, x1, y1 = (min(max(v, 0), GRID) / GRID for v in box)
    width, height = full[2], full[3]
    return (
        min(x0, x1) * width,
        min(y0, y1) * height,
        max(x0, x1) * width,
        max(y0, y1) * height,
    )


def _numeric(axis: AxisMap | None) -> AxisMap | None:
    return axis if axis is not None and axis.scale != "categorical" else None


def _axis(vlm: VlmAxis, calibrated: AxisMap | None) -> Axis | None:
    model_range = (
        [vlm.min, vlm.max] if vlm.min is not None and vlm.max is not None else None
    )
    return _calibrated(
        calibrated,
        Axis(name=vlm.name, unit=vlm.unit, scale=vlm.scale, range=model_range),
    )


def _calibrated(calibrated: AxisMap | None, model: Axis | None) -> Axis | None:
    """The model's axis (name, unit) with scale, range and ticks from the
    tick labels when they were calibrated."""
    if calibrated is None:
        return model
    axis = model.model_copy() if model is not None else Axis()
    axis.scale = calibrated.scale
    axis.ticks = [label for _, label in calibrated.ticks]
    span = calibrated.value_range
    if span is not None:
        axis.range = [span[0], span[1]]
    return axis


def _axis_hint(axes: PanelAxes, region: Box) -> str | None:
    parts: list[str] = []
    x0, y0, x1, y1 = region
    for name, axis, origin, size in (
        ("y", axes.y, y0, y1 - y0),
        ("x", axes.x, x0, x1 - x0),
    ):
        if axis is None or axis.scale == "categorical":
            continue
        ticks = ", ".join(
            f"{label:g} at {round((pos - origin) / size * GRID)}"
            for pos, label in axis.ticks
            if isinstance(label, float)
        )
        parts.append(f"{name} ({axis.scale}): {ticks}")
    return "; ".join(parts) or None


def _x_value(text: str | None) -> float | str | None:
    if text is None:
        return None
    number = parse_number(text)
    return number if number is not None else text


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _short(value: float | None) -> str:
    return "?" if value is None else f"{value:.3g}"
