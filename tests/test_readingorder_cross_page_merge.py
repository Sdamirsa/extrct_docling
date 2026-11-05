# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A paragraph that runs from a landscape page onto a portrait page keeps a
box on each page that holds that page's part of it."""

import ctypes
import re
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from docling_core.types.doc import CoordOrigin

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

_LEADING = 14.0
_ON_LANDSCAPE = [
    "We describe the second analysis here because it changes how the main",
    "result should be read by clinicians who use the score at the bedside",
    "and by the teams that maintain the registry in the participating",
]
_ON_PORTRAIT = [
    "centres, who asked for a version of the score that can be computed",
    "from the routine admission record without any additional laboratory",
    "tests or imaging studies being ordered for the patient.",
]


def _draw(
    pdf: pdfium.PdfDocument,
    page: pdfium.PdfPage,
    lines: list[str],
    top: float,
    size: float = 11.0,
) -> None:
    for n, line in enumerate(lines):
        obj = pdfium_c.FPDFPageObj_NewTextObj(
            pdf.raw, b"Helvetica", ctypes.c_float(size)
        )
        wide = (ctypes.c_ushort * (len(line) + 1))(*map(ord, line), 0)
        pdfium_c.FPDFText_SetText(obj, wide)
        pdfium_c.FPDFPageObj_Transform(obj, 1, 0, 0, 1, 72, top - n * _LEADING)
        pdfium_c.FPDFPage_InsertObject(page.raw, obj)


def _mixed_size_pdf(path: Path) -> None:
    pdf = pdfium.PdfDocument.new()
    landscape = pdf.new_page(792, 612)
    _draw(pdf, landscape, ["Results"], 540, size=14)
    _draw(
        pdf,
        landscape,
        [
            "The cohort included patients from three hospitals who were followed",
            "for a median of four years after the index visit, and the outcomes",
            "were adjudicated by two clinicians who did not know the model output.",
        ],
        510,
    )
    _draw(pdf, landscape, _ON_LANDSCAPE, 150)
    landscape.gen_content()
    portrait = pdf.new_page(612, 792)
    _draw(pdf, portrait, _ON_PORTRAIT, 720)
    _draw(
        pdf,
        portrait,
        [
            "A third analysis repeated the main model in the subgroup of patients",
            "with diabetes and found the same direction of effect in every centre.",
        ],
        650,
    )
    portrait.gen_content()
    pdf.save(path)
    pdf.close()


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text)


def test_cross_page_merge_boxes_each_part_on_its_own_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "landscape_then_portrait.pdf"
    _mixed_size_pdf(pdf_path)
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

    merged = [item for item in doc.texts if len(item.prov) > 1]
    assert len(merged) == 1
    assert [prov.page_no for prov in merged[0].prov] == [1, 2]

    pdf = pdfium.PdfDocument(pdf_path)
    try:
        for prov, lines in zip(merged[0].prov, (_ON_LANDSCAPE, _ON_PORTRAIT)):
            size = doc.pages[prov.page_no].size
            box = prov.bbox
            assert box.coord_origin == CoordOrigin.BOTTOMLEFT
            assert 0 <= box.l < box.r <= size.width
            assert 0 <= box.b < box.t <= size.height
            # Zero-origin, unrotated pages: the box is in PDF user space.
            textpage = pdf[prov.page_no - 1].get_textpage()
            boxed = textpage.get_text_bounded(box.l, box.b, box.r, box.t)
            assert _words(boxed) == _words(" ".join(lines))
    finally:
        pdf.close()
