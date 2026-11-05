# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for the bundle self-check (:mod:`docling.engines.export_check`) and
the shared markdown policy (:mod:`docling.engines.serializers`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    PictureMeta,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
    TableItem,
)
from docling_core.types.doc.document import DescriptionMetaField, FloatingMeta

from docling.datamodel.document import ConversionResult
from docling.engines import (
    check_bundle,
    export_markdown,
    write_bundle_check,
    write_chunks,
    write_document_html,
)
from docling.engines.serializers import ANNOTATION_CLOSE, DESCRIPTION_OPEN

FIXTURE_PDF = Path("tests/data/pdf/sources/2305.03393v1-pg9.pdf")
FOUR_PAGES_PDF = Path("tests/data/pdf/sources/normal_4pages.pdf")
_PROV = ProvenanceItem(
    page_no=1, bbox=BoundingBox(l=50, t=700, r=550, b=660), charspan=(0, 0)
)
_DESCRIPTION = "The image shows a twelve-lead electrocardiogram."


def _grid(rows: list[list[str]]) -> TableData:
    return TableData(
        num_rows=len(rows),
        num_cols=len(rows[0]),
        table_cells=[
            TableCell(
                text=text,
                start_row_offset_idx=r,
                end_row_offset_idx=r + 1,
                start_col_offset_idx=c,
                end_col_offset_idx=c + 1,
            )
            for r, row in enumerate(rows)
            for c, text in enumerate(row)
        ],
    )


def _paper() -> DoclingDocument:
    """One page: heading, two paragraphs, a figure with a VLM description,
    a complete table."""
    doc = DoclingDocument(name="paper")
    doc.add_page(page_no=1, size=Size(width=600, height=800))
    doc.add_heading(text="Results", prov=_PROV)
    doc.add_text(label=DocItemLabel.TEXT, text="ST elevation in V1 to V3.", prov=_PROV)
    doc.add_text(
        label=DocItemLabel.TEXT,
        text="The agent flagged every infarction.",
        prov=_PROV,
    )
    ecg = doc.add_picture(prov=_PROV)
    ecg.meta = PictureMeta(
        description=DescriptionMetaField(text=_DESCRIPTION, created_by="a VLM")
    )
    doc.add_table(
        data=_grid([["Model", "AUC"], ["ECG-Agent", "0.91"]]),
        prov=_PROV,
    )
    return doc


