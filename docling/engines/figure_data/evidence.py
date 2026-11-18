# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Evidence for one figure: its image, the words printed in it, the PDF
paths drawn in it, and axis maps fitted to its tick labels.

- **Image.** The bundle's crop, or with the source PDF the figure box
  rendered at ``crop_dpi``; when one embedded bitmap covers the box at a
  higher resolution than that, the bitmap itself (a 600 dpi chart pasted
  into a paper is common).
- **Words.** The PDF text layer inside the box (pypdfium2 character boxes,
  grouped into words) plus what OCR reads on the work image where the text
  layer has nothing: a chart pasted as a bitmap keeps its tick labels in
  the pixels even when the box also holds a few PDF words (a panel letter,
  a watermark). Without RapidOCR, the text items Docling's OCR put under
  the picture in ``document.json``.
- **Marks.** PDF path objects inside the box with fill / stroke colour and
  vertices, form XObjects resolved; ``source_kind`` is ``raster`` when an
  image covers the box, ``vector`` when paths do the drawing.
- **Axis maps.** Numeric, monotone, collinear tick labels along an edge give
  a linear or log pixel→value map; non-numeric labels a categorical axis.
"""

from __future__ import annotations

import ctypes
import functools
import logging
import math
import re
import unicodedata
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from docling_core.types.doc import DoclingDocument, PictureItem, TextItem
from PIL import Image
from pydantic import BaseModel, ConfigDict

from docling.engines.figure_data.schema import (
    AxisScale,
    Box,
    Figure,
    FigureJob,
    SourceKind,
    VectorMark,
    Word,
)
from docling.engines.figure_typing import get_figure_type
from docling.engines.run_snapshot import read_run_record

if TYPE_CHECKING:
    from pypdfium2 import PdfMatrix, PdfObject, PdfPage, PdfTextPage

_log = logging.getLogger(__name__)

FIGURES_FILENAME = "figures.jsonl"
_MAX_WORK_SIDE_PX = 3200
_NATIVE_MIN_COVER = 0.9
_RASTER_MIN_COVER = 0.6
_VECTOR_MIN_PATHS = 8
_OCR_MIN_SCORE = 0.5

_NUMBER = re.compile(
    r"^\(?([+-]?(?:\d+(?:[.,]\d+)*|[.,]\d+)(?:[eE][+-]?\d+)?)\s*(%|[kKM])?\)?$"
)
_SUFFIX_FACTOR = {"k": 1e3, "K": 1e3, "M": 1e6}


class FigureRow(BaseModel):
    """The fields of a ``figures.jsonl`` row the figure-data stage reads."""

    model_config = ConfigDict(extra="ignore")

    self_ref: str
    image_path: str | None = None
    figure_type: str | None = None
    generic_classifier_label: str | None = None
    is_noise: bool | None = None
    noise_reason: str | None = None
    caption_text: str = ""
    chart_data: dict[str, Any] | None = None


@dataclass
class BundleSource:
    """A converted bundle (or a conversion in progress) to read figures from."""

    dir: Path
    doc: DoclingDocument
    rows: dict[str, FigureRow]
    pdf_path: Path | None = None

    @property
    def name(self) -> str:
        return self.dir.name


def load_bundle(bundle_dir: Path, pdf_path: Path | None = None) -> BundleSource:
    doc = DoclingDocument.load_from_json(bundle_dir / "document.json")
    rows = {row.self_ref: row for row in read_figure_rows(bundle_dir)}
    return BundleSource(dir=bundle_dir, doc=doc, rows=rows, pdf_path=pdf_path)


def read_figure_rows(bundle_dir: Path) -> list[FigureRow]:
    path = bundle_dir / FIGURES_FILENAME
    if not path.is_file():
        return []
    return [
        FigureRow.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def find_source_pdf(bundle_dir: Path, pdf_dir: Path | None) -> Path | None:
    """The bundle's source PDF: ``<pdf_dir>/<run.json file_name>`` (or
    ``<bundle name>.pdf``), else run.json's recorded input path."""
    record = read_run_record(bundle_dir)
    file_name = (
        record.source.file_name
        if record is not None and record.source.file_name
        else f"{bundle_dir.name}.pdf"
    )
    if pdf_dir is not None:
        candidate = pdf_dir / file_name
        return candidate if candidate.is_file() else None
    if record is not None and record.source.input:
        candidate = Path(record.source.input)
        if candidate.is_file():
            return candidate
    return None


