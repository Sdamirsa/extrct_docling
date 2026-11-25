# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The temporary repairs of docling-parse 7.20's faults
(:mod:`docling.utils.parser_repair`): words of tightly set text run
together, letters read as look-alikes; and the check that names both
whether or not they were repaired.

``test_docling_parse_runs_the_words_of_tight_text_together`` states the
fault itself: when it fails after a parser upgrade, the parser no longer has
it, and the repair is to be measured for removal (see the module).
"""

from __future__ import annotations

from pathlib import Path

from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)
from docling_parse.pdf_parser import DoclingPdfParser

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.engines import PdfEngine
from docling.engines.export_check import _check_text_quality
from docling.utils.parser_repair import (
    Respacer,
    letters_from_pdfium,
    needs_respacing,
    respacing_holds,
    spacing,
)

_LINES = [
    "studies and small randomized clinical trials suggest that",
    "conduction system pacing can improve electrical synchrony",
    "as well as ventricular function in patients with heart failure",
    "nevertheless these studies have been limited by low numbers",
    "high crossover rates and heterogeneous implant experience",
]
# Thousandths of an em between words, no space character. docling-parse 7.20
# joins words up to 125 apart with its default spacing and separates them
# from 100 with the repair's (measured on this page, 2026-11-25).
_TIGHT_GAP = 110


def _tight_pdf() -> bytes:
    """A page of justified-looking lines whose words are placed apart by a
    small shift and hold no space character, as JAMA sets its text; a last
    line with ordinary spaces."""
    shown = [
        "[" + f" -{_TIGHT_GAP} ".join(f"({word})" for word in line.split()) + "] TJ"
        for line in _LINES
    ]
    stream = (
        "BT /F 10 Tf 14 TL 72 720 Td\n"
        + "\nT*\n".join(shown)
        + "\nT*\n(An ordinary line with spaces in it.) Tj\nET"
    ).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


def _line_texts(pdf: Path) -> list[str]:
    document = DoclingPdfParser().load(path_or_stream=pdf)
    try:
        return [cell.text for cell in document.get_page(1).textline_cells]
    finally:
        document.unload()


def test_docling_parse_runs_the_words_of_tight_text_together(tmp_path: Path) -> None:
    pdf = tmp_path / "tight.pdf"
    pdf.write_bytes(_tight_pdf())

    found = spacing(_line_texts(pdf))

    assert needs_respacing(found), _line_texts(pdf)


def test_decoded_again_the_words_are_apart_and_the_page_kept(tmp_path: Path) -> None:
    pdf = tmp_path / "tight.pdf"
    pdf.write_bytes(_tight_pdf())
    respacer = Respacer(pdf)
    try:
        again = [cell.text for cell in respacer.page(1).textline_cells]
    finally:
        respacer.close()

    assert respacing_holds(spacing(_line_texts(pdf)), spacing(again))
    joined = " ".join(again)
    for line in _LINES:
        assert line in joined


def test_a_new_decode_that_splits_words_or_changes_characters_is_refused() -> None:
    fused = spacing(["studiesandsmallrandomizedclinicaltrials " * 4])
    assert needs_respacing(fused)
    split = spacing(["studies and s m a l l randomized clinical trials " * 4])
    other = spacing(["studies and small randomized trials " * 4])

    assert not respacing_holds(fused, split)
    assert not respacing_holds(fused, other)
    assert not needs_respacing(spacing(["an ordinary electrocardiographically"]))


def test_a_letter_read_as_a_look_alike_takes_pdfiums_by_place() -> None:
    # "Reporting Summary" as docling-parse 7.20 reads a Calibri subset.
    misread = "Repo\u018cti\u0176g Su\u0175\u0175a\u018c\u01c7"

    assert letters_from_pdfium(misread, "Reporting Summary") == (
        "Reporting Summary",
        6,
    )
    # A real letter of the block reads the same in both and stays; a hyphen
    # pdfium marks at a line end pairs with the parser's.
    assert letters_from_pdfium(
        "\u0141\u00f3d\u017a pro-", "\u0141\u00f3d\u017a pro\ufffe"
    ) == (
        "\u0141\u00f3d\u017a pro-",
        0,
    )
    # Digits and brackets of the same font, with a bullet and the next line
    # in pdfium's box: the alignment pairs the rest one to one.
    criteria = "documented by \u015b\u0142\u015c a note for \u0142\u0143 months"
    assert letters_from_pdfium(
        criteria, "documented by \u2002 \u2022 (1) a note for 12 months; AND"
    ) == ("documented by (1) a note for 12 months", 5)
    # Nothing to pair it with: left alone.
    assert letters_from_pdfium(misread, "") == (misread, 0)


def test_the_check_names_pages_with_run_together_words_or_look_alikes() -> None:
    """Only what the PDF's own text of the page does not hold: a long word
    printed as one and the letters of Czech names are not faults."""
    long_words = "electrophysiological " * 3
    names = (
        "Neu\u017eil Kautzner \u0160t\u011bp\u00e1n \u010cih\u00e1k \u0158\u00edha " * 3
    )
    # "2.6 in subjects age" in a font whose codes are its glyph numbers: both
    # readers give the same.
    unmapped = (
        "\u03ee\u0358\u03f2 \u015d\u0176 \u0190\u01b5\u010f\u0169\u011e\u0110\u019a\u0190 "
        * 2
    )
    texts = {
        1: "studiesandsmallrandomizedclinicaltrials " * 3,
        2: "Repo\u018cti\u0176g Su\u0175\u0175a\u018c\u01c7 " * 2,
        3: "An ordinary page.",
        4: long_words + names,
        5: unmapped,
    }
    printed = [
        "studies and small randomized clinical trials " * 3,
        "Reporting Summary " * 2,
        "An ordinary page.",
        long_words + names,
        unmapped,
    ]
    doc = DoclingDocument(name="x")
    for page_no, text in texts.items():
        doc.add_page(page_no=page_no, size=Size(width=612, height=792))
        doc.add_text(
            label=DocItemLabel.TEXT,
            text=text,
            prov=ProvenanceItem(
                page_no=page_no,
                bbox=BoundingBox(l=0, t=0, r=10, b=10),
                charspan=(0, len(text)),
            ),
        )

    found = _check_text_quality(doc, printed)

    assert found.fused_pages == [1]
    assert found.lookalike_pages == [2]
    assert found.unmapped_pages == [5]
    assert len(found.issues) == 3
    # Without the PDF, every such page is named.
    assert _check_text_quality(doc, None).fused_pages == [1, 4]


def test_a_conversion_respaces_the_page_and_records_it(tmp_path: Path) -> None:
    pdf = tmp_path / "tight.pdf"
    pdf.write_bytes(_tight_pdf())
    engine = PdfEngine(
        picture_description=None, granite_vision_tables=False, figure_types=False
    )

    output = engine.convert(pdf, output_dir=tmp_path / "out")

    assert output.succeeded, output.errors
    assert output.markdown is not None
    for line in _LINES:
        assert line in " ".join(output.markdown.split())
    assert output.quality is not None and output.quality.parser_repair is not None
    assert output.quality.parser_repair.respaced_pages == [1]
    assert "parser_text_repaired" in {w.code for w in output.quality.warnings}
    assert output.check is not None and not output.check.text_quality.issues


def test_without_the_repair_the_check_names_the_page(tmp_path: Path) -> None:
    pdf = tmp_path / "tight.pdf"
    pdf.write_bytes(_tight_pdf())
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=PdfPipelineOptions(repair_parser_text=False)
            )
        }
    )

    output = PdfEngine(converter=converter).convert(pdf, output_dir=tmp_path / "out")

    assert output.succeeded, output.errors
    assert output.quality is not None and output.quality.parser_repair is None
    assert output.markdown is not None
    assert "studiesandsmallrandomizedclinicaltrials" in output.markdown
    # pdfium runs the words of this page together too, so the check, which
    # takes a run the PDF's own text holds for printed so, names it only
    # without the PDF (real JAMA pages: pdfium has the spaces).
    doc = DoclingDocument.load_from_json(tmp_path / "out" / "tight" / "document.json")
    assert _check_text_quality(doc, None).fused_pages == [1]
