# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for :class:`docling.engines.PdfEngine` (Phase 1)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    PictureClassificationClass,
    PictureClassificationData,
    PictureMeta,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
)

from docling.datamodel.base_models import ConversionStatus
from docling.engines import PdfConversionOutput, PdfEngine, SourceKind
from docling.engines.figure_typing import (
    BIOMEDCLIP_REPO,
    FIGURE_TYPES,
    FigureTypePrediction,
    get_figure_type,
)
from docling.engines.picture_filter import classify_pictures
from docling.engines.text_repair import repair_ligature_splits
from docling.engines.validation import (
    InvalidPdfSourceError,
    classify_source,
    validate_pdf_source,
)

FIXTURE_PDF = Path("tests/data/pdf/sources/2305.03393v1-pg9.pdf")


def test_classify_source_url() -> None:
    assert classify_source("https://example.com/x.pdf") is SourceKind.URL
    assert classify_source("http://example.com/x.pdf") is SourceKind.URL


def test_classify_source_local_path() -> None:
    assert classify_source("relative/path.pdf") is SourceKind.LOCAL_PATH
    assert classify_source(Path("/tmp/x.pdf")) is SourceKind.LOCAL_PATH
    # `file://` is not treated as URL by the engine — local paths only.
    assert classify_source("file:///tmp/x.pdf") is SourceKind.LOCAL_PATH


def test_validate_pdf_source_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.pdf"
    with pytest.raises(InvalidPdfSourceError, match="does not exist"):
        validate_pdf_source(missing)


def test_validate_pdf_source_rejects_non_pdf_suffix(tmp_path: Path) -> None:
    not_pdf = tmp_path / "doc.txt"
    not_pdf.write_text("hello")
    with pytest.raises(InvalidPdfSourceError, match=r"\.pdf suffix"):
        validate_pdf_source(not_pdf)


