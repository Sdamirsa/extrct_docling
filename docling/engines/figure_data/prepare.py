# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Phase 1 of the figure-to-data step: prepare each chart candidate of a
bundle for a reader. No model is involved.

``<bundle>/figure-to-data/`` (or the folder given as *step_dir*)::

    prepare.json            every picture of the paper: prepared, or why not
    pictures_3/
        figure.png          the figure, captured at high resolution from the PDF
        figure.txt          what a reader needs beside the image, condensed
        evidence.json       the same evidence for code: words with their boxes,
                            the charts found, the PDF's drawing paths
        panel-1.png ...     one crop per chart, when the figure holds several

Every reading method works from this folder alone, so a method can be
swapped or rerun without touching the PDF again, and what a model was
given can be looked at afterwards.
"""

from __future__ import annotations

import logging
import re
import shutil
import time
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from docling.engines.figure_data.eligibility import is_eligible
from docling.engines.figure_data.evidence import (
    AxisMap,
    BundleSource,
    FigureRow,
    build_job,
    find_axes,
    job_stem,
    words_in,
)
from docling.engines.figure_data.panels import split_panels
from docling.engines.figure_data.readers.vlm import words_block
from docling.engines.figure_data.schema import (
    Box,
    Figure,
    FigureDataOptions,
    FigureJob,
    SourceKind,
    VectorMark,
    Word,
)

_log = logging.getLogger(__name__)

STEP_DIRNAME = "figure-to-data"
# The revision of the step that wrote a folder: 3 = the three-method step.
STEP_VERSION = "3"
PREPARE_FILENAME = "prepare.json"
IMAGE_FILENAME = "figure.png"
CONTEXT_FILENAME = "figure.txt"
EVIDENCE_FILENAME = "evidence.json"
PREPARED_SCHEMA = "extrct.figure-prep/1"
MANIFEST_SCHEMA = "extrct.figure-prep-manifest/1"
_CONTEXT_WORDS = 400
_UNSAFE = re.compile(r"[^\w-]+")

Capture = Literal["pdf-render", "embedded-bitmap", "bundle-crop"]


class PreparedPanel(BaseModel):
    """One chart of the figure, as the layout analysis found it; ``bbox`` in
    pixels of ``figure.png``."""

    id: str
    bbox: Box
    image: str | None = None
    x_axis: str | None = None
    y_axis: str | None = None


class PreparedFigure(BaseModel):
    """``evidence.json``: one prepared figure."""

    model_config = ConfigDict(validate_by_name=True, serialize_by_alias=True)

    schema_id: str = Field(default=PREPARED_SCHEMA, alias="schema")
    step_version: str = STEP_VERSION
    figure: Figure
    image: str = IMAGE_FILENAME
    width: int
    height: int
    capture: Capture
    px_per_crop: float = 1.0
    source_kind: SourceKind = "unknown"
    figure_type: str | None = None
    caption: str | None = None
    split_method: str = "single"
    split_notes: list[str] = Field(default_factory=list)
    panels: list[PreparedPanel] = Field(default_factory=list)
    words: list[Word] = Field(default_factory=list)
    marks: list[VectorMark] = Field(default_factory=list)
    image_objects: int = 0

    @classmethod
    def load(cls, figure_dir: Path) -> PreparedFigure:
        return cls.model_validate_json(
            (figure_dir / EVIDENCE_FILENAME).read_text(encoding="utf-8")
        )

    @property
    def full(self) -> Box:
        return (0.0, 0.0, float(self.width), float(self.height))

    def panel(self, panel_id: str) -> PreparedPanel | None:
        wanted = panel_id.strip().casefold()
        return next((p for p in self.panels if p.id.casefold() == wanted), None)

    def job(self, figure_dir: Path) -> FigureJob:
        """The evidence as the measured engine takes it."""
        image = figure_dir / self.image
        return FigureJob(
            figure=self.figure,
            crop_path=image,
            image_path=image,
            px_per_crop=self.px_per_crop,
            native_bitmap=self.capture == "embedded-bitmap",
            figure_type=self.figure_type,
            caption=self.caption,
            words=self.words,
            marks=self.marks,
            image_objects=self.image_objects,
            source_kind=self.source_kind,
        )

    def to_crop(self, box: Box) -> list[float]:
        return [round(v / self.px_per_crop, 1) for v in box]


class PrepareRow(BaseModel):
    """One picture of the paper in ``prepare.json``."""

    self_ref: str
    status: Literal["prepared", "skipped"]
    folder: str | None = None
    reason: str | None = None
    page: int | None = None
    figure_type: str | None = None
    capture: Capture | None = None
    size_px: list[int] | None = None
    source_kind: SourceKind | None = None
    charts: int | None = None
    words: int | None = None


class PrepareManifest(BaseModel):
    """``prepare.json``: what the prepare phase did for one bundle."""

    model_config = ConfigDict(validate_by_name=True, serialize_by_alias=True)

    schema_id: str = Field(default=MANIFEST_SCHEMA, alias="schema")
    step_version: str = STEP_VERSION
    bundle: str
    pdf: str | None = None
    prepared_at: str = ""
    crop_dpi: int = 220
    panel_split: str = "auto"
    # The pictures that were asked for; None: every chart candidate.
    selection: list[str] | None = None
    figures: list[PrepareRow] = Field(default_factory=list)

    @property
    def prepared(self) -> list[PrepareRow]:
        return [row for row in self.figures if row.status == "prepared"]


def load_manifest(step_dir: Path) -> PrepareManifest | None:
    path = step_dir / PREPARE_FILENAME
    if not path.is_file():
        return None
    return PrepareManifest.model_validate_json(path.read_text(encoding="utf-8"))


def prepare_bundle(
    bundle: BundleSource,
    options: FigureDataOptions,
    *,
    step_dir: Path | None = None,
    refs: list[str] | None = None,
) -> PrepareManifest:
    """Prepare the chart candidates of *bundle* (or the pictures *refs*)
    under *step_dir* (default ``<bundle>/figure-to-data``). A figure folder
    that exists is replaced, with whatever an earlier run read into it."""
    step_dir = step_dir or bundle.dir / STEP_DIRNAME
    step_dir.mkdir(parents=True, exist_ok=True)
    manifest = PrepareManifest(
        bundle=bundle.name,
        pdf=bundle.pdf_path.name if bundle.pdf_path is not None else None,
        prepared_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        crop_dpi=options.crop_dpi,
        panel_split=options.panel_split,
        selection=sorted(refs) if refs is not None else None,
    )
    for picture in bundle.doc.pictures:
        ref = picture.self_ref
        row = bundle.rows.get(ref)
        wanted = ref in refs if refs is not None else None
        if wanted is False:
            continue
        if wanted is None and (row is None or not is_eligible(row, options)):
            manifest.figures.append(
                PrepareRow(
                    self_ref=ref,
                    status="skipped",
                    reason=_skip_reason(row),
                    figure_type=row.figure_type if row is not None else None,
                )
            )
            continue
        figure_dir = step_dir / job_stem(ref)
        try:
            prepared = prepare_figure(bundle, ref, figure_dir, options)
        except ValueError as exc:
            _log.warning("figure-to-data: %s not prepared: %s", ref, exc)
            manifest.figures.append(
                PrepareRow(self_ref=ref, status="skipped", reason=str(exc))
            )
            continue
        manifest.figures.append(
            PrepareRow(
                self_ref=ref,
                status="prepared",
                folder=figure_dir.name,
                page=prepared.figure.page,
                figure_type=prepared.figure_type,
                capture=prepared.capture,
                size_px=[prepared.width, prepared.height],
                source_kind=prepared.source_kind,
                charts=len(prepared.panels),
                words=len(prepared.words),
            )
        )
    (step_dir / PREPARE_FILENAME).write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def prepare_figure(
    bundle: BundleSource, self_ref: str, figure_dir: Path, options: FigureDataOptions
) -> PreparedFigure:
    """Write ``figure.png``, ``evidence.json``, ``figure.txt`` and the panel
    crops of one picture into *figure_dir* (emptied first)."""
    if figure_dir.is_dir():
        shutil.rmtree(figure_dir)
    figure_dir.mkdir(parents=True)
    job = build_job(bundle, self_ref, work_dir=figure_dir, crop_dpi=options.crop_dpi)
    # A PDF text layer can hold half a surrogate pair, which no file takes.
    job.words = [
        word.model_copy(update={"text": _writable(word.text)}) for word in job.words
    ]
    job.caption = _writable(job.caption) if job.caption else job.caption
    target = figure_dir / IMAGE_FILENAME
    if job.image_path == job.crop_path:
        # No PDF at hand: the bundle's crop is all there is.
        shutil.copyfile(job.crop_path, target)
        capture: Capture = "bundle-crop"
    else:
        job.image_path.rename(target)
        capture = "embedded-bitmap" if job.native_bitmap else "pdf-render"
    with Image.open(target) as opened:
        image = opened.convert("RGB")
    mode = "auto" if options.panel_split == "vlm" else options.panel_split
    split = split_panels(np.asarray(image), job.words, mode=mode)
    several = len(split.panels) > 1
    panels: list[PreparedPanel] = []
    for box in split.panels:
        axes = find_axes(words_in(job.words, box.bbox), box.bbox)
        name: str | None = None
        if several:
            name = f"panel-{_UNSAFE.sub('_', box.id)}.png"
            x0, y0, x1, y1 = (round(v) for v in box.bbox)
            image.crop((x0, y0, x1, y1)).save(figure_dir / name)
        panels.append(
            PreparedPanel(
                id=box.id,
                bbox=box.bbox,
                image=name,
                x_axis=_axis_line(axes.x),
                y_axis=_axis_line(axes.y),
            )
        )
    prepared = PreparedFigure(
        figure=job.figure,
        width=image.width,
        height=image.height,
        capture=capture,
        px_per_crop=job.px_per_crop,
        source_kind=job.source_kind,
        figure_type=job.figure_type,
        caption=job.caption,
        split_method=split.method,
        split_notes=split.notes,
        panels=panels,
        words=job.words,
        marks=job.marks,
        image_objects=job.image_objects,
    )
    (figure_dir / EVIDENCE_FILENAME).write_text(
        prepared.model_dump_json(indent=1) + "\n", encoding="utf-8"
    )
    (figure_dir / CONTEXT_FILENAME).write_text(context_text(prepared), encoding="utf-8")
    return prepared


def context_text(prepared: PreparedFigure) -> str:
    """``figure.txt``: what a reader is told beside the image. The paper's
    caption, the charts the layout analysis found and the text printed in
    the figure; not the description a small model wrote of the figure at
    conversion time, which states numbers the figure does not show."""
    figure = prepared.figure
    lines = [
        f"Figure {job_stem(figure.self_ref)} of {figure.bundle}"
        + (f", page {figure.page}" if figure.page is not None else ""),
        f"Image: {prepared.image}, {prepared.width} x {prepared.height} px",
        f"Caption in the paper: {prepared.caption or '(none found)'}",
        "",
    ]
    several = len(prepared.panels) > 1
    if several:
        lines.append(
            f"Charts found by layout analysis: {len(prepared.panels)} "
            "(box = [x0, y0, x1, y1] on a 0-1000 grid of the image, x from "
            "the left, y from the top). The analysis can be wrong: trust the "
            "image."
        )
    else:
        lines.append("Charts found by layout analysis: one, or none.")
    for panel in prepared.panels:
        parts = [f"- chart {panel.id}"]
        if several:
            parts.append(f"box {_grid_box(panel.bbox, prepared)}")
        if panel.image is not None:
            parts.append(f"crop {panel.image}")
        for name, axis in (("y", panel.y_axis), ("x", panel.x_axis)):
            if axis is not None:
                parts.append(f"{name} ticks {axis}")
        lines.append(", ".join(parts))
    lines.append("")
    inside: list[Word] = []
    for panel in prepared.panels if several else []:
        words = words_in(prepared.words, panel.bbox)
        inside.extend(words)
        lines.append(
            f"Text printed in chart {panel.id} (text @ x,y on a 0-1000 grid "
            "of that chart's crop):"
        )
        lines.append(words_block(words, panel.bbox, limit=_CONTEXT_WORDS))
        lines.append("")
    rest = [w for w in prepared.words if w not in inside]
    lines.append(
        "Text printed outside the charts (legend, titles; text @ x,y on a "
        "0-1000 grid of the image):"
        if several
        else "Text printed in the figure (text @ x,y on a 0-1000 grid of the image):"
    )
    lines.append(words_block(rest, prepared.full, limit=_CONTEXT_WORDS))
    sources = {w.source for w in prepared.words}
    if "ocr" in sources:
        lines.append("")
        lines.append(
            "Part of this text was read by OCR and can hold misreads; the "
            "image decides."
        )
    return "\n".join(lines) + "\n"


def _writable(text: str) -> str:
    """*text* with the characters UTF-8 cannot encode replaced by ``?``."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _grid_box(box: Box, prepared: PreparedFigure) -> list[int]:
    return [
        round(box[0] / prepared.width * 1000),
        round(box[1] / prepared.height * 1000),
        round(box[2] / prepared.width * 1000),
        round(box[3] / prepared.height * 1000),
    ]


def _axis_line(axis: AxisMap | None) -> str | None:
    """``0 | 0.5 | 1 (linear)``: the tick labels of a calibrated axis."""
    if axis is None or not axis.ticks:
        return None
    labels = [
        f"{label:g}" if isinstance(label, float) else str(label)
        for _, label in sorted(axis.ticks, key=lambda tick: tick[0])
    ]
    if axis.scale != "categorical":
        labels = sorted(set(labels), key=float)
    return f"{' | '.join(labels[:24])} ({axis.scale})"


def _skip_reason(row: FigureRow | None) -> str:
    if row is None:
        return "no row in figures.jsonl"
    if row.is_noise:
        return f"noise ({row.noise_reason or 'filtered'})"
    if row.image_path is None:
        return "no crop in the bundle"
    kind = row.figure_type or row.generic_classifier_label or "untyped"
    return f"not typed as a chart ({kind})"