def picture_by_ref(doc: DoclingDocument, self_ref: str) -> PictureItem | None:
    return next((p for p in doc.pictures if p.self_ref == self_ref), None)


def job_stem(self_ref: str) -> str:
    """``#/pictures/8`` → ``pictures_8``: the file stem of a figure's outputs."""
    return self_ref.lstrip("#/").replace("/", "_")


@dataclass(frozen=True)
class _PageFrame:
    """PDF user space ↔ Docling's frame (top-left of the page as displayed,
    CropBox and ``/Rotate`` applied; see ``text_repair._user_space_rect``)."""

    left: float
    bottom: float
    right: float
    top: float
    rotation: int

    @classmethod
    def of(cls, page: PdfPage) -> _PageFrame:
        left, bottom, right, top = page.get_bbox()
        return cls(left, bottom, right, top, page.get_rotation())

    def to_docling(self, x: float, y: float) -> tuple[float, float]:
        if self.rotation == 90:
            return y - self.bottom, x - self.left
        if self.rotation == 180:
            return self.right - x, y - self.bottom
        if self.rotation == 270:
            return self.top - y, self.right - x
        return x - self.left, self.top - y

    def rect(self, left: float, bottom: float, right: float, top: float) -> Box:
        xs, ys = zip(
            *(
                self.to_docling(x, y)
                for x, y in ((left, bottom), (right, top), (left, top), (right, bottom))
            )
        )
        return min(xs), min(ys), max(xs), max(ys)


@dataclass(frozen=True)
class _Placement:
    """Figure box (Docling frame, points) → work-image pixels."""

    box: Box
    scale: float

    def px(self, x: float, y: float) -> tuple[float, float]:
        return (x - self.box[0]) * self.scale, (y - self.box[1]) * self.scale

    def px_box(self, box: Box) -> Box:
        x0, y0 = self.px(box[0], box[1])
        x1, y1 = self.px(box[2], box[3])
        return x0, y0, x1, y1

    @property
    def size(self) -> tuple[int, int]:
        return (
            max(1, round((self.box[2] - self.box[0]) * self.scale)),
            max(1, round((self.box[3] - self.box[1]) * self.scale)),
        )


