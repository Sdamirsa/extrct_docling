# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A PDF whose text layer does not say what its pages print
(:mod:`docling.utils.text_layer`): fonts read by glyph number are decoded,
unreadable pages go to OCR, and the bundle says which pages were which."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docling.engines import PdfEngine
from docling.engines.text_repair import pdf_page_texts
from docling.utils.text_layer import (
    FontReading,
    proves_glyph_order,
    read_document,
    read_font,
    summary,
)

_PRINTED = [
    "Sample size: 3000 patients were included in 12 centres.",
    "The primary endpoint was death at 30 days (95% CI 1.2 to 3.4).",
]
_ORDINARY = "An ordinary page with ordinary words on it, and a number: 42."
# What a font whose codes were handed out as its characters came leaves in
# the text layer (a shell table of a statistical analysis plan).
_UNMAPPED = [
    '!"#$%F\'()*+,-./0$-$1*2 3F4-+%567 3F4-+%567 3F4-+%567 !"#$%FG%($)*+HF-',
    "!\"#$%F'()*+,-./0$-$1*2 3F4-+%567 8F-3HF49 :-;-F<- =1F3$)41$%L41*+HF-%5?",
]


def _as_glyph_numbers(text: str) -> str:
    """What the text layer holds for *text* set in a font of the standard
    glyph order that has no Unicode map."""
    return "".join(chr(ord(char) - 29) for char in text)


def _pdf(pages: list[list[tuple[str, str]]]) -> bytes:
    """A PDF whose pages hold lines of (font, text). Font ``glyph``: a
    composite font without a Unicode map, shown by glyph number, as the PDFs
    this was found on have it. Font ``plain``: Helvetica."""
    objects: list[bytes] = []

    def add(body: str | bytes) -> int:
        objects.append(body.encode("latin-1") if isinstance(body, str) else body)
        return len(objects)

    catalog, pages_object = add(""), add("")
    plain = add(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        "/Encoding /WinAnsiEncoding >>"
    )
    descriptor = add(
        "<< /Type /FontDescriptor /FontName /ArialMT /Flags 4 "
        "/FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 900 /Descent -200 "
        "/CapHeight 700 /StemV 80 >>"
    )
    descendant = add(
        "<< /Type /Font /Subtype /CIDFontType2 /BaseFont /ArialMT "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
        f"/FontDescriptor {descriptor} 0 R /DW 550 /CIDToGIDMap /Identity >>"
    )
    glyph = add(
        "<< /Type /Font /Subtype /Type0 /BaseFont /ArialMT /Encoding /Identity-H "
        f"/DescendantFonts [{descendant} 0 R] >>"
    )
    kids: list[int] = []
    for lines in pages:
        parts = ["BT"]
        for row, (font, text) in enumerate(lines):
            y = 720 - 18 * row
            if font == "glyph":
                shown = "".join(f"{ord(char) - 29:04X}" for char in text)
                parts.append(f"/G 11 Tf 1 0 0 1 60 {y} Tm <{shown}> Tj")
            else:
                escaped = (
                    text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                )
                parts.append(f"/P 11 Tf 1 0 0 1 60 {y} Tm ({escaped}) Tj")
        parts.append("ET")
        stream = "\n".join(parts).encode("latin-1")
        content = add(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )
        kids.append(
            add(
                f"<< /Type /Page /Parent {pages_object} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /P {plain} 0 R /G {glyph} 0 R >> >> "
                f"/Contents {content} 0 R >>"
            )
        )
    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_object} 0 R >>".encode()
    objects[pages_object - 1] = (
        f"<< /Type /Pages /Count {len(kids)} "
        f"/Kids [{' '.join(f'{kid} 0 R' for kid in kids)}] >>"
    ).encode()
    out = bytearray(b"%PDF-1.7\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog,
        xref,
    )
    return bytes(out)


def _three_pages() -> bytes:
    return _pdf(
        [
            [("plain", "A trial of two treatments"), *(("glyph", t) for t in _PRINTED)],
            [("plain", _ORDINARY)],
            [("plain", "Table 3"), *(("plain", t) for t in _UNMAPPED)],
        ]
    )


