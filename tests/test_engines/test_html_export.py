# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for the standalone ``<stem>.html`` (:mod:`docling.engines.html_export`)."""

from __future__ import annotations

import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from docling_core.types.doc import (
    BoundingBox,
    ContentLayer,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    PictureMeta,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
)
from docling_core.types.doc.document import FloatingMeta

from docling.engines import ENGINE_VERSION, PdfEngine
from docling.engines.figure_typing import FigureTypePrediction
from docling.engines.html_export import (
    MANIFEST_ID,
    rebuild_document_html,
    write_document_html,
)
from docling.engines.picture_filter import PictureNoiseFlag
from docling.engines.structure import structure_document, write_structure

FIXTURE_PDF = Path("tests/data/pdf/sources/2305.03393v1-pg9.pdf")


class _Elements(HTMLParser):
    """Collects every tagged block's attributes and the manifest JSON."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: dict[str, dict[str, str | None]] = {}
        self.ref_counts: Counter[str] = Counter()
        self.tags: list[str] = []
        self._manifest: list[str] = []
        self._in_manifest = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        self.tags.append(tag)
        if (ref := attr.get("data-self-ref")) is not None:
            self.blocks[ref] = attr
            self.ref_counts[ref] += 1
        self._in_manifest = tag == "script" and attr.get("id") == MANIFEST_ID

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_manifest = False

    def handle_data(self, data: str) -> None:
        if self._in_manifest:
            self._manifest.append(data)

    @property
    def manifest(self) -> dict:
        return json.loads("".join(self._manifest))


def _parse(path: Path) -> _Elements:
    parser = _Elements()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _all_item_refs(doc: DoclingDocument) -> set[str]:
    return {
        item.self_ref
        for item, _level in doc.iterate_items(
            with_groups=False,
            traverse_pictures=True,
            included_content_layers=set(ContentLayer),
        )
    }


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_document_html(tmp_path: Path) -> None:
    """Every item Docling extracted — page furniture and text inside figures
    included — is one tagged element of the standalone HTML, every chunk can
    be traced to it, and an existing bundle regenerates to the same file but
    for the final run block."""
    engine = PdfEngine(
        images_scale=1.0,
        picture_description=None,
        granite_vision_tables=False,
        figure_types=False,
    )
    output = engine.convert(FIXTURE_PDF, output_dir=tmp_path)
    assert output.succeeded, f"conversion failed: {output.errors}"
    pdf_dir = tmp_path / FIXTURE_PDF.stem
    html_path, tables_jsonl = output.html_path, output.tables_jsonl
    assert html_path is not None and tables_jsonl is not None
    assert html_path == pdf_dir / f"{FIXTURE_PDF.stem}.html"

    html_text = html_path.read_text(encoding="utf-8")
    assert 'src="images/' not in html_text  # standalone: images are inlined
    parsed = _parse(html_path)
    manifest = parsed.manifest
    assert manifest["run"]["source"]["file_name"] == FIXTURE_PDF.name
    assert len(manifest["tables"]) == len(tables_jsonl.read_text().splitlines())

    doc = DoclingDocument.load_from_json(pdf_dir / "document.json")
    assert _all_item_refs(doc) <= parsed.blocks.keys()
    assert max(parsed.ref_counts.values()) == 1

    chunk_refs = {ref for chunk in manifest["chunks"] for ref in chunk["self_refs"]}
    assert chunk_refs, "fixture produced no chunks"
    assert chunk_refs <= parsed.blocks.keys()
    for ref, attrs in parsed.blocks.items():
        pages, boxes = attrs["data-page"], attrs["data-bbox"]
        assert pages and boxes, ref
        assert len(boxes.split(";")) == len(pages.split())

    # The conversion embeds the run block written before the check, which
    # says the run is not complete; a rebuild embeds the final run.json.
    assert manifest["run"]["complete"] is False
    assert rebuild_document_html(pdf_dir).read_text(encoding="utf-8") == (
        html_text.replace('"complete": false', '"complete": true', 1)
    )


def test_document_html_keeps_everything_docling_extracted(tmp_path: Path) -> None:
    """The parts Docling's HTML serializer leaves out are in the file, marked:
    a logo (noise, with its caption), a page header, text inside a figure, a
    table footnote, a reference number, a formula's PDF characters. Paper text
    containing ``</script>`` cannot truncate the manifest."""
    doc = DoclingDocument(name="paper")
    doc.add_page(page_no=1, size=Size(width=600, height=800))

    def prov(t: float) -> ProvenanceItem:  # PDF-style bottom-left origin, as parsed
        bbox = BoundingBox(
            l=50, t=t, r=550, b=t - 40, coord_origin=CoordOrigin.BOTTOMLEFT
        )
        return ProvenanceItem(page_no=1, bbox=bbox, charspan=(0, 0))

    header = doc.add_text(
        label=DocItemLabel.PAGE_HEADER,
        text="J Cardiol (2026) 21:1293",
        prov=prov(790),
        content_layer=ContentLayer.FURNITURE,
    )
    para = doc.add_text(
        label=DocItemLabel.TEXT, text="ST elevation in V1-V3.", prov=prov(700)
    )
    ecg = doc.add_picture(prov=prov(600))
    ecg.meta = PictureMeta()
    ecg.meta.set_custom_field(
        "amir",
        "figure_type",
        FigureTypePrediction(label="ecg", confidence=0.91).model_dump(),
    )
    lead_label = doc.add_text(
        label=DocItemLabel.TEXT, text="Lead V2", prov=prov(590), parent=ecg
    )
    logo = doc.add_picture(prov=prov(100))
    logo_caption = doc.add_text(label=DocItemLabel.CAPTION, text="Qwen", prov=prov(60))
    logo.captions.append(logo_caption.get_ref())

    table = doc.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="0.91",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                )
            ],
        ),
        prov=prov(500),
    )
    footnote = doc.add_text(
        label=DocItemLabel.FOOTNOTE,
        text="Boldface = best performance.",
        prov=prov(450),
        parent=table,
    )
    table.footnotes.append(footnote.get_ref())
    table.meta = FloatingMeta()  # the table model's cells missed words
    table.meta.set_custom_field(
        "amir", "pdf_text", {"text": "0.91 Boldface best", "cell_text_recall": 0.5}
    )

    prompt = doc.add_code(text="You are a medical expert.", prov=prov(350))
    prompt_caption = doc.add_text(
        label=DocItemLabel.CAPTION,
        text="Table SI.3 | Agent prompt",
        prov=prov(340),
        parent=prompt,
    )
    prompt.captions.append(
        prompt_caption.get_ref()
    )  # dropped by Docling's HTML code serializer
    formula = doc.add_formula(text="", orig="sim ( w a t , p i )", prov=prov(400))
    references = doc.add_list_group()
    reference = doc.add_list_item(
        text="T. Han et al., Automatic stent struts detection.",
        marker="[3]",
        enumerated=True,
        parent=references,
        prov=prov(300),
    )

    pdf_dir = tmp_path / "paper"
    pdf_dir.mkdir()
    script_text = "x</script><script>alert(1)</script>"
    chunks_jsonl = pdf_dir / "chunks.jsonl"
    chunks_jsonl.write_text(
        json.dumps({"index": 0, "text": script_text, "self_refs": [para.self_ref]})
        + "\n"
    )
    flags = [
        PictureNoiseFlag(ecg.self_ref, False, None, None),
        PictureNoiseFlag(logo.self_ref, True, "classifier:logo", "logo"),
    ]

    html_path = write_document_html(
        doc, pdf_dir, noise_flags=flags, chunks_jsonl=chunks_jsonl
    )
    parsed = _parse(html_path)
    html_text = html_path.read_text(encoding="utf-8")

    assert _all_item_refs(doc) <= parsed.blocks.keys()
    assert max(parsed.ref_counts.values()) == 1
    assert parsed.manifest["chunks"][0]["text"] == script_text
    assert parsed.tags.count("script") == 1
    assert parsed.manifest["html_written_by"]["version"] == ENGINE_VERSION

    assert parsed.blocks[logo.self_ref]["data-noise"] == "classifier:logo"
    assert logo_caption.self_ref in parsed.blocks
    assert parsed.blocks[header.self_ref]["data-content-layer"] == "furniture"
    assert parsed.blocks[ecg.self_ref]["data-figure-type"] == "ecg"
    figure_text = re.search(
        r'<details class="extrct-figure-text">.*?</details>', html_text, re.S
    )
    assert figure_text is not None and lead_label.self_ref in figure_text.group()
    assert footnote.self_ref in parsed.blocks
    assert parsed.blocks[table.self_ref]["data-cell-text-recall"] == "0.500"
    assert re.search(
        r'extrct-table-pdf-text">.*?<pre>0\.91 Boldface best</pre>', html_text
    )
    assert 'data-meta-name="amir__pdf_text"' not in html_text
    assert re.search(r'class="extrct-formula-text">sim \( w a t , p i \)<', html_text)
    assert parsed.blocks[formula.self_ref]["data-label"] == "formula"
    assert parsed.blocks[reference.self_ref]["data-marker"] == "[3]"
    assert '<span class="extrct-marker">[3]</span> T. Han' in html_text
    # Top-left origin: the paragraph sits 100 pt below the page top.
    assert parsed.blocks[para.self_ref]["data-bbox"] == "50.0,100.0,550.0,140.0"


def test_manifest_holds_only_this_runs_sidecars(tmp_path: Path) -> None:
    """A conversion that writes no ``tables.jsonl`` (no tables) or whose
    chunker failed must not embed the files an earlier run left in the
    folder; regenerating an existing bundle reads what is on disk."""
    doc = DoclingDocument(name="paper")
    doc.add_page(page_no=1, size=Size(width=600, height=800))
    doc.add_text(
        label=DocItemLabel.TEXT,
        text="No tables here.",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(
                l=50, t=700, r=550, b=660, coord_origin=CoordOrigin.BOTTOMLEFT
            ),
            charspan=(0, 15),
        ),
    )
    pdf_dir = tmp_path / "paper"
    pdf_dir.mkdir()
    doc.save_as_json(pdf_dir / "document.json")
    stale = {"self_ref": "#/tables/0", "caption_text": "from an earlier run"}
    for name in ("tables.jsonl", "chunks.jsonl"):
        (pdf_dir / name).write_text(json.dumps(stale) + "\n", encoding="utf-8")
    run = {"status": "ConversionStatus.SUCCESS", "complete": True}

    manifest = _parse(write_document_html(doc, pdf_dir, run=run)).manifest
    assert manifest["tables"] == manifest["chunks"] == manifest["figures"] == []
    assert manifest["run"] == run

    rebuilt = _parse(rebuild_document_html(pdf_dir)).manifest
    assert [row["caption_text"] for row in rebuilt["tables"]] == ["from an earlier run"]


def _line(text: str, page: int, top: float, size: float = 10.0) -> ProvenanceItem:
    return ProvenanceItem(
        page_no=page,
        bbox=BoundingBox(
            l=72,
            t=top,
            r=72 + 0.5 * size * len(text),
            b=top + size,
            coord_origin=CoordOrigin.TOPLEFT,
        ),
        charspan=(0, len(text)),
    )


def test_document_html_says_where_each_block_sits(tmp_path: Path) -> None:
    """The title is ``<h1>``, section headers ``<h2>``/``<h3>`` by level, and
    every block carries its role, its section and its links; a bundle without
    ``structure.json`` gets them when its HTML is rebuilt."""
    doc = DoclingDocument(name="paper")
    for page_no in (1, 2, 3):
        doc.add_page(page_no=page_no, size=Size(width=612, height=792))

    def heading(text: str, page: int, top: float, size: float = 12.0) -> str:
        return doc.add_heading(text=text, prov=_line(text, page, top, size)).self_ref

    def text(text: str, page: int, top: float, **kwargs: Any) -> str:
        return doc.add_text(
            label=DocItemLabel.TEXT, text=text, prov=_line(text, page, top), **kwargs
        ).self_ref

    # In reading order.
    banners = [heading("ARTICLE IN PRESS", 1, 20, 10)]
    title = heading("A study of structure in converted papers", 1, 60, 18)
    methods = heading("1 Methods", 1, 120)
    design = heading("1.1 Study design", 1, 180, 11)
    paragraph = text("Outcomes are listed in Table 2.", 1, 200)
    watermark = text(
        "Preprint not peer reviewed", 1, 300, content_layer=ContentLayer.BACKGROUND
    )
    banners.append(heading("ARTICLE IN PRESS", 2, 20, 10))
    table_caption = text("Table 2. Outcomes by group", 2, 60)
    table = doc.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="42",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                )
            ],
        ),
        prov=_line("x" * 40, 2, 90, size=60),
    ).self_ref
    heading("References", 2, 400)
    banners.append(heading("ARTICLE IN PRESS", 3, 20, 10))

    pdf_dir = tmp_path / "paper"
    pdf_dir.mkdir()
    doc.save_as_json(pdf_dir / "document.json")
    # An earlier release's bundle: no structure.json.
    parsed = _parse(rebuild_document_html(pdf_dir))

    def tag_of(ref: str) -> str:
        html = (pdf_dir / "paper.html").read_text(encoding="utf-8")
        match = re.search(rf'<([a-z0-9]+) [^>]*data-self-ref="{re.escape(ref)}"', html)
        assert match is not None
        return match.group(1)

    blocks = parsed.blocks
    assert (tag_of(title), blocks[title]["data-role"]) == ("h1", "title")
    assert (tag_of(methods), blocks[methods]["data-level"]) == ("h2", "1")
    assert tag_of(design) == "h3"
    assert blocks[design]["data-number"] == "1.1"
    assert blocks[design]["data-parent-ref"] == methods
    assert blocks[design]["data-level-source"] == "numbering"
    assert blocks[paragraph]["data-role"] == "body"
    assert blocks[paragraph]["data-section-ref"] == design
    assert blocks[table]["data-number"] == "Table 2"
    assert blocks[table]["data-caption-ref"] == table_caption
    assert blocks[table]["data-first-mention-ref"] == paragraph
    assert blocks[table]["data-first-mention-section-ref"] == design
    assert blocks[table_caption]["data-for"] == table
    assert blocks[table_caption]["data-role"] == "table-caption"
    assert blocks[table_caption]["data-label-was"] == "text"
    for ref in banners:
        assert blocks[ref]["data-label"] == "page_header"
        assert blocks[ref]["data-content-layer"] == "furniture"
        assert blocks[ref]["data-label-source"] == "rule:repeated-text"
        assert blocks[ref]["data-repeat-count"] == "3"
    assert blocks[watermark]["data-role"] == "watermark"
    assert set(parsed.ref_counts.values()) == {1}

    outline = parsed.manifest["structure"]["outline"]
    assert [(entry["level"], entry["title"]) for entry in outline] == [
        (1, "Methods"),
        (2, "Study design"),
        (1, "References"),
    ]
    assert parsed.manifest["document"]["title"] == (
        "A study of structure in converted papers"
    )
    assert parsed.manifest["tables"] == []

    # A bundle that has structure.json is rebuilt from it, not recomputed.
    structured = DoclingDocument.load_from_json(pdf_dir / "document.json")
    structure = structure_document(structured, document_role="supplement")
    structured.save_as_json(pdf_dir / "document.json")
    write_structure(pdf_dir, structure)
    rebuilt = _parse(rebuild_document_html(pdf_dir))
    assert rebuilt.manifest["structure"]["document_role"] == "supplement"
    assert rebuilt.blocks[paragraph]["data-document-role"] == "supplement"
    assert rebuilt.blocks[banners[0]]["data-label-was"] == "section_header"
