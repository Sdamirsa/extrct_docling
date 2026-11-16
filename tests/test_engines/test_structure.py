# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for the structure pass (:mod:`docling.engines.structure`)."""

from __future__ import annotations

import ctypes
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from docling_core.types.doc import (
    BoundingBox,
    ContentLayer,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
    TableData,
)

from docling.engines.structure import (
    RULE_CAPTION_PATTERN,
    RULE_REPEATED_TEXT,
    RULE_STANDARD_SECTION_NAME,
    RULE_TITLE,
    DocumentStructure,
    quality_report,
    read_structure,
    structure_document,
    write_structure,
)
from docling.engines.text_repair import GlyphStyle, pdf_text_styles

_PAGE = Size(width=612, height=792)
_SENTENCE = "The cohort included patients from three hospitals followed for years."


def _doc(pages: int = 1) -> DoclingDocument:
    doc = DoclingDocument(name="paper")
    for page_no in range(1, pages + 1):
        doc.add_page(page_no=page_no, size=_PAGE)
    return doc


def _prov(text: str, page: int, top: float, size: float = 10.0) -> ProvenanceItem:
    """One line of *text* set in *size* points, *top* points down the page."""
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


def _heading(
    doc: DoclingDocument, text: str, *, page: int = 1, top: float, size: float = 12.0
) -> str:
    return doc.add_heading(text=text, prov=_prov(text, page, top, size)).self_ref


def _text(
    doc: DoclingDocument, text: str = _SENTENCE, *, page: int = 1, top: float
) -> str:
    return doc.add_text(
        label=DocItemLabel.TEXT, text=text, prov=_prov(text, page, top)
    ).self_ref


def _outline(structure: DocumentStructure) -> list[tuple[int, str | None, str]]:
    return [(e.level, e.number, e.title) for e in structure.outline]


def test_line_repeated_in_the_margin_is_furniture_and_repeated_headings_stay() -> None:
    doc = _doc(pages=3)
    banners, results, examples = [], [], []
    for page in (1, 2, 3):
        banners.append(_heading(doc, "ARTICLE IN PRESS", page=page, top=20))
        # The same text on three pages, but in the page: a real heading.
        results.append(_heading(doc, "Results", page=page, top=300))
        _text(doc, page=page, top=330)
        # In the margin, but a different line on every page.
        examples.append(
            _heading(doc, f"SI.1.{page} Example of a conversation 3", page=page, top=60)
        )
        _text(doc, f"{page} Z. Arow et al.", page=page, top=760)

    structure = structure_document(doc)

    by_ref = {item.self_ref: item for item in doc.texts}
    for ref in banners:
        assert by_ref[ref].label == DocItemLabel.PAGE_HEADER
        assert by_ref[ref].content_layer == ContentLayer.FURNITURE
        info = structure.elements[ref]
        assert (info.role, info.label_was, info.label_source, info.repeat_count) == (
            "page-header",
            "section_header",
            RULE_REPEATED_TEXT,
            3,
        )
    assert [by_ref[ref].label for ref in results + examples] == [
        DocItemLabel.SECTION_HEADER
    ] * 6
    # A page number at the start does not make the running line another one.
    footers = [item for item in doc.texts if item.label == DocItemLabel.PAGE_FOOTER]
    assert [item.text for item in footers] == [
        "1 Z. Arow et al.",
        "2 Z. Arow et al.",
        "3 Z. Arow et al.",
    ]
    assert quality_report(doc).repeated_heading_texts[0].text == "results"


