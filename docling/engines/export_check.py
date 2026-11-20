# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Self-check of a converted bundle, written as ``check.json``.

Reads only the bundle folder and, when it can be found, the source PDF, so it
runs on bundles written by earlier releases without reconverting:

- **html_coverage** — every item of ``document.json`` is exactly one
  ``data-self-ref`` element of ``<stem>.html``;
- **page_recall** — the words of each page's PDF text layer (pypdfium2) are
  in the items ``document.json`` places on that page;
- **uncovered_text** — the printed words of each page lie inside the box of
  some item on that page (a box on the wrong spot, or text left out);
- **export_fidelity** — ``<stem>.html`` holds the words of every item,
  ``<stem>.md`` and the chunks (text + headings) those of the body; model
  written descriptions are left out of the exports first;
- **ligature_splits** — no export has a ligature split off its word
  ("speci fi c") that the PDF prints whole;
- **tables** — degenerate grids, and the tables whose cells miss words of
  their box (the engine's stored ``cell_text_recall``);
- **chunks** — empty chunks, chunks over the token budget, dangling refs;
- **structure** — a paper that came out as a few blocks or without headings
  (the warnings of :func:`~docling.engines.structure.quality_report`, which
  ``run.json`` carries under ``quality``);
- **guards** — images on disk, noise pictures kept out of the markdown and
  marked in the HTML, the run's status;
- **figure_data** — chart figures eligible for figure-to-data, those with
  chart data, and how many of them reached the confidence threshold.

Word recall is multiset recall over NFKC + casefolded runs of two or more
letters or digits.
"""

from __future__ import annotations

import html
import json
import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import numpy as np
from docling_core.types.doc import (
    ContentLayer,
    DocItem,
    DoclingDocument,
    PageItem,
    SectionHeaderItem,
    Size,
    TableItem,
    TextItem,
)
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from docling.datamodel.base_models import (
    ConversionStatus,
    degenerate_table_reason,
    table_filled_fraction,
)
from docling.engines.figure_data.eligibility import is_eligible
from docling.engines.figure_data.evidence import FigureRow
from docling.engines.figure_data.publish import panel_confidence
from docling.engines.figure_data.schema import ChartData, FigureDataOptions
from docling.engines.run_snapshot import (
    ENGINE_VERSION,
    RunRecord,
    public_source_path,
    read_run_record,
    write_text_atomic,
)
from docling.engines.serializers import ANNOTATION_CLOSE
from docling.engines.structure import quality_report
from docling.engines.text_repair import (
    LIGATURES,
    PDF_HYPHENATION,
    TABLE_TEXT_MIN_RECALL,
    WORD_HEAD,
    WORD_TAIL,
    get_table_pdf_text,
    pdf_page_texts,
)
from docling.utils.text_layer import (
    PartlyUnreadablePage,
    pages_text,
    read_pdf,
    summary,
)

if TYPE_CHECKING:
    from pypdfium2 import PdfPage

_log = logging.getLogger(__name__)

CHECK_FILENAME = "check.json"
CHECK_SCHEMA = "extrct.bundle-check/1"

PAGE_RECALL_MIN = 0.90
PAGE_LOST_WORDS_MAX = 50
PAGE_MIN_WORDS = 30
DOCUMENT_RECALL_MIN = 0.97
UNCOVERED_SHARE_MAX = 0.05
UNCOVERED_WORDS_MAX = 30
EXPORT_FIDELITY_MIN = 0.99
# Non-blocking quality warnings that are issues of a bundle all the same.
_STRUCTURE_ISSUE_CODES = frozenset({"no_headings"})

_TOP_MISSING = 5
_EXAMPLES = 5
_SAMPLE_CHARS = 70
_BOX_TOLERANCE = 1.0

_WORD = re.compile(r"[^\W_]{2,}")
# Letters only: a font without a Unicode map prints control codes and symbols.
_LETTER_WORD = re.compile(r"[^\W\d_]{2,}")
_ALPHA = re.compile(r"[a-z]+")

_HIDDEN = re.compile(r"<(script|style|title)\b[^>]*>.*?</\1\s*>", re.S | re.I)
_ABOUT = re.compile(r'<header class="extrct-about">.*?</header>', re.S)
_MODEL_META = re.compile(r'<details class="docling-meta">.*?</details>', re.S)
# HTML5: "< K" is text, not a tag; a naive <[^>]+> eats code containing "<".
_TAG = re.compile(r"</?[A-Za-z][^>]*>|<![^>]*>")
_TAGGED = re.compile(r'<[A-Za-z][^>]*?\sdata-self-ref="([^"]+)"[^>]*>')
_ANNOTATION = re.compile(
    r'<!--<annotation kind="[^"]*">-->.*?' + re.escape(ANNOTATION_CLOSE), re.S
)
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_COMMENT = re.compile(r"<!--.*?-->", re.S)


class CheckBlock(BaseModel):
    """One check: its numbers (in subclasses), human-readable ``issues``, and
    ``skipped`` with the reason when it could not run (not an issue)."""

    skipped: str | None = None
    issues: list[str] = Field(default_factory=list)


class HtmlCoverage(CheckBlock):
    items: int = 0
    tagged_once: int = 0
    missing: int = 0
    missing_by_label: dict[str, int] = Field(default_factory=dict)
    duplicate: int = 0
    phantom: int = 0


class PageRecallFlag(BaseModel):
    page: int
    pdf_words: int
    recall: float
    lost: int
    top_missing: dict[str, int]


class PageRecall(CheckBlock):
    pdf_words: int = 0
    no_text_layer: bool = False
    document_recall: float | None = None
    pages_checked: int = 0
    min_page: int | None = None
    min_page_recall: float | None = None
    flagged_pages: list[PageRecallFlag] = Field(default_factory=list)


class UncoveredTextPage(BaseModel):
    page: int
    words: int
    uncovered_words: int
    share: float
    chars: int
    uncovered_chars: int
    sample: str


class UncoveredText(CheckBlock):
    """Words are runs of two or more letters, chars every printed non-space
    character; a word is uncovered when most of its letters are."""

    no_text_layer: bool = False
    chars: int = 0
    uncovered_chars: int = 0
    words: int = 0
    uncovered_words: int = 0
    pages_checked: int = 0
    max_page: int | None = None
    max_page_share: float | None = None
    flagged_pages: list[UncoveredTextPage] = Field(default_factory=list)


class ExportFidelity(CheckBlock):
    html: float | None = None
    md: float | None = None
    chunks: float | None = None


class LigatureSplits(CheckBlock):
    per_export: dict[str, int] = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)


class TableRecall(BaseModel):
    self_ref: str
    cell_text_recall: float


class DegenerateTable(BaseModel):
    self_ref: str
    page: int | None
    rows: int
    cols: int
    filled_fraction: float
    reason: str


class TableCheck(CheckBlock):
    count: int = 0
    low_recall: list[TableRecall] = Field(default_factory=list)
    degenerate: list[DegenerateTable] = Field(default_factory=list)


class ChunkCheck(CheckBlock):
    count: int = 0
    empty: int = 0
    max_tokens: int | None = None
    over_max_tokens: int = 0
    unresolved_refs: list[str] = Field(default_factory=list)


class StructureCheck(CheckBlock):
    pages: int = 0
    body_text_items: int = 0
    section_headers: int = 0
    warnings: list[str] = Field(
        default_factory=list,
        description="Codes of every quality warning, issues or not.",
    )


class GuardCheck(CheckBlock):
    run_status: str | None = None
    run_errors: int = 0
    missing_images: list[str] = Field(default_factory=list)
    noise_in_md: list[str] = Field(default_factory=list)
    noise_unmarked_in_html: list[str] = Field(default_factory=list)


class FigureDataCheck(CheckBlock):
    """Chart data read from the figures by the figure-to-data step
    (:mod:`docling.engines.figure_data`). Of the *eligible* chart candidates,
    *extracted* figures carry values and *no_data* figures were looked at
    and hold none (a diagram typed as a chart, or a figure the reader
    declined). *verified* figures have every panel's median value
    confidence at the markdown threshold, the other extracted ones count as
    *low_confidence*. *mode* is the method of the run that was embedded."""

    mode: str | None = None
    eligible: int = 0
    extracted: int = 0
    no_data: int = 0
    verified: int = 0
    low_confidence: int = 0


class TextLayerCheck(CheckBlock):
    """Pages whose PDF text does not say what they print
    (``docling.utils.text_layer``). A page decoded from glyph numbers is
    checked like any other by ``page_recall``, against the decoded text; an
    unreadable page has no PDF text to check its OCR text against."""

    glyph_order_pages: list[int] = Field(default_factory=list)
    unreadable_pages: list[int] = Field(default_factory=list)
    partly_unreadable_pages: list[PartlyUnreadablePage] = Field(default_factory=list)


class BundleCheck(BaseModel):
    """Result of :func:`check_bundle`; ``ok`` and ``issues`` roll up the
    blocks' issues."""

    schema_version: str = CHECK_SCHEMA
    bundle: str
    pdf: str | None = None
    checked_by: str = ENGINE_VERSION
    ok: bool = True
    issues: list[str] = Field(default_factory=list)
    html_coverage: HtmlCoverage
    page_recall: PageRecall
    # Defaulted: check.json files written before this check still load.
    uncovered_text: UncoveredText = Field(
        default_factory=lambda: UncoveredText(skipped="not checked")
    )
    export_fidelity: ExportFidelity
    ligature_splits: LigatureSplits
    tables: TableCheck
    chunks: ChunkCheck
    structure: StructureCheck
    guards: GuardCheck
    figure_data: FigureDataCheck = Field(
        default_factory=lambda: FigureDataCheck(skipped="not checked")
    )
    text_layer: TextLayerCheck = Field(
        default_factory=lambda: TextLayerCheck(skipped="not checked")
    )

    @model_validator(mode="after")
    def _roll_up(self) -> Self:
        self.issues = [
            f"{name}: {issue}"
            for name, block in self._blocks()
            for issue in block.issues
        ]
        self.ok = not self.issues
        return self

    def _blocks(self) -> tuple[tuple[str, CheckBlock], ...]:
        return (
            ("html_coverage", self.html_coverage),
            ("page_recall", self.page_recall),
            ("uncovered_text", self.uncovered_text),
            ("export_fidelity", self.export_fidelity),
            ("ligature_splits", self.ligature_splits),
            ("tables", self.tables),
            ("chunks", self.chunks),
            ("structure", self.structure),
            ("guards", self.guards),
            ("figure_data", self.figure_data),
            ("text_layer", self.text_layer),
        )

    def summary_line(self) -> str:
        """One line for a batch table, e.g. ``html 100% · page-recall min 0.94
        (p1) · uncovered max 0.01 (p3) · md 1.000 · chunks 0.999 · tables 3
        (1 low) · 0 empty chunks · OK``."""
        cov = self.html_coverage
        if cov.skipped is not None or not cov.items:
            parts = ["html n/a"]
        elif cov.tagged_once == cov.items:
            parts = ["html 100%"]
        else:
            parts = [f"html {cov.tagged_once / cov.items:.1%}"]

        rec = self.page_recall
        if rec.skipped is not None:
            parts.append("page-recall n/a")
        elif rec.no_text_layer:
            parts.append("page-recall n/a (no text layer)")
        elif rec.min_page_recall is not None:
            parts.append(f"page-recall min {rec.min_page_recall:.2f} (p{rec.min_page})")
        elif rec.document_recall is not None:
            parts.append(f"page-recall doc {rec.document_recall:.2f}")

        unc = self.uncovered_text
        if unc.max_page_share is None:
            parts.append("uncovered n/a")
        else:
            parts.append(f"uncovered max {unc.max_page_share:.2f} (p{unc.max_page})")

        fid = self.export_fidelity
        for name, value in (("md", fid.md), ("chunks", fid.chunks)):
            parts.append(f"{name} {value:.3f}" if value is not None else f"{name} n/a")

        tab = self.tables
        notes = [
            f"{n} {what}"
            for n, what in (
                (len(tab.low_recall), "low"),
                (len(tab.degenerate), "degenerate"),
            )
            if n
        ]
        parts.append(
            f"tables {tab.count}" + (f" ({', '.join(notes)})" if notes else "")
        )
        if self.chunks.skipped is None:
            parts.append(f"{self.chunks.empty} empty chunks")
        figs = self.figure_data
        if figs.skipped is None:
            parts.append(f"charts {figs.verified}/{figs.extracted}/{figs.eligible}")
        parts.append("OK" if self.ok else f"{len(self.issues)} issues")
        return " · ".join(parts)


def check_bundle(pdf_dir: Path, pdf_path: Path | None = None) -> BundleCheck:
    """Check the bundle in *pdf_dir* (a folder holding ``document.json``).

    *pdf_path* defaults to ``run.json``'s ``source.input`` (relative to the
    current directory, as recorded at conversion time); without a PDF the
    PDF-based checks are skipped with the reason.
    """
    stem = pdf_dir.name
    doc = DoclingDocument.load_from_json(pdf_dir / "document.json")
    run = read_run_record(pdf_dir)
    html_raw = _read_text(pdf_dir / f"{stem}.html")
    md_raw = _read_text(pdf_dir / f"{stem}.md")
    embedded_raw = _read_text(pdf_dir / f"{stem}.embedded.md")
    chunks = _read_rows(pdf_dir / "chunks.jsonl", _ChunkRow)
    figures = _read_rows(pdf_dir / "figures.jsonl", _ImageRow) or []
    table_rows = _read_rows(pdf_dir / "tables.jsonl", _ImageRow) or []

    pdf_skip: str | None = None
    if pdf_path is None:
        pdf_path, pdf_skip = _source_pdf(run)
    pdf_pages = _pdf_page_texts(pdf_path) if pdf_path is not None else None

    content = _DocContent.of(doc)
    html_body = _HIDDEN.sub(" ", html_raw) if html_raw is not None else None
    exports = {
        "md": _md_text(md_raw, content.descriptions) if md_raw is not None else None,
        "embedded.md": (
            _md_text(embedded_raw, content.descriptions)
            if embedded_raw is not None
            else None
        ),
        "html": (
            _html_text(html_body, content.descriptions)
            if html_body is not None
            else None
        ),
        "chunks": (
            _without_descriptions(
                "\n".join(c.text for c in chunks), content.descriptions
            )
            if chunks is not None
            else None
        ),
    }
    tags = _tagged_elements(html_body) if html_body is not None else None

    return BundleCheck(
        bundle=stem,
        pdf=public_source_path(pdf_path) if pdf_path is not None else None,
        html_coverage=_check_html_coverage(content, tags),
        page_recall=(
            _check_page_recall(content, pdf_pages, converted=doc.pages.keys())
            if pdf_pages is not None
            else PageRecall(skipped=pdf_skip)
        ),
        uncovered_text=(
            _check_uncovered_text(content, doc.pages, pdf_path)
            if pdf_path is not None
            else UncoveredText(skipped=pdf_skip)
        ),
        export_fidelity=_check_export_fidelity(content, exports, chunks),
        ligature_splits=(
            _check_ligature_splits(exports, pdf_pages)
            if pdf_pages is not None
            else LigatureSplits(skipped=pdf_skip)
        ),
        tables=_check_tables(doc),
        chunks=_check_chunks(content, chunks, run),
        structure=_check_structure(doc),
        guards=_check_guards(pdf_dir, run, figures, table_rows, md_raw, tags),
        figure_data=_check_figure_data(
            _read_rows(pdf_dir / "figures.jsonl", FigureRow) or [], run
        ),
        text_layer=(
            _check_text_layer(pdf_path)
            if pdf_path is not None
            else TextLayerCheck(skipped=pdf_skip)
        ),
    )


def _check_figure_data(rows: list[FigureRow], run: RunRecord | None) -> FigureDataCheck:
    block = run.figure_to_data if run is not None else None
    if block is None and not any(row.chart_data for row in rows):
        return FigureDataCheck(skipped="figure-to-data not run")
    options = FigureDataOptions()
    result = FigureDataCheck(mode=str(block["method"]) if block else None)
    looked_at = 0
    for row in rows:
        eligible = is_eligible(row, options)
        result.eligible += eligible
        if not row.chart_data:
            continue
        looked_at += eligible
        chart = ChartData.model_validate(row.chart_data)
        if not any(panel.data for panel in chart.panels):
            result.no_data += 1
            continue
        result.extracted += 1
        confidences = [panel_confidence(p) for p in chart.panels if p.data]
        if all(
            c is not None and c >= options.min_confidence_for_markdown
            for c in confidences
        ):
            result.verified += 1
    result.low_confidence = result.extracted - result.verified
    if block is not None and looked_at < result.eligible:
        result.issues.append(
            f"{result.eligible - looked_at} of {result.eligible} chart "
            "figure(s) were not read by the figure-to-data step"
        )
    return result


def write_bundle_check(pdf_dir: Path, check: BundleCheck) -> Path:
    """Write *check* to ``<pdf_dir>/check.json`` and return its path."""
    target = pdf_dir / CHECK_FILENAME
    write_text_atomic(target, check.model_dump_json(indent=2) + "\n")
    _log.info("Bundle check written: %s (%s)", target, check.summary_line())
    return target


# --- bundle files -----------------------------------------------------------


class _ChunkRow(BaseModel):
    text: str = ""
    token_count: int | None = None
    headings: list[str] = Field(default_factory=list)
    self_refs: list[str] = Field(default_factory=list)


class _ImageRow(BaseModel):
    self_ref: str = ""
    image_path: str | None = None
    is_noise: bool | None = None


_Row = TypeVar("_Row", bound=BaseModel)


def _read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _read_rows(path: Path, model: type[_Row]) -> list[_Row] | None:
    text = _read_text(path)
    if text is None:
        return None
    return [model.model_validate_json(line) for line in text.splitlines() if line]


def _source_pdf(run: RunRecord | None) -> tuple[Path | None, str | None]:
    if run is None or not run.source.input:
        return None, "run.json records no source PDF"
    if run.source.source_kind == "url":
        return None, "no local PDF (URL source)"
    path = Path(run.source.input)
    if not path.is_file():
        return None, (
            f"source PDF {run.source.input!r} (run.json) not found from the "
            "current directory; pass pdf_path"
        )
    size, expected = path.stat().st_size, run.source.file_size_bytes
    if expected is not None and size != expected:
        return None, (f"{path} has {size} bytes, the converted source had {expected}")
    return path, None


def _pdf_page_texts(pdf_path: Path) -> list[str]:
    return [PDF_HYPHENATION.sub("", text) for text in pdf_page_texts(pdf_path)]


def _check_text_layer(pdf_path: Path) -> TextLayerCheck:
    found = summary(read_pdf(pdf_path))
    result = TextLayerCheck(**found.model_dump())
    if found.unreadable_pages:
        result.issues.append(
            "text layer unreadable, the text of these pages is not checked "
            f"against the PDF (OCR reads them): {pages_text(found.unreadable_pages)}"
        )
    result.issues += [
        f"p{page.page}: {page.share:.0%} of the characters are in a font the "
        "text layer cannot read"
        for page in found.partly_unreadable_pages
    ]
    return result


# --- text views ---------------------------------------------------------------


def _words(text: str) -> list[str]:
    return _WORD.findall(unicodedata.normalize("NFKC", text).casefold())


def _recall(reference: Counter[str], candidate: Counter[str]) -> float | None:
    total = sum(reference.values())
    if not total:
        return None
    return round(1 - sum((reference - candidate).values()) / total, 4)


def _top_missing(reference: Counter[str], candidate: Counter[str]) -> dict[str, int]:
    return dict((reference - candidate).most_common(_TOP_MISSING))


class _DocContent:
    """The items of a document and their words: all of them, per page, and
    the body (what the markdown and chunks carry: no furniture, no text
    inside figures)."""

    def __init__(
        self,
        items: list[DocItem],
        body_refs: set[str],
        descriptions: list[str],
    ) -> None:
        self.items = items
        self.refs = {item.self_ref for item in items}
        self.body_refs = body_refs
        self.descriptions = descriptions
        self.all_words: Counter[str] = Counter()
        self.body_words: Counter[str] = Counter()
        self.page_words: dict[int, Counter[str]] = {}
        for item in items:
            words = Counter(_words(_item_text(item)))
            self.all_words.update(words)
            if item.self_ref in body_refs:
                self.body_words.update(words)
            for prov in item.prov:
                self.page_words.setdefault(prov.page_no, Counter()).update(words)

    @classmethod
    def of(cls, doc: DoclingDocument) -> _DocContent:
        items: list[DocItem] = [
            *doc.texts,
            *doc.pictures,
            *doc.tables,
            *doc.key_value_items,
            *doc.form_items,
        ]
        inside = _inside_pictures(doc)
        body_refs = {
            item.self_ref
            for item in items
            if item.content_layer == ContentLayer.BODY and item.self_ref not in inside
        }
        return cls(items, body_refs, _descriptions(doc))


def _item_text(item: DocItem) -> str:
    if isinstance(item, TextItem):
        return item.text
    if isinstance(item, TableItem):
        return " ".join(cell.text for cell in item.data.table_cells)
    return ""


def _inside_pictures(doc: DoclingDocument) -> set[str]:
    """Refs below a picture other than its captions and footnotes: the text
    Docling found inside the figure."""
    inside: set[str] = set()
    for picture in doc.pictures:
        own = {ref.cref for ref in (*picture.captions, *picture.footnotes)}
        stack = [ref for ref in picture.children if ref.cref not in own]
        while stack:
            ref = stack.pop()
            if ref.cref in inside:
                continue
            inside.add(ref.cref)
            stack.extend(ref.resolve(doc).children)
    return inside


def _descriptions(doc: DoclingDocument) -> list[str]:
    """Model-written descriptions, longest first (a short one can be part of
    a longer one)."""
    texts = {
        item.meta.description.text.strip()
        for item in (*doc.pictures, *doc.tables)
        if item.meta is not None and item.meta.description is not None
    }
    descriptions = list(texts - {""})
    descriptions.sort(key=len, reverse=True)
    return descriptions


def _without_descriptions(text: str, descriptions: list[str]) -> str:
    text = _ANNOTATION.sub(" ", text)
    for description in descriptions:
        text = text.replace(description, " ")
    return text


def _md_text(raw: str, descriptions: list[str]) -> str:
    text = _ANNOTATION.sub(" ", raw)
    text = html.unescape(_MD_COMMENT.sub(" ", _MD_IMAGE.sub(" ", text)))
    return _without_descriptions(text, descriptions)


def _html_text(body: str, descriptions: list[str]) -> str:
    text = _MODEL_META.sub(" ", _ABOUT.sub(" ", body))
    return _without_descriptions(html.unescape(_TAG.sub(" ", text)), descriptions)


def _tagged_elements(html_body: str) -> list[tuple[str, str]]:
    """``(self_ref, opening tag)`` of every element carrying a self_ref."""
    return [(m.group(1), m.group(0)) for m in _TAGGED.finditer(html_body)]


# --- checks -----------------------------------------------------------------


def _check_html_coverage(
    content: _DocContent, tags: list[tuple[str, str]] | None
) -> HtmlCoverage:
    if tags is None:
        return HtmlCoverage(skipped="no <stem>.html in the bundle")
    tagged = Counter(ref for ref, _tag in tags)
    missing = [item for item in content.items if tagged[item.self_ref] == 0]
    duplicate = sum(1 for ref in content.refs if tagged[ref] > 1)
    phantom = sorted(ref for ref in tagged if ref not in content.refs)
    by_label = Counter(item.label.value for item in missing)
    issues: list[str] = []
    if missing:
        labels = ", ".join(f"{label} {n}" for label, n in by_label.most_common())
        issues.append(
            f"{len(missing)} of {len(content.items)} items not in the HTML "
            f"({labels}; e.g. {', '.join(i.self_ref for i in missing[:_EXAMPLES])})"
        )
    if duplicate:
        issues.append(f"{duplicate} items tagged more than once")
    if phantom:
        issues.append(
            f"{len(phantom)} data-self-ref not in document.json "
            f"(e.g. {', '.join(phantom[:_EXAMPLES])})"
        )
    return HtmlCoverage(
        items=len(content.items),
        tagged_once=sum(1 for ref in content.refs if tagged[ref] == 1),
        missing=len(missing),
        missing_by_label=dict(by_label),
        duplicate=duplicate,
        phantom=len(phantom),
        issues=issues,
    )


def _check_page_recall(
    content: _DocContent, pdf_pages: list[str], *, converted: Collection[int]
) -> PageRecall:
    """Recall of the PDF's words on the *converted* pages: a conversion
    capped by ``max_num_pages`` is not charged for the pages after the cap."""
    pdf_words = {
        page_no: Counter(_words(text))
        for page_no, text in enumerate(pdf_pages, start=1)
        if page_no in converted
    }
    pdf_all: Counter[str] = Counter()
    for words in pdf_words.values():
        pdf_all.update(words)
    total = sum(pdf_all.values())
    if not total:
        return PageRecall(no_text_layer=True)

    flagged: list[PageRecallFlag] = []
    worst: tuple[float, int] | None = None
    checked = 0
    for page_no, words in pdf_words.items():
        n = sum(words.values())
        if n < PAGE_MIN_WORDS:
            continue
        checked += 1
        on_page = content.page_words.get(page_no, Counter())
        recall = _recall(words, on_page) or 0.0
        lost = sum((words - on_page).values())
        if worst is None or recall < worst[0]:
            worst = (recall, page_no)
        if recall < PAGE_RECALL_MIN or lost >= PAGE_LOST_WORDS_MAX:
            flagged.append(
                PageRecallFlag(
                    page=page_no,
                    pdf_words=n,
                    recall=recall,
                    lost=lost,
                    top_missing=_top_missing(words, on_page),
                )
            )

    document_recall = _recall(pdf_all, content.all_words)
    issues: list[str] = []
    if document_recall is not None and document_recall < DOCUMENT_RECALL_MIN:
        lost = sum((pdf_all - content.all_words).values())
        issues.append(
            f"document.json holds {document_recall:.3f} of the PDF's words "
            f"({lost} of {total} missing)"
        )
    issues.extend(
        f"p{flag.page}: recall {flag.recall:.2f}, {flag.lost} of {flag.pdf_words} "
        f"words missing (e.g. {', '.join(flag.top_missing)})"
        for flag in flagged
    )
    return PageRecall(
        pdf_words=total,
        document_recall=document_recall,
        pages_checked=checked,
        min_page=worst[1] if worst is not None else None,
        min_page_recall=worst[0] if worst is not None else None,
        flagged_pages=flagged,
        issues=issues,
    )


def _check_uncovered_text(
    content: _DocContent, pages: Mapping[int, PageItem], pdf_path: Path
) -> UncoveredText:
    """Where the words are, which page recall does not look at: the printed
    words of each converted page whose letters lie in no item box on that
    page, of any item (a continuation boxed on the wrong spot, a panel the
    layout left out). Text printed off the visible page is left out; pages
    under ``PAGE_MIN_WORDS`` words are not flagged.

    A background item is a watermark printed across the page: its upright
    box would cover every word, so it is not a box here, and as many
    uncovered words as it holds are its own."""
    import pypdfium2 as pdfium

    boxes: dict[int, list[tuple[float, float, float, float]]] = {}
    background_words: Counter[int] = Counter()
    for item in content.items:
        for prov in item.prov:
            if prov.page_no not in pages:
                continue
            if item.content_layer == ContentLayer.BACKGROUND:
                background_words[prov.page_no] += len(
                    _LETTER_WORD.findall(_item_text(item))
                )
                continue
            box = prov.bbox.to_top_left_origin(pages[prov.page_no].size.height)
            boxes.setdefault(prov.page_no, []).append((box.l, box.t, box.r, box.b))

    result = UncoveredText()
    flagged: list[UncoveredTextPage] = []
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        for page_no in sorted(pages):
            if not 1 <= page_no <= len(pdf):
                continue
            page = pdf[page_no - 1]
            text, centres = _page_glyphs(page)
            page.close()
            flag = _uncovered_on_page(
                page_no, text, centres, boxes.get(page_no, []), pages[page_no].size
            )
            own = min(flag.uncovered_words, background_words[page_no])
            if own:
                flag.uncovered_words -= own
                flag.share = round(flag.uncovered_words / flag.words, 4)
            result.chars += flag.chars
            result.uncovered_chars += flag.uncovered_chars
            result.words += flag.words
            result.uncovered_words += flag.uncovered_words
            if flag.words < PAGE_MIN_WORDS:
                continue
            result.pages_checked += 1
            if result.max_page_share is None or flag.share > result.max_page_share:
                result.max_page, result.max_page_share = page_no, flag.share
            if (
                flag.share > UNCOVERED_SHARE_MAX
                or flag.uncovered_words >= UNCOVERED_WORDS_MAX
            ):
                flagged.append(flag)
    finally:
        pdf.close()

    result.no_text_layer = not result.chars
    result.flagged_pages = flagged
    result.issues = [
        f"p{flag.page}: {flag.uncovered_words} of {flag.words} words "
        f"({flag.share:.0%}) outside every item box (e.g. {flag.sample!r})"
        for flag in flagged
    ]
    return result


def _page_glyphs(page: PdfPage) -> tuple[str, np.ndarray]:
    """The characters of *page* in text order and the centre of each printed
    one in Docling's frame, top-left of the page as displayed (CropBox,
    ``/Rotate``; the inverse of ``text_repair._user_space_rect``). NaN for
    spaces and the characters pdfium generates."""
    import pypdfium2.raw as pdfium_c

    left, bottom, right, top = page.get_bbox()
    rotation = page.get_rotation()
    textpage = page.get_textpage()
    try:
        count = textpage.count_chars()
        chars: list[str] = []
        centres = np.full((count, 2), np.nan)
        for index in range(count):
            char = chr(pdfium_c.FPDFText_GetUnicode(textpage.raw, index))
            chars.append(char)
            if char.isspace() or pdfium_c.FPDFText_IsGenerated(textpage.raw, index):
                continue
            char_left, char_bottom, char_right, char_top = textpage.get_charbox(index)
            x, y = (char_left + char_right) / 2, (char_bottom + char_top) / 2
            if rotation == 90:
                centres[index] = (y - bottom, x - left)
            elif rotation == 180:
                centres[index] = (right - x, y - bottom)
            elif rotation == 270:
                centres[index] = (top - y, right - x)
            else:
                centres[index] = (x - left, top - y)
        return "".join(chars), centres
    finally:
        textpage.close()


def _uncovered_on_page(
    page_no: int,
    text: str,
    centres: np.ndarray,
    boxes: list[tuple[float, float, float, float]],
    size: Size,
) -> UncoveredTextPage:
    x, y = centres[:, :1], centres[:, 1:]
    # NaN compares false: spaces are neither shown nor uncovered.
    shown = ((x >= 0) & (x <= size.width) & (y >= 0) & (y <= size.height)).ravel()
    inside = np.zeros(len(text), dtype=bool)
    if boxes:
        left, top, right, bottom = np.asarray(boxes).T
        tol = _BOX_TOLERANCE
        inside = (
            (x >= left - tol)
            & (x <= right + tol)
            & (y >= top - tol)
            & (y <= bottom + tol)
        ).any(axis=1)
    uncovered = shown & ~inside

    words = uncovered_words = 0
    for match in _LETTER_WORD.finditer(text):
        start, end = match.span()
        letters = int(shown[start:end].sum())
        if not letters:
            continue
        words += 1
        if 2 * int(uncovered[start:end].sum()) > letters:
            uncovered_words += 1
    kept = "".join(
        char if out and char.isprintable() else " "
        for char, out in zip(text, uncovered)
    )
    return UncoveredTextPage(
        page=page_no,
        words=words,
        uncovered_words=uncovered_words,
        share=round(uncovered_words / words, 4) if words else 0.0,
        chars=int(shown.sum()),
        uncovered_chars=int(uncovered.sum()),
        sample=" ".join(kept.split())[:_SAMPLE_CHARS],
    )


def _check_export_fidelity(
    content: _DocContent,
    exports: dict[str, str | None],
    chunks: list[_ChunkRow] | None,
) -> ExportFidelity:
    views: dict[str, tuple[Counter[str], str | None]] = {
        "html": (content.all_words, exports["html"]),
        "md": (content.body_words, exports["md"]),
        "chunks": (
            content.body_words,
            # HybridChunker keeps section headers in `headings`, not `text`.
            "\n".join(
                [
                    exports["chunks"] or "",
                    *dict.fromkeys(h for c in chunks for h in c.headings),
                ]
            )
            if chunks is not None
            else None,
        ),
    }
    if all(text is None for _ref, text in views.values()):
        return ExportFidelity(skipped="no html, md or chunks.jsonl in the bundle")
    scores: dict[str, float | None] = {}
    issues: list[str] = []
    for name, (reference, text) in views.items():
        if text is None:
            scores[name] = None
            continue
        words = Counter(_words(text))
        scores[name] = recall = _recall(reference, words)
        if recall is not None and recall < EXPORT_FIDELITY_MIN:
            source = "every item" if name == "html" else "the body"
            missing = ", ".join(_top_missing(reference, words))
            issues.append(
                f"{name} holds {recall:.3f} of the words of {source} of "
                f"document.json (missing e.g. {missing})"
            )
    return ExportFidelity(
        html=scores["html"], md=scores["md"], chunks=scores["chunks"], issues=issues
    )


def _check_ligature_splits(
    exports: dict[str, str | None], pdf_pages: list[str]
) -> LigatureSplits:
    known = set(
        _ALPHA.findall(unicodedata.normalize("NFKC", "\n".join(pdf_pages)).lower())
    )
    per_export: dict[str, int] = {}
    examples: list[str] = []
    for name, text in exports.items():
        if text is None:
            continue
        splits = _ligature_splits(text, known)
        per_export[name] = len(splits)
        examples.extend(s for s in splits if s not in examples)
    issues: list[str] = []
    if any(per_export.values()):
        counts = ", ".join(f"{name} {n}" for name, n in per_export.items())
        examples_txt = "; ".join(repr(e) for e in examples[:_EXAMPLES])
        issues.append(f"ligatures split off their word ({counts}; e.g. {examples_txt})")
    return LigatureSplits(
        per_export=per_export, examples=examples[:_EXAMPLES], issues=issues
    )


def _ligature_splits(text: str, known: set[str]) -> list[str]:
    """Lone ``fi``/``fl``/... tokens that join a neighbour into a word the
    PDF prints (same rule as :func:`~docling.engines.text_repair.repair_ligature_splits`)."""
    tokens = text.split()
    found: list[str] = []
    for i, token in enumerate(tokens):
        if token not in LIGATURES:
            continue
        tail = _letters(WORD_TAIL, tokens[i - 1]) if i else ""
        head = _letters(WORD_HEAD, tokens[i + 1]) if i + 1 < len(tokens) else ""
        if (
            (tail and head and tail + token + head in known)
            or (head and token + head in known)
            or (tail and tail + token in known)
        ):
            found.append(" ".join(tokens[max(0, i - 1) : i + 2]))
    return found


def _letters(pattern: re.Pattern[str], word: str) -> str:
    match = pattern.search(word)
    return match.group().lower() if match is not None else ""


def _check_tables(doc: DoclingDocument) -> TableCheck:
    low: list[TableRecall] = []
    degenerate: list[DegenerateTable] = []
    for table in doc.tables:
        pdf_text = get_table_pdf_text(table)
        recall = pdf_text["cell_text_recall"] if pdf_text is not None else None
        if recall is not None and recall < TABLE_TEXT_MIN_RECALL:
            low.append(TableRecall(self_ref=table.self_ref, cell_text_recall=recall))
        data = table.data
        rows, cols = data.num_rows, data.num_cols
        reason = degenerate_table_reason(rows, cols, data.table_cells)
        if reason is None:
            continue
        degenerate.append(
            DegenerateTable(
                self_ref=table.self_ref,
                page=table.prov[0].page_no if table.prov else None,
                rows=rows,
                cols=cols,
                filled_fraction=table_filled_fraction(rows, cols, data.table_cells),
                reason=reason,
            )
        )
    issues = [
        f"{t.self_ref} (p{t.page}, {t.rows}x{t.cols}) degenerate: {t.reason}"
        for t in degenerate
    ]
    return TableCheck(
        count=len(doc.tables), low_recall=low, degenerate=degenerate, issues=issues
    )


def _check_chunks(
    content: _DocContent, chunks: list[_ChunkRow] | None, run: RunRecord | None
) -> ChunkCheck:
    if chunks is None:
        return ChunkCheck(skipped="no chunks.jsonl in the bundle")
    max_tokens = run.chunk_max_tokens if run is not None else None
    empty = sum(1 for c in chunks if not c.text.strip())
    over = (
        sum(
            1
            for c in chunks
            if c.token_count is not None and c.token_count > max_tokens
        )
        if max_tokens is not None
        else 0
    )
    unresolved = sorted({ref for c in chunks for ref in c.self_refs} - content.refs)
    issues: list[str] = []
    if empty:
        issues.append(f"{empty} chunks with empty text")
    if over:
        issues.append(f"{over} chunks over chunk_max_tokens ({max_tokens})")
    if unresolved:
        issues.append(
            f"{len(unresolved)} self_refs not in document.json "
            f"(e.g. {', '.join(unresolved[:_EXAMPLES])})"
        )
    return ChunkCheck(
        count=len(chunks),
        empty=empty,
        max_tokens=max_tokens,
        over_max_tokens=over,
        unresolved_refs=unresolved,
        issues=issues,
    )


def _check_structure(doc: DoclingDocument) -> StructureCheck:
    report = quality_report(doc)
    return StructureCheck(
        pages=report.pages,
        body_text_items=report.body_text_items,
        section_headers=report.section_headers,
        warnings=[warning.code for warning in report.warnings],
        issues=[
            f"{warning.code}: {warning.detail}"
            for warning in report.warnings
            if warning.blocking or warning.code in _STRUCTURE_ISSUE_CODES
        ],
    )


def _check_guards(
    pdf_dir: Path,
    run: RunRecord | None,
    figures: list[_ImageRow],
    table_rows: list[_ImageRow],
    md_raw: str | None,
    tags: list[tuple[str, str]] | None,
) -> GuardCheck:
    issues: list[str] = []
    if run is None:
        issues.append("no run.json in the bundle")
    else:
        status = (run.status or "").rsplit(".", 1)[-1].lower()
        if status != ConversionStatus.SUCCESS.value:
            issues.append(f"run.json status is {run.status}")
        if run.errors:
            issues.append(f"run.json lists {len(run.errors)} errors")
    missing = [
        row.image_path
        for row in (*figures, *table_rows)
        if row.image_path is not None and not (pdf_dir / row.image_path).is_file()
    ]
    if missing:
        issues.append(
            f"{len(missing)} images missing (e.g. {', '.join(missing[:_EXAMPLES])})"
        )

    first_tag: dict[str, str] = {}
    for ref, tag in tags or []:
        first_tag.setdefault(ref, tag)
    noise = {row.self_ref: row.image_path for row in figures if row.is_noise}
    in_md = [
        ref
        for ref, image_path in noise.items()
        if md_raw is not None and image_path and f"]({image_path})" in md_raw
    ]
    unmarked = [
        ref
        for ref in noise
        if tags is not None and "data-noise=" not in first_tag.get(ref, "")
    ]
    if in_md:
        issues.append(f"noise pictures shown in the markdown: {', '.join(in_md)}")
    if unmarked:
        issues.append(
            f"noise pictures without data-noise in the HTML: {', '.join(unmarked)}"
        )
    return GuardCheck(
        run_status=run.status if run is not None else None,
        run_errors=len(run.errors) if run is not None else 0,
        missing_images=missing,
        noise_in_md=in_md,
        noise_unmarked_in_html=unmarked,
        issues=issues,
    )
