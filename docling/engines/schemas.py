# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Output schemas for the Amir Engine wrappers."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from docling.datamodel.base_models import ConversionStatus
from docling.engines.export_check import BundleCheck
from docling.engines.structure import DocumentStructure, QualityReport


class SourceKind(str, Enum):
    """Where the input document came from."""

    LOCAL_PATH = "local_path"
    URL = "url"
    STREAM = "stream"


class PageSummary(BaseModel):
    """Minimal per-page summary for downstream tooling and previews."""

    page_no: int = Field(..., ge=1, description="1-indexed page number.")
    width: float | None = Field(None, description="Page width in points, if known.")
    height: float | None = Field(None, description="Page height in points, if known.")
    cluster_count: int = Field(
        0, ge=0, description="Number of layout clusters detected on the page."
    )


class PdfEngineError(BaseModel):
    """One error item surfaced by the pipeline (component + message)."""

    component: str
    message: str


class RelatedDocument(BaseModel):
    """Another PDF this one belongs with, as recorded in ``run.json``: the
    manuscript of a supplement, or a supplement of a manuscript."""

    role: Literal["manuscript", "supplement"]
    file_name: str
    file_size_bytes: int | None = None
    binary_hash: str | None = Field(
        None, description="Docling's SHA-256 of the file (``source.binary_hash``)."
    )
    bundle: str | None = Field(
        None, description="Name of its bundle folder, next to this one."
    )
    pairing: str | None = Field(
        None, description="How the two were paired, e.g. ``file-name``."
    )


class PdfConversionOutput(BaseModel):
    """Result of :meth:`PdfEngine.convert` — a typed snapshot of the conversion.

    The full :class:`docling.datamodel.document.ConversionResult` is referenced
    via :attr:`raw` so callers can drop down to upstream APIs when needed.
    """

    model_config = {"arbitrary_types_allowed": True}

    status: ConversionStatus
    source: str = Field(..., description="String form of the input (path or URL).")
    source_kind: SourceKind
    page_count: int = Field(0, ge=0)
    pages: list[PageSummary] = Field(default_factory=list)
    errors: list[PdfEngineError] = Field(default_factory=list)
    markdown: str | None = Field(
        None,
        description=(
            "Primary markdown export. When ``save_artifacts=True`` and "
            "``link_images=True`` (defaults), image placeholders are replaced "
            "with relative ``![](images/picture_NNN.png)`` references so the "
            "file renders in any markdown viewer."
        ),
    )
    markdown_path: Path | None = Field(
        None,
        description="Path to ``<stem>.md``, the primary markdown, when written.",
    )
    markdown_embedded_path: Path | None = Field(
        None,
        description=(
            "Path to ``<stem>.embedded.md`` — a second, standalone markdown "
            "file with images inlined as base64 data URIs. Written when "
            "``embed_images=True``."
        ),
    )
    html_path: Path | None = Field(
        None,
        description=(
            "Path to ``<stem>.html`` — the manuscript as one standalone HTML "
            "page (images inlined) whose blocks carry ``data-self-ref`` / "
            "``data-page`` / ``data-bbox``, with a JSON manifest of figures, "
            "tables, chunks and run metadata. Written when ``embed_images=True``."
        ),
    )
    output_dir: Path | None = Field(
        None,
        description="Directory where artifacts (markdown, json) were saved, if any.",
    )
    document_json: Path | None = Field(
        None,
        description="Path to the saved DoclingDocument JSON, when artifacts were written.",
    )
    nodes_jsonl: Path | None = Field(
        None,
        description="Path to the per-node JSONL, when artifacts were written.",
    )
    chunks_jsonl: Path | None = Field(
        None,
        description="Path to the HybridChunker chunks JSONL, when chunking ran.",
    )
    tables_jsonl: Path | None = Field(
        None,
        description="Path to ``tables.jsonl`` — one row per TableItem (markdown + html + flat cells with spans + caption + image_path).",
    )
    figures_jsonl: Path | None = Field(
        None,
        description="Path to ``figures.jsonl`` — one row per PictureItem (caption_text + figure_type + vlm_caption + generic_classifier_label + image_path).",
    )
    run_json: Path | None = Field(
        None,
        description="Path to the run snapshot (env, timing, config, models).",
    )
    picture_images: list[Path] = Field(
        default_factory=list,
        description="Paths to extracted figure images.",
    )
    table_images: list[Path] = Field(
        default_factory=list,
        description="Paths to extracted table images.",
    )
    preview_html: Path | None = Field(
        None,
        description="Path to the HTML bounding-box viewer, when rendered.",
    )
    preview_html_embedded: Path | None = Field(
        None,
        description=(
            "Path to ``preview.embedded.html`` — the same viewer with all "
            "images inlined as data URIs (written when ``embed_images=True``)."
        ),
    )
    check_json: Path | None = Field(
        None,
        description=(
            "Path to ``check.json`` — the bundle self-check "
            "(:func:`~docling.engines.export_check.check_bundle`)."
        ),
    )
    check: BundleCheck | None = Field(
        None,
        description="The bundle self-check written to ``check_json``.",
    )
    structure: DocumentStructure | None = Field(
        None,
        description=(
            "Outline, per-element roles and links, and relabelled items "
            "(:func:`~docling.engines.structure.structure_document`)."
        ),
    )
    structure_json: Path | None = Field(
        None, description="Path to ``structure.json``, when artifacts were written."
    )
    quality: QualityReport | None = Field(
        None,
        description=(
            "Label counts and warnings (``run.json`` → ``quality``); a "
            "blocking warning also sets ``status`` to PARTIAL_SUCCESS and "
            "adds a ``quality`` error."
        ),
    )
    # `raw` is not part of the serialisable schema — it carries the underlying
    # ConversionResult so callers can drop down to upstream APIs.
    raw: object | None = Field(default=None, exclude=True, repr=False)

    @property
    def succeeded(self) -> bool:
        return self.status in {
            ConversionStatus.SUCCESS,
            ConversionStatus.PARTIAL_SUCCESS,
        }

    def kind(self) -> Literal["pdf"]:
        return "pdf"