def build_job(
    bundle: BundleSource,
    self_ref: str,
    *,
    work_dir: Path,
    crop_dpi: int = 220,
    crop_path: Path | None = None,
) -> FigureJob:
    """Collect the evidence of the picture *self_ref*; the work image is
    written to ``<work_dir>/<stem>.work.png`` when it is not the crop."""
    picture = picture_by_ref(bundle.doc, self_ref)
    if picture is None or not picture.prov:
        raise ValueError(f"{self_ref} is not a picture with a page position")
    prov = picture.prov[0]
    page_height = bundle.doc.pages[prov.page_no].size.height
    tl = prov.bbox.to_top_left_origin(page_height)
    box: Box = (tl.l, tl.t, tl.r, tl.b)
    row = bundle.rows.get(self_ref)
    if crop_path is None:
        if row is None or row.image_path is None:
            raise ValueError(f"{self_ref} has no crop in {bundle.dir}")
        crop_path = bundle.dir / row.image_path
    with Image.open(crop_path) as crop:
        crop_w = crop.width
    figure_type = get_figure_type(picture)
    figure = Figure(
        bundle=bundle.name,
        self_ref=self_ref,
        image_path=crop_path.relative_to(bundle.dir).as_posix()
        if crop_path.is_relative_to(bundle.dir)
        else crop_path.name,
        page=prov.page_no,
        bbox=[round(v, 2) for v in box],
    )
    job = FigureJob(
        figure=figure,
        crop_path=crop_path,
        image_path=crop_path,
        figure_type=figure_type.label if figure_type is not None else None,
        caption=(row.caption_text if row is not None else None)
        or picture.caption_text(bundle.doc)
        or None,
    )
    crop_scale = crop_w / max(box[2] - box[0], 1e-6)
    if bundle.pdf_path is None:
        with Image.open(crop_path) as crop:
            read = image_words(crop)
        job.words = (
            read
            if read is not None
            else list(_ocr_words(bundle.doc, picture, _Placement(box, crop_scale)))
        )
        return job

    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(bundle.pdf_path)
    try:
        page = pdf[prov.page_no - 1]
        frame = _PageFrame.of(page)
        objects = _page_objects(page, frame, box)
        native = _native_bitmap(objects, box)
        render_scale = crop_dpi / 72
        use_native = native is not None and native[1] > render_scale
        scale = native[1] if native is not None and use_native else render_scale
        placement = _Placement(
            box,
            min(scale, _MAX_WORK_SIDE_PX / max(_Placement(box, scale).size) * scale),
        )
        work = (
            _paste_native(native[0], placement)
            if native is not None and use_native
            else _render_box(page, placement)
        )
        job.native_bitmap = use_native
        work_dir.mkdir(parents=True, exist_ok=True)
        job.image_path = work_dir / f"{job_stem(self_ref)}.work.png"
        work.save(job.image_path)
        job.px_per_crop = work.width / crop_w

        textpage = page.get_textpage()
        try:
            words = list(_pdf_words(textpage, frame, placement))
        finally:
            textpage.close()
        read = image_words(work)
        job.words = merge_words(
            words,
            read
            if read is not None
            else list(_ocr_words(bundle.doc, picture, placement)),
        )
        job.marks = [
            obj.mark(placement) for obj in objects if obj.kind == "path" and obj.inside
        ]
        job.image_objects = sum(1 for obj in objects if obj.kind == "image")
        job.source_kind = _source_kind(objects, box, has_text=bool(words))
        page.close()
    finally:
        pdf.close()
    return job


@dataclass
class _PdfObject:
    kind: Literal["path", "image", "text"]
    box: Box
    inside: bool
    fill: str | None = None
    stroke: str | None = None
    points: list[tuple[float, float]] | None = None
    closed: bool = False
    bitmap: Image.Image | None = None
    px_per_pt: float = 0.0

    def mark(self, placement: _Placement) -> VectorMark:
        points = [placement.px(x, y) for x, y in self.points or []]
        return VectorMark(
            bbox=placement.px_box(self.box),
            fill=self.fill,
            stroke=self.stroke,
            points=[(round(x, 2), round(y, 2)) for x, y in points],
            closed=self.closed,
            is_rect=_is_rect(self.points or [], self.box),
        )