def test_levels_follow_numbering_and_lettered_appendices() -> None:
    doc = _doc(pages=2)
    title = _heading(
        doc, "Echo-CoPilot: An Agentic Framework for Echo", top=60, size=18
    )
    author = _text(doc, "A. Author", top=90)
    intro = _heading(doc, "1 Introduction", top=120)
    intro_text = _text(doc, top=140)
    _heading(doc, "2 Experiments", top=200)
    accuracy = _heading(doc, "2.1 Diagnostic Accuracy", top=230, size=10)
    accuracy_text = _text(doc, top=250)
    _heading(doc, "References", top=400)
    reference = _text(doc, "[1] A. Author. A paper. 2024.", top=420)
    _heading(doc, "A Implementation Details", page=2, top=60)
    prompts = _heading(doc, "A.1 Prompts", page=2, top=90, size=10)
    prompt_text = _text(doc, page=2, top=110)
    _heading(doc, "B Additional Results", page=2, top=200)
    # A count at the start of a line the layout model took for a heading.
    _heading(doc, "75 commonly asked questions", page=2, top=260, size=10)

    structure = structure_document(doc)

    assert _outline(structure) == [
        (1, "1", "Introduction"),
        (1, "2", "Experiments"),
        (2, "2.1", "Diagnostic Accuracy"),
        (1, None, "References"),
        (1, "A", "Implementation Details"),
        (2, "A.1", "Prompts"),
        (1, "B", "Additional Results"),
        (2, None, "75 commonly asked questions"),
    ]
    assert structure.title_ref == title
    assert doc.texts[0].label == DocItemLabel.TITLE
    assert structure.elements[title].label_source == RULE_TITLE
    sub = next(e for e in structure.outline if e.ref == accuracy)
    assert sub.path == ["Experiments", "Diagnostic Accuracy"]
    assert sub.parent == structure.outline[1].ref
    assert [e.zone for e in structure.outline] == [
        "body",
        "body",
        "body",
        "reference",
        "supplement",
        "supplement",
        "supplement",
        "supplement",
    ]
    roles = {ref: structure.elements[ref].role for ref in structure.elements}
    assert roles[author] == "front-matter"
    assert roles[intro_text] == "body"
    assert roles[reference] == "reference"
    assert roles[prompt_text] == "supplement"
    assert structure.elements[intro_text].section_ref == intro
    assert structure.elements[accuracy_text].section_ref == accuracy
    assert structure.elements[prompt_text].section_ref == prompts
    # The level reaches the document, so <h2>/<h3> and chunk headings follow.
    levels = {
        item.text: item.level for item in doc.texts if item.label == "section_header"
    }
    assert levels["2 Experiments"] == 1
    assert levels["2.1 Diagnostic Accuracy"] == 2


def test_headings_set_alike_nest_under_the_named_sections() -> None:
    doc = _doc()
    for top, text in enumerate(
        ["Methods", "Study Design", "Statistical Analysis", "Results", "Study cohort"]
    ):
        _heading(doc, text, top=100 + 60 * top)
        _text(doc, top=120 + 60 * top)

    structure = structure_document(doc)

    assert [(e.level, e.title, e.level_source) for e in structure.outline] == [
        (1, "Methods", "standard-name"),
        (2, "Study Design", "position"),
        (2, "Statistical Analysis", "position"),
        (1, "Results", "standard-name"),
        (2, "Study cohort", "position"),
    ]


def test_heading_set_like_the_sections_is_a_section_where_type_marks_levels() -> None:
    doc = _doc()
    rows = [
        ("Introduction", 12.0),
        ("Dataset", 12.0),
        ("Method", 12.0),
        ("Window Fusion", 10.0),
        ("Conclusion and Future Work", 12.0),
    ]
    for index, (text, size) in enumerate(rows):
        _heading(doc, text, top=100 + 60 * index, size=size)
        _text(doc, top=120 + 60 * index)

    structure = structure_document(doc)

    assert [(e.level, e.title) for e in structure.outline] == [
        (1, "Introduction"),
        (1, "Dataset"),
        (1, "Method"),
        (2, "Window Fusion"),
        (1, "Conclusion and Future Work"),
    ]
    assert structure.outline[1].level_source == "font-size"


