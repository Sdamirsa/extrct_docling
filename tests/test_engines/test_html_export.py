# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for the standalone ``<stem>.html`` (:mod:`docling.engines.html_export`)."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    PictureMeta,
    ProvenanceItem,
    Size,
)

from docling.engines import PdfEngine
from docling.engines.figure_typing import FigureTypePrediction
from docling.engines.html_export import (
    MANIFEST_ID,
    rebuild_document_html,
    write_document_html,
)
from docling.engines.picture_filter import PictureNoiseFlag

FIXTURE_PDF = Path("tests/data/pdf/sources/2305.03393v1-pg9.pdf")


class _Elements(HTMLParser):
    """Collects every tagged block's attributes and the manifest JSON."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: dict[str, dict[str, str | None]] = {}
        self.tags: list[str] = []
        self._manifest: list[str] = []
        self._in_manifest = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        self.tags.append(tag)
        if (ref := attr.get("data-self-ref")) is not None:
            self.blocks[ref] = attr
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


@pytest.mark.skipif(
    not FIXTURE_PDF.exists(),
    reason=f"fixture {FIXTURE_PDF} not available",
)
def test_pdf_engine_writes_document_html(tmp_path: Path) -> None:
    """Every chunk can be traced to a page region in the standalone HTML, and
    an existing bundle regenerates to the same file."""
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

    chunk_refs = {ref for chunk in manifest["chunks"] for ref in chunk["self_refs"]}
    assert chunk_refs, "fixture produced no chunks"
    assert chunk_refs <= parsed.blocks.keys()
    for ref, attrs in parsed.blocks.items():
        pages, boxes = attrs["data-page"], attrs["data-bbox"]
        assert pages and boxes, ref
        assert len(boxes.split(";")) == len(pages.split())

    assert rebuild_document_html(pdf_dir).read_text(encoding="utf-8") == html_text


def test_document_html_drops_noise_and_survives_script_text(tmp_path: Path) -> None:
    """A noise picture loses its image but keeps its caption; the BiomedCLIP
    type is exposed as an attribute; paper text containing ``</script>``
    cannot truncate the manifest."""
    doc = DoclingDocument(name="paper")
    doc.add_page(page_no=1, size=Size(width=600, height=800))

    def prov(t: float) -> ProvenanceItem:  # PDF-style bottom-left origin, as parsed
        bbox = BoundingBox(
            l=50, t=t, r=550, b=t - 40, coord_origin=CoordOrigin.BOTTOMLEFT
        )
        return ProvenanceItem(page_no=1, bbox=bbox, charspan=(0, 0))

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
    logo = doc.add_picture(prov=prov(100))
    logo_caption = doc.add_text(label=DocItemLabel.CAPTION, text="Qwen", prov=prov(60))
    logo.captions.append(logo_caption.get_ref())

    pdf_dir = tmp_path / "paper"
    pdf_dir.mkdir()
    script_text = "x</script><script>alert(1)</script>"
    (pdf_dir / "chunks.jsonl").write_text(
        json.dumps({"index": 0, "text": script_text, "self_refs": [para.self_ref]})
        + "\n"
    )
    flags = [
        PictureNoiseFlag(ecg.self_ref, False, None, None),
        PictureNoiseFlag(logo.self_ref, True, "classifier:logo", "logo"),
    ]

    parsed = _parse(write_document_html(doc, pdf_dir, noise_flags=flags))

    assert parsed.manifest["chunks"][0]["text"] == script_text
    assert parsed.tags.count("script") == 1
    assert logo.self_ref not in parsed.blocks
    assert logo_caption.self_ref in parsed.blocks
    assert parsed.blocks[ecg.self_ref]["data-figure-type"] == "ecg"
    # Top-left origin: the paragraph sits 100 pt below the page top.
    assert parsed.blocks[para.self_ref]["data-bbox"] == "50.0,100.0,550.0,140.0"