def _write_bundle(
    tmp_path: Path, doc: DoclingDocument, *, extra_chunks: tuple[dict, ...] = ()
) -> Path:
    """The files of a bundle, as PdfEngine lays them out; one chunk holds
    the whole markdown."""
    pdf_dir = tmp_path / doc.name
    pdf_dir.mkdir()
    doc.save_as_json(pdf_dir / "document.json")
    markdown = export_markdown(doc)
    (pdf_dir / f"{doc.name}.md").write_text(markdown, encoding="utf-8")
    run = {
        "status": "ConversionStatus.SUCCESS",
        "source": {"input": str(tmp_path / "gone.pdf"), "file_name": "gone.pdf"},
        "engine_config": {"chunk_max_tokens": 512},
        "errors": [],
    }
    (pdf_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    body_refs = [item.self_ref for item, _ in doc.iterate_items(with_groups=False)]
    chunks = [
        {"index": 0, "text": markdown, "token_count": 80, "self_refs": body_refs},
        *extra_chunks,
    ]
    (pdf_dir / "chunks.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in chunks), encoding="utf-8"
    )
    write_document_html(doc, pdf_dir)
    return pdf_dir


def test_clean_bundle_is_ok(tmp_path: Path) -> None:
    """Every item tagged once, exports complete (the VLM description does not
    count as paper text), and only check.json is added to the bundle."""
    doc = _paper()
    pdf_dir = _write_bundle(tmp_path, doc)
    before = set(pdf_dir.iterdir())

    check = check_bundle(pdf_dir)

    assert check.ok, check.issues
    assert check.html_coverage.items == check.html_coverage.tagged_once == 5
    assert check.export_fidelity.md == check.export_fidelity.chunks == 1.0
    assert check.export_fidelity.html == 1.0
    assert check.page_recall.skipped and "gone.pdf" in check.page_recall.skipped
    assert check.summary_line().endswith("· OK")

    target = write_bundle_check(pdf_dir, check)
    assert set(pdf_dir.iterdir()) - before == {target}
    assert json.loads(target.read_text(encoding="utf-8"))["ok"] is True


def test_check_reports_a_missing_html_item_an_empty_chunk_and_a_degenerate_table(
    tmp_path: Path,
) -> None:
    doc = _paper()
    flat = doc.add_table(
        data=_grid([[f"metric {i}" for i in range(8)]]),  # one row of 8 columns
        prov=_PROV,
    )
    pdf_dir = _write_bundle(
        tmp_path,
        doc,
        extra_chunks=(
            {
                "index": 1,
                "text": "",
                "token_count": 0,
                "self_refs": [doc.texts[0].self_ref],
            },
        ),
    )
    para_ref = doc.texts[1].self_ref
    html_path = pdf_dir / "paper.html"
    html_text = html_path.read_text(encoding="utf-8")
    html_path.write_text(
        html_text.replace(f' data-self-ref="{para_ref}"', "", 1), encoding="utf-8"
    )

    check = check_bundle(pdf_dir)

    assert not check.ok
    assert [issue.split(":")[0] for issue in check.issues] == [
        "html_coverage",
        "tables",
        "chunks",
    ]
    assert check.html_coverage.missing == 1
    assert check.html_coverage.missing_by_label == {"text": 1}
    assert para_ref in check.html_coverage.issues[0]
    assert [t.self_ref for t in check.tables.degenerate] == [flat.self_ref]
    assert check.chunks.empty == 1
    assert check.summary_line().endswith("· 3 issues")


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(), reason=f"fixture {FIXTURE_PDF} not available"
)
def test_check_measures_page_recall_and_ligature_splits_against_the_pdf(
    tmp_path: Path,
) -> None:
    """A document holding half of the page's words is flagged with the words
    it lost; a ligature split off a word the PDF prints is counted per
    export."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(FIXTURE_PDF)
    page_text = re.sub(r"\ufffe\s*", "", pdf[0].get_textpage().get_text_range())
    pdf.close()
    words = page_text.split()

    def bundle(name: str, text: str) -> Path:
        doc = DoclingDocument(name=name)
        doc.add_page(page_no=1, size=Size(width=600, height=800))
        doc.add_text(label=DocItemLabel.TEXT, text=text, prov=_PROV)
        return _write_bundle(tmp_path, doc)

    complete = check_bundle(bundle("complete", page_text), FIXTURE_PDF)
    assert complete.page_recall.min_page_recall == 1.0
    assert complete.page_recall.issues == []
    assert complete.ligature_splits.per_export == {"md": 0, "html": 0, "chunks": 0}

    half_dir = bundle("half", " ".join(words[: len(words) // 2]))
    md_path = half_dir / "half.md"
    md_path.write_text(
        md_path.read_text(encoding="utf-8") + "\n\nIt is di ffi cult.\n",
        encoding="utf-8",
    )
    half = check_bundle(half_dir, FIXTURE_PDF)

    recall = half.page_recall
    assert recall.document_recall is not None and recall.document_recall < 0.7
    assert [flag.page for flag in recall.flagged_pages] == [1]
    dropped = " ".join(words[len(words) // 2 :]).casefold()
    assert all(word in dropped for word in recall.flagged_pages[0].top_missing)
    assert half.ligature_splits.per_export["md"] == 1
    assert half.ligature_splits.per_export["html"] == 0
    assert half.ligature_splits.examples == ["di ffi cult."]


@pytest.mark.skipif(
    not FOUR_PAGES_PDF.exists(), reason=f"fixture {FOUR_PAGES_PDF} not available"
)
def test_page_recall_leaves_out_the_pages_a_capped_conversion_did_not_reach(
    tmp_path: Path,
) -> None:
    """A conversion with ``max_num_pages=1`` of a four-page PDF holds page 1
    only; pages 2-4 are not lost words."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(FOUR_PAGES_PDF)
    page_text = re.sub(r"\ufffe\s*", "", pdf[0].get_textpage().get_text_range())
    pdf.close()
    doc = DoclingDocument(name="capped")
    doc.add_page(page_no=1, size=Size(width=600, height=800))
    doc.add_text(label=DocItemLabel.TEXT, text=page_text, prov=_PROV)

    recall = check_bundle(_write_bundle(tmp_path, doc), FOUR_PAGES_PDF).page_recall

    assert recall.issues == []
    assert recall.pages_checked == 1
    assert recall.document_recall == 1.0


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(), reason=f"fixture {FIXTURE_PDF} not available"
)
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_uncovered_text_flags_words_whose_box_is_misplaced(
    tmp_path: Path, rotation: int
) -> None:
    """With every text line boxed where Docling's parser puts it, no printed
    character is uncovered, also on a cropped and rotated page. One item
    holding the lower half of the page with its box 180 pt too high, as a
    page-height mix-up puts it, gets those words flagged with a sample of
    them, while page recall (words per page) sees nothing."""
    import pypdfium2 as pdfium

    from docling.backend.docling_parse_backend import (
        ThreadedDoclingParseDocumentBackend,
    )
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import InputDocument

    pdf = pdfium.PdfDocument(FIXTURE_PDF)
    page = pdf[0]
    left, bottom, right, top = page.get_mediabox()
    page.set_cropbox(left + 30, bottom + 45, right - 20, top - 10)
    page.set_rotation(rotation)
    cropped = tmp_path / "cropped.pdf"
    pdf.save(cropped)
    pdf.close()
    backend = InputDocument(
        path_or_stream=cropped,
        format=InputFormat.PDF,
        backend=ThreadedDoclingParseDocumentBackend,
    )._backend
    page_backend = next(backend.iter_pages())
    size = page_backend.get_size()
    lines = [
        (cell.text, cell.rect.to_bounding_box().to_top_left_origin(size.height))
        for cell in page_backend.get_text_cells()
        if cell.text.strip()
    ]
    backend.unload()

    def bundle(name: str, boxed: list[tuple[str, BoundingBox]]) -> Path:
        doc = DoclingDocument(name=name)
        doc.add_page(page_no=1, size=size)
        for text, box in boxed:
            doc.add_text(
                label=DocItemLabel.TEXT,
                text=text,
                prov=ProvenanceItem(
                    page_no=1,
                    bbox=box.to_bottom_left_origin(size.height),
                    charspan=(0, len(text)),
                ),
            )
        return _write_bundle(tmp_path, doc)

    placed = check_bundle(bundle("placed", lines), cropped).uncovered_text
    assert placed.issues == []
    assert placed.chars > 1000
    assert placed.uncovered_chars == 0
    assert placed.pages_checked == 1

    upper = [(text, box) for text, box in lines if box.b <= size.height / 2]
    lower = [(text, box) for text, box in lines if box.b > size.height / 2]
    lower_text = " ".join(text for text, _box in lower)
    union = BoundingBox.enclosing_bbox([box for _text, box in lower])
    too_high = union.model_copy(update={"t": union.t - 180, "b": union.b - 180})
    misplaced = check_bundle(
        bundle("misplaced", [*upper, (lower_text, too_high)]), cropped
    )

    flags = misplaced.uncovered_text.flagged_pages
    assert [flag.page for flag in flags] == [1]
    assert flags[0].uncovered_words >= 30
    assert all(piece in lower_text for piece in flags[0].sample.split())
    assert misplaced.page_recall.flagged_pages == []
    assert any(issue.startswith("uncovered_text: p1:") for issue in misplaced.issues)


