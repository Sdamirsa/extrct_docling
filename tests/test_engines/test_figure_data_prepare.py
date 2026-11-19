# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""What the prepare phase of figure-to-data hands a reader, on cases a real
paper brought up (round 4 of the chart-to-data mini bench)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)
from PIL import Image, ImageDraw

from docling.engines.figure_data.evidence import fit_axis
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.schema import FigureDataOptions
from docling.engines.figure_data.step import prepare_step

_GREY = (210, 210, 210)


def _masked_figure_bundle(tmp_path: Path) -> tuple[Path, Path]:
    """A one-page PDF whose figure is an image with a soft mask, and a
    bundle whose only picture is that image. The image is 900 x 600 px: an
    opaque grey plot area on a canvas that is transparent and stored black,
    with a black tick mark drawn on the transparent part."""
    import pypdfium2 as pdfium

    canvas = Image.new("RGBA", (900, 600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((150, 50, 850, 450), fill=(*_GREY, 255))
    draw.rectangle((145, 500, 155, 560), fill=(0, 0, 0, 255))
    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(300, 300)
    image = pdfium.PdfImage.new(pdf)
    image.set_bitmap(pdfium.PdfBitmap.from_pil(canvas))
    image.set_matrix(pdfium.PdfMatrix().scale(270, 180).translate(15, 60))
    page.insert_obj(image)
    page.gen_content()
    pdf_path = tmp_path / "masked.pdf"
    pdf.save(pdf_path)
    pdf.close()

    doc = DoclingDocument(name="masked")
    doc.add_page(page_no=1, size=Size(width=300, height=300))
    prov = ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(l=15, t=240, r=285, b=60, coord_origin=CoordOrigin.BOTTOMLEFT),
        charspan=(0, 0),
    )
    doc.add_text(label=DocItemLabel.TEXT, text="Accuracy by year.", prov=prov)
    doc.add_picture(prov=prov)
    bundle = tmp_path / "masked"
    (bundle / "images").mkdir(parents=True)
    rendered = pdfium.PdfDocument(pdf_path)
    rendered[0].render(scale=1.5).to_pil().save(bundle / "images" / "picture_001.png")
    rendered.close()
    doc.save_as_json(bundle / "document.json")
    row = {
        "index": 0,
        "self_ref": "#/pictures/0",
        "image_path": "images/picture_001.png",
        "figure_type": "line_chart",
        "is_noise": False,
        "caption_text": "",
    }
    (bundle / "figures.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    return bundle, pdf_path


def test_an_embedded_bitmap_is_taken_with_its_soft_mask(tmp_path: Path) -> None:
    """Figure 6 of the showcase paper: its image stores black where the mask
    makes it transparent. Taken without the mask, every reader got black
    where the page is white, and the axis labels printed there in black
    were gone. The figure's own pixels are kept where it is opaque."""
    bundle, pdf_path = _masked_figure_bundle(tmp_path)

    prepare_step(bundle, pdf_path, FigureDataOptions())

    figure_dir = bundle / "figure-to-data" / "pictures_0"
    assert PreparedFigure.load(figure_dir).capture == "embedded-bitmap"
    figure = np.asarray(Image.open(figure_dir / "figure.png").convert("RGB"))
    assert figure.shape[:2] == (600, 900)
    assert figure[3, 3].tolist() == [255, 255, 255]
    assert figure[300, 600].tolist() == list(_GREY)
    assert figure[530, 150].tolist() == [0, 0, 0]
    assert float((figure.max(axis=2) < 40).mean()) < 0.01


def test_ticks_that_lie_on_a_line_in_value_are_a_linear_axis() -> None:
    """Years a step apart fit a line in both scales; the last pixel made
    the x axis of that figure "log" in what the readers were told."""
    years = fit_axis([(100.4, "2021"), (300.0, "2022"), (499.5, "2023")], "x")
    octaves = fit_axis([(100, "1"), (200, "2"), (300, "4"), (400, "8")], "x")

    assert years is not None and years.scale == "linear"
    assert octaves is not None and octaves.scale == "log"
