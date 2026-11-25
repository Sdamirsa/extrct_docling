# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

import logging
import re
import warnings
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional

import numpy as np
from docling_core.types.doc import BoundingBox
from docling_core.types.doc.page import TextCell
from PIL import ImageDraw
from PIL.Image import Image
from pydantic import BaseModel

from docling.datamodel.base_models import InputFormat, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions
from docling.datamodel.settings import settings
from docling.models.base_model import BasePageModel
from docling.utils.parser_repair import (
    LOOKALIKE,
    Respacer,
    letters_from_pdfium,
    lookalike_letters,
    needs_respacing,
    respacing_holds,
    spacing,
)
from docling.utils.profiling import TimeRecorder
from docling.utils.text_layer import PageTextLayer, read_document, read_pages, read_pdf

_log = logging.getLogger(__name__)


def resolve_skip_cell_extraction(pipeline_options: PdfPipelineOptions) -> bool:
    """Whether the native segmented-page (text-cell) decode can be skipped.

    In full-page OCR mode the native PDF text cells are discarded wholesale
    during OCR post-processing, so extracting them is pure waste — and on
    vector-dense pages (CAD/wiring schematics drawn as 100k+ path segments)
    that decode costs multiple GiB regardless of cell content levels.
    See https://github.com/docling-project/docling/issues/4058.
    """
    return bool(pipeline_options.do_ocr) and (
        pipeline_options.ocr_options.mode == OcrMode.FULL_PAGE
    )


class PagePreprocessingOptions(BaseModel):
    images_scale: Optional[float]
    skip_cell_extraction: bool = (
        False  # Skip text cell extraction for VLM-only processing
    )
    # Leave a page whose text layer is unreadable to the OCR stage (set when
    # OCR runs; without OCR the page keeps the text it has).
    ocr_unreadable_pages: bool = False
    # Repair the faults of docling-parse 7.20 (docling.utils.parser_repair).
    repair_parser_text: bool = False