def test_parts_of_a_structured_abstract_stay_in_the_abstract() -> None:
    doc = _doc()
    _heading(doc, "Abstract", top=100)
    _heading(doc, "Methods", top=130)
    abstract_methods = _text(doc, top=150)
    _heading(doc, "Results", top=190)
    _heading(doc, "Introduction", top=260)
    _heading(doc, "Methods", top=320)
    methods = _text(doc, top=340)
    _heading(doc, "Results", top=400)

    structure = structure_document(doc)

    assert [(e.level, e.title, e.zone) for e in structure.outline] == [
        (1, "Abstract", "abstract"),
        (2, "Methods", "abstract"),
        (2, "Results", "abstract"),
        (1, "Introduction", "body"),
        (1, "Methods", "body"),
        (1, "Results", "body"),
    ]
    assert structure.elements[abstract_methods].role == "abstract"
    assert structure.elements[methods].role == "body"


def test_caption_like_lines_become_captions_tied_to_their_table_or_figure() -> None:
    doc = _doc(pages=2)
    results = _heading(doc, "Results", top=60)
    citing = _text(doc, "Ratings are compared in Fig. 3 and Table S11.", top=90)
    table_heading = _heading(doc, "Table S11. Detailed results by reviewer", top=140)
    table = doc.add_table(
        data=TableData(num_rows=0, num_cols=0, table_cells=[]),
        prov=_prov("x" * 60, 1, 170, size=80),
    )
    picture = doc.add_picture(prov=_prov("x" * 60, 1, 300, size=150))
    figure_text = _text(doc, "Figure 3. Paired differences in overall quality", top=460)
    sentence = _text(doc, "Figure 3 shows that the ratings agree.", top=500)
    algorithm = _heading(doc, "Algorithm 1 Proposed framework", page=2, top=60)

    structure = structure_document(doc)

    by_ref = {item.self_ref: item for item in doc.texts}
    assert by_ref[table_heading].label == DocItemLabel.CAPTION
    assert by_ref[figure_text].label == DocItemLabel.CAPTION
    assert by_ref[algorithm].label == DocItemLabel.CAPTION
    assert by_ref[sentence].label == DocItemLabel.TEXT
    assert [ref.cref for ref in table.captions] == [table_heading]
    assert [ref.cref for ref in picture.captions] == [figure_text]
    assert by_ref[figure_text].parent.cref == picture.self_ref

    elements = structure.elements
    assert (elements[table.self_ref].role, elements[table.self_ref].number) == (
        "table",
        "Table S11",
    )
    assert elements[table.self_ref].caption_ref == table_heading
    assert elements[table_heading].caption_for == table.self_ref
    assert elements[table_heading].role == "table-caption"
    assert elements[table_heading].label_source == RULE_CAPTION_PATTERN
    assert elements[picture.self_ref].number == "Figure 3"
    assert elements[picture.self_ref].first_mention_ref == citing
    assert elements[picture.self_ref].first_mention_section_ref == results
    assert elements[algorithm].role == "algorithm-caption"
    assert [e.title for e in structure.outline] == ["Results"]
    # Same refs as before the pass: locators made on the labels still resolve.
    assert [item.self_ref for item in doc.texts] == [
        f"#/texts/{index}" for index in range(len(doc.texts))
    ]


def test_title_is_the_long_heading_in_large_type_not_the_journal_name() -> None:
    doc = _doc()
    _heading(doc, "European Journal of Radiology", top=40, size=22)
    title = _heading(
        doc,
        "Reproducibility of rapid strain assessment in cardiac MRI",
        top=90,
        size=20,
    )
    _heading(doc, "1. Introduction", top=200)
    _heading(doc, "A subsection with several words in it", top=260, size=11)

    structure = structure_document(doc)

    assert structure.title_ref == title