def _table_with_pdf_text(doc: DoclingDocument) -> TableItem:
    table = doc.add_table(
        data=_grid([["Model", "AUC"], ["ECG-Agent", "0.91"]]), prov=_PROV
    )
    table.meta = FloatingMeta()
    table.meta.set_custom_field(
        "amir",
        "pdf_text",
        {"text": "Model AUC\nECG-Agent 0.91 Boldface best", "cell_text_recall": 0.5},
    )
    return table


def test_markdown_marks_descriptions_and_keeps_a_tables_pdf_text() -> None:
    doc = _paper()
    _table_with_pdf_text(doc)

    markdown = export_markdown(doc)

    assert f"{DESCRIPTION_OPEN}{_DESCRIPTION}{ANNOTATION_CLOSE}" in markdown
    assert (
        "Table text from the PDF (cell recall 0.50): "
        "Model AUC ECG-Agent 0.91 Boldface best"
    ) in markdown


def test_chunks_keep_a_tables_pdf_text_and_skip_text_less_chunks(
    tmp_path: Path,
) -> None:
    """A long captioned table is split to fit the token budget; the caption
    split off it serializes to nothing and is not written."""
    doc = DoclingDocument(name="paper")
    doc.add_page(page_no=1, size=Size(width=600, height=800))
    doc.add_heading(text="Results", prov=_PROV)
    small = _table_with_pdf_text(doc)
    doc.add_heading(text="Supplementary tables", prov=_PROV)
    long = doc.add_table(
        data=_grid([[f"value {r} {c}" for c in range(3)] for r in range(30)]),
        prov=_PROV,
    )
    caption = doc.add_text(
        label=DocItemLabel.CAPTION, text="Table S1 | Every value.", prov=_PROV
    )
    long.captions.append(caption.get_ref())

    paths = write_chunks(
        ConversionResult.model_construct(document=doc), tmp_path, max_tokens=64
    )
    rows = [json.loads(line) for line in paths.chunks_jsonl.read_text().splitlines()]

    assert rows and all(row["text"].strip() for row in rows)
    assert [row["index"] for row in rows] == list(range(paths.chunk_count))
    small_chunk = next(row for row in rows if row["self_refs"] == [small.self_ref])
    assert "Table text from the PDF (cell recall 0.50)" in small_chunk["text"]
    assert any(long.self_ref in row["self_refs"] for row in rows)