class PagePreprocessingModel(BasePageModel):
    def __init__(self, options: PagePreprocessingOptions):
        self.options = options
        # The text layers of the document being converted, by its hash.
        self._text_layers: tuple[str, dict[int, PageTextLayer]] = ("", {})
        # Its pages decoded again with tighter word spacing, opened when needed.
        self._respacer: tuple[str, Respacer | None] = ("", None)

        # Pre-compiled regex patterns for efficiency
        self.GLYPH_RE = re.compile(r"GLYPH<[0-9A-Fa-f]+>")
        self.SLASH_G_RE = re.compile(r"(?:/G\d+){2,}")
        self.FRAG_RE = re.compile(r"\b[A-Za-z](?:/[a-z]{1,3}\.[a-z]{1,3}){2,}\b")
        self.SLASH_NUMBER_GARBAGE_RE = re.compile(
            r"(?:/\w+\s*){2,}"
        )  # Two or more "/token " sequences

    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:
        for page in page_batch:
            assert page._backend is not None
            if not page._backend.is_valid():
                yield page
            else:
                with TimeRecorder(conv_res, "page_parse"):
                    page = self._populate_page_images(page)
                    if not self.options.skip_cell_extraction:
                        page = self._parse_page_cells(conv_res, page)
                yield page

    # Generate the page image and store it in the page object
    def _populate_page_images(self, page: Page) -> Page:
        # default scale
        page.get_image(
            scale=1.0
        )  # puts the page image on the image cache at default scale

        images_scale = self.options.images_scale
        # user requested scales
        if images_scale is not None:
            page._default_image_scale = images_scale
            page.get_image(
                scale=images_scale
            )  # this will trigger storing the image in the internal cache

        return page

    def _read_through_fonts(self, conv_res: ConversionResult, page: Page) -> None:
        """Where the PDF's text layer does not say what the page prints
        (``docling.utils.text_layer``): give the cells of fonts read by glyph
        number their decoded text, and leave a page that is unreadable to the
        OCR stage, as a page without text."""
        if conv_res.input.format != InputFormat.PDF or page.parsed_page is None:
            return
        layer = self._document_text_layers(conv_res).get(page.page_no)
        if layer is None:
            return
        parsed = page.parsed_page
        if layer.unreadable and self.options.ocr_unreadable_pages:
            parsed.textline_cells, parsed.word_cells, parsed.char_cells = [], [], []
            parsed.has_lines = parsed.has_words = parsed.has_chars = False
            page.text_layer_unreadable = True
            return
        if not layer.glyph_order:
            return
        for cell in (*parsed.textline_cells, *parsed.word_cells, *parsed.char_cells):
            text, decoded = layer.read_box(cell.rect.to_bounding_box())
            if decoded:
                cell.text = cell.orig = " ".join(text.split())

    def _repair_parser_text(self, conv_res: ConversionResult, page: Page) -> None:
        """Repair the faults of docling-parse 7.20 in the page's cells
        (``docling.utils.parser_repair``, temporary): words run together,
        letters read as look-alikes. A page the text layer reads through its
        fonts is left to that."""
        parsed = page.parsed_page
        if (
            not self.options.repair_parser_text
            or conv_res.input.format != InputFormat.PDF
            or parsed is None
            or page.text_layer_unreadable
            or page.page_no in self._document_text_layers(conv_res)
        ):
            return
        source = conv_res.input._backend.path_or_stream
        before = spacing(cell.text for cell in parsed.textline_cells)
        if needs_respacing(before):
            again = self._document_respacer(conv_res, source).page(page.page_no)
            after = spacing(cell.text for cell in again.textline_cells)
            if respacing_holds(before, after):
                parsed.textline_cells = again.textline_cells
                parsed.word_cells = again.word_cells
                page.parser_respaced = True
            _log.info(
                "Page %d: %d runs of words without spaces; decoded again with "
                "tighter spacing: %d runs, %s",
                page.page_no,
                before.fused,
                after.fused,
                "kept" if page.parser_respaced else "not kept",
            )
        if not lookalike_letters(c.text for c in parsed.textline_cells):
            return
        layer = read_pages(source, [page.page_no]).get(page.page_no)
        if layer is None:
            return
        for cells, counted in (
            (parsed.textline_cells, True),
            (parsed.word_cells, False),
            (parsed.char_cells, False),
        ):
            for cell in cells:
                if not LOOKALIKE.search(cell.text):
                    continue
                pdfium, _ = layer.read_box(cell.rect.to_bounding_box())
                text, replaced = letters_from_pdfium(cell.text, pdfium)
                if not replaced:
                    continue
                cell.text = cell.orig = text
                if counted:
                    page.parser_letters_repaired += replaced

    def _document_respacer(
        self, conv_res: ConversionResult, source: Path | BytesIO
    ) -> Respacer:
        document = conv_res.input.document_hash
        held_for, respacer = self._respacer
        if held_for != document or respacer is None:
            if respacer is not None:
                respacer.close()
            respacer = Respacer(source)
            self._respacer = (document, respacer)
        return respacer

    def _document_text_layers(
        self, conv_res: ConversionResult
    ) -> dict[int, PageTextLayer]:
        document = conv_res.input.document_hash
        if self._text_layers[0] != document:
            self._text_layers = (document, self._read_text_layers(conv_res))
        return self._text_layers[1]

    @staticmethod
    def _read_text_layers(conv_res: ConversionResult) -> dict[int, PageTextLayer]:
        try:
            from pypdfium2 import PdfiumError
        except ImportError:
            # pdfium is an extra of its own beside docling-parse.
            return {}
        source = conv_res.input._backend.path_or_stream
        try:
            if isinstance(source, Path):
                return read_pdf(source)
            return read_document(source)
        except PdfiumError as exc:
            # A PDF pdfium cannot open on its own (a password): as before.
            _log.debug("Text layer of %s not read: %s", conv_res.input.file, exc)
            return {}

    # Extract and populate the page cells and store it in the page object
    def _parse_page_cells(self, conv_res: ConversionResult, page: Page) -> Page:
        assert page._backend is not None

        page.parsed_page = page._backend.get_segmented_page()
        assert page.parsed_page is not None
        self._read_through_fonts(conv_res, page)
        self._repair_parser_text(conv_res, page)

        # Rate the text quality from the PDF parser, and aggregate on page
        text_scores = []
        for c in page.cells:
            score = self.rate_text_quality(c.text)
            text_scores.append(score)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", "Mean of empty slice", RuntimeWarning, "numpy"
            )
            conv_res.confidence.pages[page.page_no].parse_score = float(
                np.nanquantile(
                    text_scores, q=0.10
                )  # To emphasise problems in the parse_score, we take the 10% percentile score of all text cells.
            )

        def draw_cell_boxes(
            image: Image,
            text_cells: Iterable[TextCell],
            shape_cells: Iterable[BoundingBox],
            bitmap_cells: Iterable[BoundingBox],
            show: bool = False,
        ) -> None:
            r"""Draw the PDF cells: text in red, shapes in blue, bitmaps in green"""

            image = image.copy()
            draw = ImageDraw.Draw(image)
            # Text cells in red
            for c in text_cells:
                bbox = c.to_bounding_box()
                x0, y0, x1, y1 = (bbox.l, bbox.t, bbox.r, bbox.b)

                draw.rectangle([(x0, y0), (x1, y1)], outline="red")
            # Connected shape regions in blue
            for bbox in shape_cells:
                x0, y0, x1, y1 = (bbox.l, bbox.t, bbox.r, bbox.b)

                draw.rectangle([(x0, y0), (x1, y1)], outline="blue")
            # Bitmap rects in green
            for bbox in bitmap_cells:
                x0, y0, x1, y1 = (bbox.l, bbox.t, bbox.r, bbox.b)

                draw.rectangle([(x0, y0), (x1, y1)], outline="green")
            if show:
                image.show()
            else:
                out_path: Path = (
                    Path(settings.debug.debug_output_path)
                    / f"debug_{conv_res.input.file.stem}"
                )
                out_path.mkdir(parents=True, exist_ok=True)

                out_file = out_path / f"cells_page_{page.page_no:05}.png"
                image.save(str(out_file), format="png")

        if settings.debug.visualize_cells:
            page_image = page.get_image(scale=1.0)
            if page_image is not None:
                # Not all backends support the shape boxes
                shape_boxes = page._backend.get_connected_shape_bounding_boxes()
                if shape_boxes is None:
                    shape_boxes = []

                draw_cell_boxes(
                    page_image,
                    page.cells,
                    shape_boxes,
                    page._backend.get_bitmap_rects(),
                )

        return page

    def rate_text_quality(self, text: str) -> float:
        # Hard errors: if any of these patterns are found, return 0.0 immediately.
        blacklist_chars = ["�"]
        if (
            any(text.find(c) >= 0 for c in blacklist_chars)
            or self.GLYPH_RE.search(text)
            or self.SLASH_G_RE.search(text)
            or self.SLASH_NUMBER_GARBAGE_RE.match(
                text
            )  # Check if text is mostly slash-number pattern
        ):
            return 0.0

        penalty = 0.0

        # Apply a penalty only if the fragmented words pattern occurs at least three times.
        frag_matches = self.FRAG_RE.findall(text)
        if len(frag_matches) >= 3:
            penalty += 0.1 * len(frag_matches)

        # Additional heuristic: if the average token length is below 2, add a penalty.
        # tokens = text.split()
        # if tokens and (sum(map(len, tokens)) / len(tokens)) < 2:
        #    penalty += 0.2

        return max(1.0 - penalty, 0.0)