def test_standard_section_name_left_as_a_paragraph_becomes_a_heading() -> None:
    doc = _doc()
    _heading(doc, "Introduction", top=60)
    _text(doc, top=80)
    missed = _text(doc, "Methods", top=140)
    _text(doc, top=160)
    run_in = _text(doc, "Funding:", top=300)

    structure = structure_document(doc)

    by_ref = {item.self_ref: item for item in doc.texts}
    assert by_ref[missed].label == DocItemLabel.SECTION_HEADER
    assert structure.elements[missed].label_source == RULE_STANDARD_SECTION_NAME
    assert by_ref[run_in].label == DocItemLabel.TEXT
    assert [e.title for e in structure.outline] == ["Introduction", "Methods"]


def test_text_packed_into_a_few_blocks_is_a_blocking_warning() -> None:
    packed = _doc(pages=20)
    for page in (1, 10, 11, 17, 18):
        _text(packed, _SENTENCE * 60, page=page, top=60)
    for page in range(1, 21):
        packed.add_text(
            label=DocItemLabel.PAGE_HEADER,
            text=str(page),
            prov=_prov(str(page), page, 20),
            content_layer=ContentLayer.FURNITURE,
        )

    report = quality_report(packed)

    assert [(w.code, w.blocking) for w in report.warnings] == [
        ("few_text_blocks", True),
        ("no_headings", False),
        ("pages_without_content", False),
    ]
    assert report.label_counts == {"page_header": 20, "text": 5}
    assert report.pages_without_text == [
        page for page in range(1, 21) if page not in (1, 10, 11, 17, 18)
    ]

    scan = _doc(pages=2)
    assert [(w.code, w.blocking) for w in quality_report(scan).blocking] == [
        ("no_body_text", True)
    ]

    paper = _doc(pages=2)
    _heading(paper, "Introduction", top=60)
    for page in (1, 2):
        _text(paper, page=page, top=100)
    assert quality_report(paper).warnings == []


def test_structure_json_round_trips(tmp_path: Path) -> None:
    doc = _doc()
    _heading(doc, "1 Introduction", top=60)
    _text(doc, top=80)
    structure = structure_document(doc, document_role="supplement")

    write_structure(tmp_path, structure)

    assert read_structure(tmp_path) == structure
    assert read_structure(tmp_path / "missing") is None


def _draw(
    pdf: pdfium.PdfDocument,
    page: pdfium.PdfPage,
    text: str,
    *,
    font: bytes,
    size: float,
    y: float,
) -> ProvenanceItem:
    obj = pdfium_c.FPDFPageObj_NewTextObj(pdf.raw, font, ctypes.c_float(size))
    wide = (ctypes.c_ushort * (len(text) + 1))(*map(ord, text), 0)
    pdfium_c.FPDFText_SetText(obj, wide)
    pdfium_c.FPDFPageObj_Transform(obj, 1, 0, 0, 1, 72, y)
    pdfium_c.FPDFPage_InsertObject(page.raw, obj)
    return ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(
            l=70, t=y + size, r=400, b=y - 3, coord_origin=CoordOrigin.BOTTOMLEFT
        ),
        charspan=(0, len(text)),
    )


def test_heading_type_is_read_from_the_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "styles.pdf"
    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(612, 792)
    regions = {
        "section": _draw(pdf, page, "Methods", font=b"Helvetica-Bold", size=12, y=700),
        "subsection": _draw(
            pdf, page, "Study design", font=b"Helvetica-Bold", size=12, y=650
        ),
        "minor": _draw(
            pdf, page, "Blinding", font=b"Helvetica-Oblique", size=10, y=600
        ),
        "empty": ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(
                l=70, t=300, r=400, b=280, coord_origin=CoordOrigin.BOTTOMLEFT
            ),
            charspan=(0, 0),
        ),
    }
    page.gen_content()
    pdf.save(pdf_path)
    pdf.close()

    styles = pdf_text_styles(pdf_path, regions)

    assert styles == {
        "section": GlyphStyle(size=12.0, bold=True, upright=True),
        "subsection": GlyphStyle(size=12.0, bold=True, upright=True),
        "minor": GlyphStyle(size=10.0, bold=False, upright=False),
    }
    assert styles["minor"] < styles["section"]