def test_validate_pdf_source_accepts_url() -> None:
    kind, normalised = validate_pdf_source("https://arxiv.org/pdf/2206.01062")
    assert kind is SourceKind.URL
    assert normalised == "https://arxiv.org/pdf/2206.01062"


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_converts_local_fixture(tmp_path: Path) -> None:
    """End-to-end conversion of a small bundled PDF.

    Verifies the wrapper's contract: status, source classification, page
    summaries, and markdown export are populated and internally consistent.
    """
    engine = PdfEngine(
        save_artifacts=False,
        embed_images=False,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output: PdfConversionOutput = engine.convert(FIXTURE_PDF, output_dir=tmp_path)

    assert output.succeeded, f"conversion failed: {output.errors}"
    assert output.status in {
        ConversionStatus.SUCCESS,
        ConversionStatus.PARTIAL_SUCCESS,
    }
    assert output.source_kind is SourceKind.LOCAL_PATH
    assert output.source.endswith(FIXTURE_PDF.name)

    # At least one page must have been processed with a layout summary.
    assert output.page_count >= 1
    assert len(output.pages) >= 1
    first = output.pages[0]
    assert first.page_no >= 1
    assert first.cluster_count >= 0  # may be 0 on tiny/empty pages

    # Markdown export landed on disk in a per-PDF subfolder.
    assert output.markdown is not None and output.markdown.strip()
    pdf_dir = tmp_path / FIXTURE_PDF.stem
    assert output.output_dir == pdf_dir
    written = pdf_dir / f"{FIXTURE_PDF.stem}.md"
    assert written.exists()
    assert written.read_text(encoding="utf-8") == output.markdown

    # The schema must serialise without leaking the raw ConversionResult.
    dumped = output.model_dump()
    assert "raw" not in dumped


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_renders_html_preview(tmp_path: Path) -> None:
    """End-to-end: page images are retained and an HTML preview is written."""
    engine = PdfEngine(
        with_page_images=True,
        images_scale=1.0,
        save_artifacts=False,
        embed_images=False,
        picture_description=None,
        granite_vision_tables=False,
        filter_noise_pictures=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path, make_html_preview=True)

    assert output.succeeded, f"conversion failed: {output.errors}"
    assert output.preview_html is not None
    assert output.preview_html.exists()
    assert output.preview_html.name == "preview.html"

    html_text = output.preview_html.read_text(encoding="utf-8")
    # Structural smoke checks rather than mock-driven assertions:
    assert "<!doctype html>" in html_text
    assert "Docling preview" in html_text
    assert 'class="bbox"' in html_text
    assert 'class="legend"' in html_text

    # Page images landed under the per-PDF subdir.
    pdf_dir = tmp_path / FIXTURE_PDF.stem
    assert output.preview_html == pdf_dir / "preview.html"
    pngs = sorted((pdf_dir / "images").glob("page_*.png"))
    assert pngs, "no page images were written"
    assert all(p.stat().st_size > 0 for p in pngs)
    assert output.preview_html_embedded is None


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_standalone_html_preview(tmp_path: Path) -> None:
    """``embed_images=True`` adds a preview that works without ``images/``."""
    engine = PdfEngine(
        images_scale=1.0,
        picture_description=None,
        granite_vision_tables=False,
        filter_noise_pictures=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path, make_html_preview=True)

    assert output.succeeded, f"conversion failed: {output.errors}"
    assert output.preview_html_embedded is not None
    standalone = output.preview_html_embedded.read_text(encoding="utf-8")
    assert "images/" not in standalone
    assert "data:image/jpeg;base64," in standalone
    # The linked preview is left untouched for folder-based sharing.
    assert "images/page_" in output.preview_html.read_text(encoding="utf-8")


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_embedded_markdown_companion(tmp_path: Path) -> None:
    """``embed_images=True`` writes a second ``<stem>.embedded.md`` companion."""
    engine = PdfEngine(
        embed_images=True,
        images_scale=1.0,
        save_artifacts=True,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path)

    assert output.succeeded, f"conversion failed: {output.errors}"
    pdf_dir = tmp_path / FIXTURE_PDF.stem

    # Primary stays small (linked refs); the embedded companion holds base64.
    assert output.markdown_embedded_path == pdf_dir / f"{FIXTURE_PDF.stem}.embedded.md"
    assert output.markdown_embedded_path.exists()
    embedded = output.markdown_embedded_path.read_text(encoding="utf-8")
    assert "<!-- image -->" not in embedded
    if "![" in embedded:
        assert "data:image" in embedded

    # Primary `.md` exists and has no base64 blobs.
    primary = pdf_dir / f"{FIXTURE_PDF.stem}.md"
    assert primary.exists()
    assert "data:image" not in primary.read_text(encoding="utf-8")


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_links_images_in_primary_markdown(tmp_path: Path) -> None:
    """``link_images=True`` (default) rewrites placeholders to ``![](images/..)``."""
    engine = PdfEngine(
        embed_images=False,
        link_images=True,
        images_scale=1.0,
        save_artifacts=True,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path)

    assert output.succeeded, f"conversion failed: {output.errors}"
    if not output.picture_images:
        pytest.skip("fixture has no extracted pictures to link")

    assert output.markdown is not None
    # Every saved picture should be referenced; no leftover placeholders for them.
    placeholders = output.markdown.count("<!-- image -->")
    assert placeholders == 0
    for picture in output.picture_images:
        rel = picture.relative_to(output.output_dir).as_posix()
        assert f"![]({rel})" in output.markdown


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_artifacts(tmp_path: Path) -> None:
    """``save_artifacts=True`` writes document.json, nodes.jsonl, and images."""
    engine = PdfEngine(
        images_scale=1.0,
        save_artifacts=True,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path)

    assert output.succeeded, f"conversion failed: {output.errors}"
    pdf_dir = tmp_path / FIXTURE_PDF.stem

    assert output.document_json == pdf_dir / "document.json"
    assert output.document_json.exists()
    doc = json.loads(output.document_json.read_text(encoding="utf-8"))
    assert isinstance(doc, dict) and doc  # non-empty JSON object

    assert output.nodes_jsonl == pdf_dir / "nodes.jsonl"
    assert output.nodes_jsonl.exists()
    lines = output.nodes_jsonl.read_text(encoding="utf-8").splitlines()
    assert lines, "nodes.jsonl should not be empty"
    sample = json.loads(lines[0])
    # Every node carries our kind/level annotations and a label.
    assert "_kind" in sample and "_level" in sample and "label" in sample

    # All referenced images actually exist on disk.
    for img_path in output.picture_images + output.table_images:
        assert img_path.exists()
        assert img_path.stat().st_size > 0
        assert img_path.parent == pdf_dir / "images"

    # run.json captures the per-conversion snapshot for reproducibility.
    assert output.run_json == pdf_dir / "run.json"
    assert output.run_json.exists()
    run = json.loads(output.run_json.read_text(encoding="utf-8"))
    for key in (
        "schema_version",
        "source",
        "status",
        "timing",
        "engine_config",
        "pipeline_options",
        "models",
        "environment",
        "output_summary",
    ):
        assert key in run, f"run.json missing '{key}'"
    assert run["timing"]["duration_seconds"] > 0
    assert run["environment"]["python"]
    assert run["engine_config"]["save_artifacts"] is True


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_chunks(tmp_path: Path) -> None:
    """``save_artifacts=True`` also produces ``chunks.jsonl`` via HybridChunker."""
    engine = PdfEngine(
        images_scale=1.0,
        save_artifacts=True,
        embed_images=False,
        chunk_max_tokens=512,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path)

    assert output.succeeded, f"conversion failed: {output.errors}"
    pdf_dir = tmp_path / FIXTURE_PDF.stem
    assert output.chunks_jsonl == pdf_dir / "chunks.jsonl"
    assert output.chunks_jsonl.exists()

    lines = output.chunks_jsonl.read_text(encoding="utf-8").splitlines()
    assert lines, "chunks.jsonl should not be empty"
    sample = json.loads(lines[0])
    for key in ("index", "text", "token_count", "headings", "page_nos", "self_refs"):
        assert key in sample, f"chunk row missing '{key}'"
    # Token budget is respected by HybridChunker.
    for raw in lines:
        row = json.loads(raw)
        if row["token_count"] is not None:
            assert row["token_count"] <= 512


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_picture_description_config() -> None:
    """``picture_description`` wires the right pipeline_options without firing the VLM."""
    from docling.datamodel.pipeline_options import (
        PictureDescriptionVlmEngineOptions,
    )

    engine = PdfEngine(
        save_artifacts=False,
        embed_images=False,
        picture_description="qwen25_vl_3b",
        picture_description_engine="vllm",
        figure_types=False,
    )
    opts = engine._pipeline_options
    assert opts is not None
    assert opts.do_picture_description is True
    assert isinstance(
        opts.picture_description_options, PictureDescriptionVlmEngineOptions
    )
    assert opts.picture_description_options.model_spec.default_repo_id == (
        "Qwen/Qwen2.5-VL-3B-Instruct"
    )


def test_pdf_engine_granite_vision_tables_config() -> None:
    """``granite_vision_tables=True`` swaps in the VLM table-structure options."""
    from docling.datamodel.pipeline_options import GraniteVisionTableStructureOptions

    engine = PdfEngine(
        save_artifacts=False,
        embed_images=False,
        granite_vision_tables=True,
        figure_types=False,
    )
    assert isinstance(
        engine._pipeline_options.table_structure_options,
        GraniteVisionTableStructureOptions,
    )


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_structured_outputs(tmp_path: Path) -> None:
    """``tables.jsonl`` / ``figures.jsonl`` written only when items exist; rows align with image crops."""
    engine = PdfEngine(
        images_scale=1.0,
        save_artifacts=True,
        embed_images=False,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path)
    assert output.succeeded, f"conversion failed: {output.errors}"

    if output.tables_jsonl is not None:
        rows = [
            json.loads(line) for line in output.tables_jsonl.read_text().splitlines()
        ]
        assert len(rows) == len(output.table_images)
        for row in rows:
            for key in (
                "index",
                "self_ref",
                "prov",
                "caption_text",
                "markdown",
                "num_rows",
                "num_cols",
                "cells",
            ):
                assert key in row

    if output.figures_jsonl is not None:
        rows = [
            json.loads(line) for line in output.figures_jsonl.read_text().splitlines()
        ]
        assert len(rows) == len(output.picture_images)
        for row in rows:
            for key in (
                "index",
                "self_ref",
                "prov",
                "caption_text",
                "image_path",
                "vlm_caption",
                "figure_type",
                "figure_type_confidence",
                "generic_classifier_label",
            ):
                assert key in row


def test_classifier_noise_ignores_large_pictures() -> None:
    """A generic-classifier noise label only counts for small pictures: the
    classifier called a page-wide 3-D CT rendering ``icon``, which hid it
    from the markdown."""
    doc = DoclingDocument(name="noise")
    doc.add_page(page_no=1, size=Size(width=600, height=800))

    def picture(label: str, bbox: BoundingBox) -> None:
        doc.add_picture(
            prov=ProvenanceItem(page_no=1, bbox=bbox, charspan=(0, 0)),
            annotations=[
                PictureClassificationData(
                    provenance="test",
                    predicted_classes=[
                        PictureClassificationClass(class_name=label, confidence=0.9)
                    ],
                )
            ],
        )

    picture("logo", BoundingBox(l=20, t=20, r=60, b=60))  # 0.3 % of page
    picture("icon", BoundingBox(l=100, t=200, r=400, b=400))  # 12.5 % of page

    logo, rendering = classify_pictures(SimpleNamespace(document=doc))
    assert logo.is_noise and logo.noise_reason == "classifier:logo"
    assert not rendering.is_noise


def test_confident_medical_image_overrules_classifier_noise_label() -> None:
    """Small echo frames inside a composite figure get ``icon`` / ``logo`` from
    the generic classifier; a confident BiomedCLIP imaging type keeps them.
    The cases mirror the corpus check: a QR code typed ultrasound 0.85 and a
    Springer logo typed ecg 1.00 stay noise."""
    doc = DoclingDocument(name="noise")
    doc.add_page(page_no=1, size=Size(width=600, height=800))

    def picture(x: float, label: str, figure_type: str, confidence: float) -> None:
        pic = doc.add_picture(
            prov=ProvenanceItem(
                page_no=1,
                bbox=BoundingBox(l=x, t=20, r=x + 40, b=60),
                charspan=(0, 0),
            ),
            annotations=[
                PictureClassificationData(
                    provenance="test",
                    predicted_classes=[
                        PictureClassificationClass(class_name=label, confidence=0.9)
                    ],
                )
            ],
        )
        pic.meta = PictureMeta()
        pic.meta.set_custom_field(
            "amir",
            "figure_type",
            FigureTypePrediction(label=figure_type, confidence=confidence).model_dump(),
        )

    picture(20, "logo", "ultrasound", 0.9999)  # echo frame
    picture(100, "icon", "ultrasound", 0.85)  # QR code
    picture(180, "logo", "ecg", 1.0)  # Springer logo

    echo_frame, qr_code, springer = classify_pictures(SimpleNamespace(document=doc))
    assert not echo_frame.is_noise
    assert qr_code.is_noise and springer.is_noise


def test_ligature_split_words_are_rejoined_only_when_the_pdf_has_them() -> None:
    """The parser emits some ligature glyphs as words ("speci fi city"); a
    split is rejoined only into a word the page's PDF text layer contains."""
    doc = DoclingDocument(name="ligatures")
    doc.add_page(page_no=1, size=Size(width=600, height=800))
    prov = ProvenanceItem(
        page_no=1, bbox=BoundingBox(l=0, t=0, r=10, b=10), charspan=(0, 0)
    )
    para = doc.add_text(
        label=DocItemLabel.TEXT,
        text="the fi rst domain-speci fi c result, from a hi fi system",
        prov=prov,
    )
    table = doc.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="speci fi city",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                )
            ],
        ),
        prov=prov,
    )
    page_words = {1: {"the", "first", "domain", "specific", "specificity", "hi"}}

    assert repair_ligature_splits(doc, page_words) == 3
    assert para.text == "the first domain-specific result, from a hi fi system"
    assert table.data.table_cells[0].text == "specificity"