def test_a_font_read_by_glyph_number_is_decoded_and_the_rest_left_as_it_is() -> None:
    layers = read_document(BytesIO(_three_pages()))

    found = summary(layers)
    assert found.glyph_order_pages == [1]
    assert found.unreadable_pages == [3]
    # The ordinary page is not touched, and neither is the ordinary line
    # that shares a page with the decoded ones.
    assert 2 not in layers
    assert layers[1].text().splitlines() == ["A trial of two treatments", *_PRINTED]
    assert layers[3].unmapped_share > 0.9


def test_glyph_order_is_only_assumed_for_a_small_font_once_the_document_proves_it() -> (
    None
):
    heading = _as_glyph_numbers("6.2.5 Follow-up")
    assert not proves_glyph_order(heading)
    assert proves_glyph_order(_as_glyph_numbers(_PRINTED[0]))
    assert read_font(heading, glyph_order_proven=True) == (
        FontReading.GLYPH_ORDER,
        len(heading),
    )
    # Alone, the same characters are a font nobody can read, not a decoded one.
    assert read_font(heading, glyph_order_proven=False)[0] is FontReading.UNMAPPED
    # A symbol font with a few control codes never decodes to words.
    assert (
        read_font("\x06\x07\x06\x1f\x06", glyph_order_proven=True)[0]
        is FontReading.UNMAPPED
    )


def test_fonts_that_only_look_odd_stay_readable() -> None:
    for ordinary in (
        "12.5* (3.4) <0.001# 45/120 (37.5%) 0.82 [0.61, 1.10] +/- 2.1 & 3",
        "STUDY OBJECTIVES AND ENDPOINTS OF THE TRIAL",
        "{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}",
        "Procedure" + "." * 60 + "17 Statistics" + "_" * 40,
        "(siehe „CLOSURE_tracked“) (siehe „CLOSURE“) […] […] […]",
    ):
        assert read_font(ordinary, glyph_order_proven=True) == (
            FontReading.READABLE,
            0,
        ), ordinary


def test_a_readable_font_with_some_unmapped_glyphs_loses_only_those() -> None:
    answers = (
        "Last updated by author(s): \x04\x05\x06\x07\x06\x07 2025 n/a \x08\x0a\x0b"
    )
    reading, lost = read_font(answers, glyph_order_proven=False)
    assert reading is FontReading.UNMAPPED
    assert lost == 9


def test_the_pdf_text_the_engine_reads_is_the_decoded_one(tmp_path: Path) -> None:
    pdf = tmp_path / "trial.pdf"
    pdf.write_bytes(_three_pages())

    first, second, third = pdf_page_texts(pdf)

    assert first.splitlines()[1:] == _PRINTED
    assert second == _ORDINARY
    # Nothing a check could compare the OCR text of this page with.
    assert third == ""


def test_a_conversion_holds_the_printed_text_and_names_the_pages(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "trial.pdf"
    pdf.write_bytes(_three_pages())
    engine = PdfEngine(
        picture_description=None, granite_vision_tables=False, figure_types=False
    )

    output = engine.convert(pdf, output_dir=tmp_path / "out")

    assert output.succeeded, output.errors
    assert output.markdown is not None
    for printed in _PRINTED:
        assert printed in output.markdown
    assert "6DPSOH" not in output.markdown
    assert output.quality is not None and output.quality.text_layer is not None
    assert output.quality.text_layer.glyph_order_pages == [1]
    assert output.quality.text_layer.unreadable_pages == [3]
    assert {warning.code for warning in output.quality.warnings} >= {
        "text_layer_decoded",
        "text_layer_read_by_ocr",
    }
    assert output.check is not None
    # The decoded page is checked against its decoded text and passes; the
    # page left to OCR is named, with nothing in the PDF to check it against.
    assert not output.check.page_recall.issues
    assert output.check.text_layer.unreadable_pages == [3]
    assert any("p3" in issue for issue in output.check.text_layer.issues)
