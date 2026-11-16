# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A diagonal watermark printed across every page stays out of the text: the
page keeps its heading and paragraphs, a paragraph still continues onto the
next page, and the watermark is a background-layer item."""

import ctypes
import math
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from docling_core.types.doc import ContentLayer, DocItemLabel

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

_WATERMARK = "Preprint not peer reviewed"
_LEADING = 14.0
_FIRST = [
    "The cohort included patients from three hospitals who were followed",
    "for a median of four years after the index visit, and the outcomes",
    "were adjudicated by two clinicians who did not know the model output.",
]
_CONTINUED = [
    "We describe the second analysis here because it changes how the main",
    "result should be read by clinicians who use the score at the bedside",
    "and by the teams that maintain the registry in the participating",
]
_CONTINUATION = [
    "centres, who asked for a version of the score that can be computed",
    "from the routine admission record without any additional laboratory",
    "tests or imaging studies being ordered for the patient.",
]
_LAST = [
    "A third analysis repeated the main model in the subgroup of patients",
    "with diabetes and found the same direction of effect in every centre.",
]


def _text(
    pdf: pdfium.PdfDocument,
    page: pdfium.PdfPage,
    line: str,
    *,
    x: float,
    y: float,
    size: float = 11.0,
    degrees: float = 0.0,
    grey: int = 0,
) -> None:
    obj = pdfium_c.FPDFPageObj_NewTextObj(pdf.raw, b"Helvetica", ctypes.c_float(size))
    pdfium_c.FPDFPageObj_SetFillColor(obj, grey, grey, grey, 255)
    wide = (ctypes.c_ushort * (len(line) + 1))(*map(ord, line), 0)
    pdfium_c.FPDFText_SetText(obj, wide)
    cos, sin = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    pdfium_c.FPDFPageObj_Transform(obj, cos, sin, -sin, cos, x, y)
    pdfium_c.FPDFPage_InsertObject(page.raw, obj)


def _paragraph(
    pdf: pdfium.PdfDocument, page: pdfium.PdfPage, lines: list[str], top: float
) -> None:
    for n, line in enumerate(lines):
        _text(pdf, page, line, x=72, y=top - n * _LEADING)


def _watermarked_pdf(path: Path) -> None:
    pdf = pdfium.PdfDocument.new()
    first = pdf.new_page(612, 792)
    _text(pdf, first, "Results", x=72, y=720, size=14)
    _paragraph(pdf, first, _FIRST, 690)
    _paragraph(pdf, first, _CONTINUED, 120)
    second = pdf.new_page(612, 792)
    _paragraph(pdf, second, _CONTINUATION, 720)
    _paragraph(pdf, second, _LAST, 650)
    for page in (first, second):
        _text(pdf, page, _WATERMARK, x=90, y=90, size=58, degrees=52, grey=225)
        page.gen_content()
    pdf.save(path)
    pdf.close()


def test_diagonal_watermark_stays_out_of_the_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "watermarked.pdf"
    _watermarked_pdf(pdf_path)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=PdfPipelineOptions(
                    do_ocr=False, do_table_structure=False
                )
            )
        }
    )
    doc = converter.convert(pdf_path).document

    background = [
        item for item in doc.texts if item.content_layer == ContentLayer.BACKGROUND
    ]
    assert [(item.text, item.prov[0].page_no) for item in background] == [
        (_WATERMARK, 1),
        (_WATERMARK, 2),
    ]

    body = [item for item in doc.texts if item.content_layer == ContentLayer.BODY]
    assert " ".join(item.text for item in body) == " ".join(
        ["Results", *_FIRST, *_CONTINUED, *_CONTINUATION, *_LAST]
    )
    assert body[0].label == DocItemLabel.SECTION_HEADER
    continued = [item for item in body if len(item.prov) > 1]
    assert [item.text for item in continued] == [" ".join(_CONTINUED + _CONTINUATION)]
    assert [prov.page_no for prov in continued[0].prov] == [1, 2]