def _page_objects(page: PdfPage, frame: _PageFrame, box: Box) -> list[_PdfObject]:
    """Paths, images and text objects overlapping *box*, in Docling's frame;
    objects inside form XObjects get their form's transform."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c

    out: list[_PdfObject] = []
    forms: dict[int, pdfium.PdfMatrix] = {0: pdfium.PdfMatrix()}
    for obj in page.get_objects(max_depth=15):
        parent = forms.get(obj.level, pdfium.PdfMatrix())
        if obj.type == pdfium_c.FPDF_PAGEOBJ_FORM:
            forms[obj.level + 1] = obj.get_matrix().multiply(parent)
            continue
        kind: Literal["path", "image", "text"]
        if obj.type == pdfium_c.FPDF_PAGEOBJ_PATH:
            kind = "path"
        elif obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
            kind = "image"
        elif obj.type == pdfium_c.FPDF_PAGEOBJ_TEXT:
            kind = "text"
        else:
            continue
        left, bottom, right, top = obj.get_bounds()
        corners = [
            parent.on_point(x, y)
            for x, y in ((left, bottom), (right, top), (left, top), (right, bottom))
        ]
        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]
        obj_box = frame.rect(min(xs), min(ys), max(xs), max(ys))
        if not _overlaps(obj_box, box):
            continue
        item = _PdfObject(kind=kind, box=obj_box, inside=_centre_inside(obj_box, box))
        if kind == "path":
            item.fill, item.stroke = _path_colours(obj.raw)
            item.points, item.closed = _path_points(
                obj.raw, obj.get_matrix().multiply(parent), frame
            )
        elif kind == "image":
            item.bitmap, item.px_per_pt = _image_bitmap(obj, frame, parent)
        out.append(item)
    return out


def _path_colours(raw: object) -> tuple[str | None, str | None]:
    import pypdfium2.raw as pdfium_c

    fill_mode, stroke = ctypes.c_int(), ctypes.c_int()
    pdfium_c.FPDFPath_GetDrawMode(raw, ctypes.byref(fill_mode), ctypes.byref(stroke))
    colours: list[str | None] = []
    for getter, on in (
        (pdfium_c.FPDFPageObj_GetFillColor, fill_mode.value != 0),
        (pdfium_c.FPDFPageObj_GetStrokeColor, bool(stroke.value)),
    ):
        if not on:
            colours.append(None)
            continue
        r, g, b, a = (ctypes.c_uint() for _ in range(4))
        getter(raw, ctypes.byref(r), ctypes.byref(g), ctypes.byref(b), ctypes.byref(a))
        colours.append(f"#{r.value:02x}{g.value:02x}{b.value:02x}")
    return colours[0], colours[1]


def _path_points(
    raw: object, matrix: PdfMatrix, frame: _PageFrame
) -> tuple[list[tuple[float, float]], bool]:
    """Vertices of a path (move/line points and Bézier end points)."""
    import pypdfium2.raw as pdfium_c

    points: list[tuple[float, float]] = []
    closed = False
    bezier = 0
    for index in range(pdfium_c.FPDFPath_CountSegments(raw)):
        segment = pdfium_c.FPDFPath_GetPathSegment(raw, index)
        x, y = ctypes.c_float(), ctypes.c_float()
        pdfium_c.FPDFPathSegment_GetPoint(segment, ctypes.byref(x), ctypes.byref(y))
        closed = closed or bool(pdfium_c.FPDFPathSegment_GetClose(segment))
        if pdfium_c.FPDFPathSegment_GetType(segment) == pdfium_c.FPDF_SEGMENT_BEZIERTO:
            bezier += 1
            if bezier % 3:
                continue
        else:
            bezier = 0
        ux, uy = matrix.on_point(x.value, y.value)
        points.append(frame.to_docling(ux, uy))
    return points, closed


def _image_bitmap(
    obj: PdfObject, frame: _PageFrame, parent: PdfMatrix
) -> tuple[Image.Image | None, float]:
    """The image's own bitmap and its pixels per point, when it is drawn
    upright and unflipped (the common case); else ``(None, 0)``."""
    from pypdfium2 import PdfImage

    if not isinstance(obj, PdfImage) or frame.rotation:
        return None, 0.0
    a, b, c, d, _e, _f = obj.get_matrix().multiply(parent).get()
    if abs(b) > 1e-3 or abs(c) > 1e-3 or a <= 0 or d <= 0:
        return None, 0.0
    width, height = obj.get_px_size()
    try:
        bitmap = obj.get_bitmap(render=False).to_pil().convert("RGB")
    except Exception as exc:  # pdfium cannot decode every filter / colour space
        _log.debug("native bitmap unavailable: %s", exc)
        return None, 0.0
    return bitmap, min(width / a, height / d)


def _native_bitmap(
    objects: list[_PdfObject], box: Box
) -> tuple[tuple[Image.Image, Box], float] | None:
    area = _area(box)
    for obj in objects:
        if obj.kind != "image" or obj.bitmap is None:
            continue
        if _area(_intersection(obj.box, box)) >= _NATIVE_MIN_COVER * area:
            return (obj.bitmap, obj.box), obj.px_per_pt
    return None


def _paste_native(
    native: tuple[Image.Image, Box], placement: _Placement
) -> Image.Image:
    bitmap, img_box = native
    canvas = Image.new("RGB", placement.size, "white")
    sx = bitmap.width / (img_box[2] - img_box[0])
    sy = bitmap.height / (img_box[3] - img_box[1])
    inter = _intersection(img_box, placement.box)
    region = bitmap.crop(
        (
            round((inter[0] - img_box[0]) * sx),
            round((inter[1] - img_box[1]) * sy),
            round((inter[2] - img_box[0]) * sx),
            round((inter[3] - img_box[1]) * sy),
        )
    )
    x0, y0 = placement.px(inter[0], inter[1])
    x1, y1 = placement.px(inter[2], inter[3])
    size = (max(1, round(x1 - x0)), max(1, round(y1 - y0)))
    canvas.paste(region.resize(size, Image.Resampling.LANCZOS), (round(x0), round(y0)))
    return canvas


def _render_box(page: PdfPage, placement: _Placement) -> Image.Image:
    rendered = page.render(scale=placement.scale).to_pil().convert("RGB")
    x0, y0, x1, y1 = (v * placement.scale for v in placement.box)
    return rendered.crop((round(x0), round(y0), round(x1), round(y1)))


def _pdf_words(
    textpage: PdfTextPage, frame: _PageFrame, placement: _Placement
) -> Iterator[Word]:
    """Words of the text layer whose characters lie in the box. Characters
    join while their boxes, grown by 60 % of their size, touch (glyph boxes
    are tighter than the advance: "1.0" has a gap before its dot); works
    for horizontal and rotated (axis-title) text alike."""
    import pypdfium2.raw as pdfium_c

    box = placement.box
    current: list[tuple[str, Box]] = []

    def flush() -> Iterator[Word]:
        if current:
            text = "".join(ch for ch, _ in current).strip()
            if text:
                merged = (
                    min(b[0] for _, b in current),
                    min(b[1] for _, b in current),
                    max(b[2] for _, b in current),
                    max(b[3] for _, b in current),
                )
                yield Word(
                    text=text,
                    bbox=_round_box(placement.px_box(merged)),
                    source="pdf",
                )
        current.clear()

    for index in range(textpage.count_chars()):
        char = chr(pdfium_c.FPDFText_GetUnicode(textpage.raw, index))
        if char.isspace() or pdfium_c.FPDFText_IsGenerated(textpage.raw, index):
            yield from flush()
            continue
        char_box = frame.rect(*textpage.get_charbox(index))
        if not _centre_inside(char_box, box):
            yield from flush()
            continue
        if current and not _touching(current[-1][1], char_box):
            yield from flush()
        current.append((char, char_box))
    yield from flush()


@functools.lru_cache(maxsize=1)
def _ocr_reader() -> Any:
    from rapidocr import RapidOCR

    return RapidOCR()


def image_words(image: Image.Image) -> list[Word] | None:
    """The text lines RapidOCR reads on *image*, in its pixels; None when
    RapidOCR or its models are not available."""
    try:
        reader = _ocr_reader()
    except Exception as exc:  # no rapidocr, or its models cannot be fetched
        _log.warning("figure data: no OCR of the figure image (%s)", exc)
        return None
    result = reader(np.asarray(image.convert("RGB"))[:, :, ::-1])
    if result.boxes is None:
        return []
    words: list[Word] = []
    for quad, text, score in zip(result.boxes, result.txts, result.scores):
        # OCR also "reads" bars and markers, as "_", "|" or a bullet.
        if score < _OCR_MIN_SCORE or not any(c.isalnum() for c in text):
            continue
        xs, ys = [float(p[0]) for p in quad], [float(p[1]) for p in quad]
        words.append(
            Word(
                text=text.strip(),
                bbox=_round_box((min(xs), min(ys), max(xs), max(ys))),
                source="ocr",
            )
        )
    return words


def merge_words(pdf: list[Word], ocr: list[Word]) -> list[Word]:
    """The text-layer words plus the OCR lines that cover none of them."""
    return pdf + [
        line
        for line in ocr
        if not any(
            _centre_inside(word.bbox, line.bbox) or _centre_inside(line.bbox, word.bbox)
            for word in pdf
        )
    ]


def _ocr_words(
    doc: DoclingDocument, picture: PictureItem, placement: _Placement
) -> Iterator[Word]:
    page_no = picture.prov[0].page_no
    page_height = doc.pages[page_no].size.height
    for item, _level in doc.iterate_items(root=picture, traverse_pictures=True):
        if not isinstance(item, TextItem) or not item.text.strip():
            continue
        for prov in item.prov:
            if prov.page_no != page_no:
                continue
            tl = prov.bbox.to_top_left_origin(page_height)
            item_box = (tl.l, tl.t, tl.r, tl.b)
            if _centre_inside(item_box, placement.box):
                yield Word(
                    text=item.text.strip(),
                    bbox=_round_box(placement.px_box(item_box)),
                    source="ocr",
                )


def _source_kind(objects: list[_PdfObject], box: Box, *, has_text: bool) -> SourceKind:
    area = _area(box)
    cover = min(
        1.0,
        sum(_area(_intersection(o.box, box)) for o in objects if o.kind == "image")
        / max(area, 1e-6),
    )
    paths = sum(1 for o in objects if o.kind == "path" and o.inside)
    if cover >= _RASTER_MIN_COVER:
        return "mixed" if paths >= _VECTOR_MIN_PATHS else "raster"
    if paths >= _VECTOR_MIN_PATHS or (paths and has_text):
        return "mixed" if cover > 0.1 else "vector"
    if cover > 0.1:
        return "raster"
    return "unknown"


def _is_rect(points: list[tuple[float, float]], box: Box, tol: float = 0.6) -> bool:
    if not 4 <= len(points) <= 6:
        return False
    return all(
        min(abs(x - box[0]), abs(x - box[2])) <= tol
        and min(abs(y - box[1]), abs(y - box[3])) <= tol
        for x, y in points
    )


def _touching(a: Box, b: Box) -> bool:
    grow = 0.6 * max(a[2] - a[0], a[3] - a[1], b[2] - b[0], b[3] - b[1])
    return not (
        b[0] > a[2] + grow
        or a[0] > b[2] + grow
        or b[1] > a[3] + grow
        or a[1] > b[3] + grow
    )


def _centre_inside(inner: Box, outer: Box, tol: float = 1.0) -> bool:
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return (
        outer[0] - tol <= cx <= outer[2] + tol
        and outer[1] - tol <= cy <= outer[3] + tol
    )


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _intersection(a: Box, b: Box) -> Box:
    return max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _round_box(box: Box) -> Box:
    return (
        round(box[0], 1),
        round(box[1], 1),
        round(box[2], 1),
        round(box[3], 1),
    )


# --- axis calibration -------------------------------------------------------


def parse_number(text: str) -> float | None:
    """A printed number: ``0.25``, ``-3`` (also with a Unicode minus or en
    dash), ``65.2%``, ``64k``, ``1M``, ``1,000``; None for anything else."""
    cleaned = text.strip().replace("\u2212", "-").replace("\u2013", "-")
    match = _NUMBER.match(cleaned)
    if match is None:
        return None
    digits, suffix = match.group(1), match.group(2)
    if "," in digits:
        thousands = re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", digits)
        digits = digits.replace(",", "" if thousands else ".")
    if digits.count(".") > 1:
        return None
    value = float(digits)
    return value * _SUFFIX_FACTOR.get(suffix or "", 1.0)


class AxisMap(BaseModel):
    """Pixel position along an axis ↔ value. Numeric scales map
    ``value = slope * pos + intercept`` (``log10(value)`` for log);
    categorical axes keep ``(pos, label)`` ticks."""

    axis: Literal["x", "y"]
    scale: AxisScale
    slope: float = 0.0
    intercept: float = 0.0
    ticks: list[tuple[float, float | str]]
    residual: float = 0.0

    def value_at(self, pos: float) -> float | None:
        if self.scale == "categorical":
            return None
        raw = self.slope * pos + self.intercept
        return 10**raw if self.scale == "log" else raw

    def pos_of(self, value: float) -> float | None:
        if self.scale == "categorical" or self.slope == 0:
            return None
        if self.scale == "log":
            if value <= 0:
                return None
            value = math.log10(value)
        return (value - self.intercept) / self.slope

    def category_at(self, pos: float) -> str | None:
        """The categorical tick nearest *pos*, within half a tick spacing."""
        if self.scale != "categorical" or not self.ticks:
            return None
        positions = sorted(p for p, _ in self.ticks)
        spacing = (
            float(np.median(np.diff(positions))) if len(positions) > 1 else math.inf
        )
        tick_pos, label = min(self.ticks, key=lambda t: abs(t[0] - pos))
        return str(label) if abs(tick_pos - pos) <= spacing / 2 else None

    @property
    def value_range(self) -> tuple[float, float] | None:
        values = [v for _, v in self.ticks if isinstance(v, float)]
        return (min(values), max(values)) if values else None


_MAX_RESIDUAL = 0.03


def fit_axis(
    ticks: Iterable[tuple[float, str]], axis: Literal["x", "y"]
) -> AxisMap | None:
    """Fit an axis to ``(pixel position, label)`` ticks: linear or log when
    at least two labels are numbers, strictly monotone in position and on a
    line within 3 % of the range; categorical when most labels are not
    numbers; None otherwise."""
    pairs = sorted(ticks)
    if not pairs:
        return None
    numeric = [(pos, v) for pos, text in pairs if (v := parse_number(text)) is not None]
    if len(numeric) < 0.6 * len(pairs):
        if len(pairs) < 2:
            return None
        return AxisMap(axis=axis, scale="categorical", ticks=[(p, t) for p, t in pairs])
    if len(numeric) < 2:
        return None
    pos = np.array([p for p, _ in numeric], dtype=float)
    val = np.array([v for _, v in numeric], dtype=float)
    steps = np.diff(val)
    if not (np.all(steps > 0) or np.all(steps < 0)) or np.ptp(pos) == 0:
        return None
    best: AxisMap | None = None
    candidates: list[tuple[AxisScale, np.ndarray]] = [("linear", val)]
    if np.all(val > 0) and len(val) >= 3:
        candidates.append(("log", np.log10(val)))
    for scale, target in candidates:
        slope, intercept = np.polyfit(pos, target, 1)
        span = float(np.ptp(target)) or 1.0
        residual = float(np.max(np.abs(slope * pos + intercept - target))) / span
        if residual > _MAX_RESIDUAL:
            continue
        if best is None or residual < best.residual:
            best = AxisMap(
                axis=axis,
                scale=scale,
                slope=float(slope),
                intercept=float(intercept),
                ticks=[(float(p), float(v)) for p, v in numeric],
                residual=round(residual, 5),
            )
    return best


class PanelAxes(BaseModel):
    x: AxisMap | None = None
    y: AxisMap | None = None


def find_axes(words: list[Word], region: Box) -> PanelAxes:
    """Tick labels of a panel: the y axis is the largest group of labels
    left of the plot sharing a right edge, the x axis the largest group
    below it sharing a baseline; each group is fitted with :func:`fit_axis`."""
    x0, y0, x1, y1 = region
    width, height = x1 - x0, y1 - y0
    inside = [
        w for w in words if x0 <= w.cx <= x1 and y0 <= w.cy <= y1 and len(w.text) <= 40
    ]
    heights = [w.bbox[3] - w.bbox[1] for w in inside] or [10.0]
    tol_y = 0.6 * float(np.median(heights))
    tol_x = max(0.02 * width, tol_y)

    left = [w for w in inside if w.cx <= x0 + 0.4 * width]
    bottom = [w for w in inside if w.cy >= y0 + 0.55 * height]
    y_group = _largest_group(
        left, key=lambda w: w.bbox[2], tol=tol_x, spread=lambda w: w.cy
    )
    x_group = _largest_group(
        bottom, key=lambda w: w.cy, tol=tol_y, spread=lambda w: w.cx
    )
    numeric_y = [w for w in y_group if parse_number(w.text) is not None]
    numeric_x = [w for w in x_group if parse_number(w.text) is not None]
    return PanelAxes(
        y=_fit_ticks(
            [(w.cy, w.text) for w in (numeric_y if len(numeric_y) >= 2 else y_group)],
            "y",
        ),
        x=_fit_ticks(
            [(w.cx, w.text) for w in (numeric_x if len(numeric_x) >= 2 else x_group)],
            "x",
        ),
    )


def _fit_ticks(
    ticks: list[tuple[float, str]], axis: Literal["x", "y"]
) -> AxisMap | None:
    """:func:`fit_axis`, forgiving one misread label among four or more
    (OCR turns "300" into "30" now and then, which breaks the monotone run)."""
    fitted = fit_axis(ticks, axis)
    if fitted is not None or len(ticks) < 4:
        return fitted
    for skip in range(len(ticks)):
        fitted = fit_axis(ticks[:skip] + ticks[skip + 1 :], axis)
        if fitted is not None and fitted.scale != "categorical":
            return fitted
    return None


def _largest_group(
    words: list[Word],
    *,
    key: Callable[[Word], float],
    tol: float,
    spread: Callable[[Word], float],
) -> list[Word]:
    """Words whose *key* agrees within *tol*, at distinct *spread* positions;
    the group with most members (numeric labels win a tie)."""
    best: list[Word] = []
    for anchor in words:
        group = [w for w in words if abs(key(w) - key(anchor)) <= tol]
        group.sort(key=spread)
        distinct: list[Word] = []
        for w in group:
            if not distinct or abs(spread(w) - spread(distinct[-1])) > 1.0:
                distinct.append(w)
        numeric = sum(parse_number(w.text) is not None for w in distinct)
        best_numeric = sum(parse_number(w.text) is not None for w in best)
        if len(distinct) >= 2 and (len(distinct), numeric) > (len(best), best_numeric):
            best = distinct
    return best


def words_in(words: list[Word], region: Box) -> list[Word]:
    return [
        w
        for w in words
        if region[0] <= w.cx <= region[2] and region[1] <= w.cy <= region[3]
    ]


_LABEL_SPACE = re.compile(r"[\s_]+")
LABEL_DISTANCE = 0.2


def normalise_label(text: str) -> str:
    return _LABEL_SPACE.sub(" ", unicodedata.normalize("NFKC", text)).strip().casefold()


def same_label(a: str, b: str) -> bool:
    """Equal after normalising, or within a Levenshtein distance of 0.2 of
    the longer (OCR and model spellings differ)."""
    na, nb = normalise_label(a), normalise_label(b)
    if na == nb:
        return True
    longest = max(len(na), len(nb))
    return longest > 0 and levenshtein(na, nb) <= LABEL_DISTANCE * longest


def closest_label(text: str, labels: list[str]) -> int | None:
    """Index of the label of *labels* nearest *text* that :func:`same_label`
    accepts ("GPT4 Web - no image" must not take "GPT4 API - no image")."""
    target = normalise_label(text)
    scored = [
        (levenshtein(target, normalise_label(label)), index)
        for index, label in enumerate(labels)
        if same_label(text, label)
    ]
    return min(scored)[1] if scored else None


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]