PICTURE_FIXTURE_PDF = Path("tests/data/pdf/sources/picture_classification.pdf")


@pytest.mark.skipif(
    not PICTURE_FIXTURE_PDF.exists() or importlib.util.find_spec("open_clip") is None,
    reason="needs the picture_classification fixture and open-clip-torch",
)
def test_pdf_engine_types_figures(tmp_path: Path) -> None:
    """BiomedCLIP types the fixture's stacked bar chart, and the type survives a
    ``document.json`` round-trip as the ``amir__figure_type`` meta field —
    without leaking into the text exports (markdown, chunks)."""
    engine = PdfEngine(
        images_scale=1.0,
        picture_description=None,
        granite_vision_tables=False,
    )
    output = engine.convert(PICTURE_FIXTURE_PDF, output_dir=tmp_path)
    assert output.succeeded, f"conversion failed: {output.errors}"

    rows = [json.loads(line) for line in output.figures_jsonl.read_text().splitlines()]
    assert rows[0]["figure_type"] == "bar_chart"
    assert rows[0]["figure_type_model"] == BIOMEDCLIP_REPO
    assert all(row["figure_type"] in FIGURE_TYPES for row in rows)

    reloaded = DoclingDocument.load_from_json(output.document_json)
    prediction = get_figure_type(reloaded.pictures[0])
    assert prediction is not None
    assert prediction.label == "bar_chart"

    # The fixture's text is lorem ipsum, so "Bar chart" could only come from the
    # generic classifier label, and "'label'" from the figure-type dict.
    texts = {
        "markdown": output.markdown,
        "embedded": output.markdown_embedded_path.read_text(encoding="utf-8"),
        "chunks": output.chunks_jsonl.read_text(encoding="utf-8"),
    }
    for name, text in texts.items():
        assert "Bar chart" not in text, name
        assert "'label'" not in text, name
