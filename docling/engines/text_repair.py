# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Repair extracted text, mostly against the PDF's own text layer (pypdfium2).

- **Ligature splits.** With some fonts Docling's parser emits a ligature
  glyph (``ﬁ``, ``ﬂ``...) as a word of its own: "specificity" becomes
  "speci fi city", "first" becomes "fi rst", in ``TextItem.text`` and table
  cells alike, so no export can be searched for the word. A split is
  rejoined only when the joined word occurs in pdfium's text of the same
  page. ``TextItem.orig`` keeps the parser's text.
- **Table text.** A vision-language table model (Granite-Vision) retypes
  cell text from the image instead of reading the PDF; on 84 tables 4 kept
  under 90 % of the words printed in their box, and a crop it fails to parse
  becomes an empty table. When the cells hold less than
  :data:`TABLE_TEXT_MIN_RECALL` of those words, the box's PDF text is stored
  on the table (``amir__pdf_text`` meta) so the HTML can carry it.
- **VLM stop tokens.** A picture-description VLM can end its text with its
  end-of-sequence token (``<|end_of_text|>``), which then reaches the
  markdown, chunks and ``figures.jsonl``. Needs no PDF.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

from docling_core.types.doc import (
    ContentLayer,
    DescriptionAnnotation,
    DoclingDocument,
    ProvenanceItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.document import (
    DescriptionMetaField,
    FloatingMeta,
    MetaUtils,
)

from docling.utils.text_layer import read_pdf, user_space_rect

_log = logging.getLogger(__name__)

TABLE_TEXT_MIN_RECALL = 0.95
_META_NAMESPACE = "amir"
_META_NAME = "pdf_text"
TABLE_PDF_TEXT_META_KEY = MetaUtils.create_meta_field_name(
    namespace=_META_NAMESPACE, name=_META_NAME
)
_TOKEN = re.compile(r"[a-z0-9]{2,}")

LIGATURES = frozenset({"fi", "fl", "ff", "ffi", "ffl"})
_WORD = re.compile(r"[a-z]+")
WORD_TAIL = re.compile(r"[A-Za-z]*$")
WORD_HEAD = re.compile(r"^[A-Za-z]*")
# pdfium marks a line-end hyphenation as U+FFFE or U+0002.
PDF_HYPHENATION = re.compile(r"[\ufffe\x02\u00ad]\s*")

_VLM_STOP_TOKENS = (
    "<|end_of_text|>",
    "<end_of_utterance>",
    "<|im_end|>",
    "<|endoftext|>",
)
_TRAILING_STOP_TOKENS = re.compile(
    r"(?:\s*(?:" + "|".join(re.escape(t) for t in _VLM_STOP_TOKENS) + r"))+\s*$"
)


def strip_vlm_stop_tokens(doc: DoclingDocument) -> int:
    """Drop the end-of-sequence tokens a VLM left at the end of picture
    descriptions (``meta.description`` and the description annotation);
    returns the number of pictures cleaned."""
    cleaned = 0
    for picture in doc.pictures:
        descriptions: list[DescriptionAnnotation | DescriptionMetaField] = [
            annotation
            for annotation in picture.annotations
            if isinstance(annotation, DescriptionAnnotation)
        ]
        if picture.meta is not None and picture.meta.description is not None:
            descriptions.append(picture.meta.description)
        changed = False
        for description in descriptions:
            text = _TRAILING_STOP_TOKENS.sub("", description.text)
            if text != description.text:
                description.text = text
                changed = True
        cleaned += changed
    if cleaned:
        _log.info("Stripped VLM stop tokens from %d picture description(s)", cleaned)
    return cleaned


def pdf_page_words(pdf_path: Path) -> dict[int, set[str]]:
    """Lower-case words of each page's text layer, keyed by 1-based page."""
    pages: dict[int, set[str]] = {}
    for index, text in enumerate(pdf_page_texts(pdf_path)):
        text = unicodedata.normalize("NFKC", PDF_HYPHENATION.sub("", text)).lower()
        pages[index + 1] = set(_WORD.findall(text))
    return pages


def pdf_page_texts(pdf_path: Path) -> list[str]:
    """The text of each page's text layer as the page prints it: fonts read
    by glyph number are decoded, and a page that is unreadable has none
    (``docling.utils.text_layer``)."""
    import pypdfium2 as pdfium

    layers = read_pdf(pdf_path)
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        texts: list[str] = []
        for index in range(len(pdf)):
            layer = layers.get(index + 1)
            if layer is not None and layer.unreadable:
                texts.append("")
            elif layer is not None and layer.glyph_order:
                texts.append(layer.text())
            else:
                page = pdf[index]
                textpage = page.get_textpage()
                texts.append(textpage.get_text_range())
                textpage.close()
                page.close()
        return texts
    finally:
        pdf.close()


def repair_ligature_splits(
    doc: DoclingDocument, page_words: dict[int, set[str]]
) -> int:
    """Rejoin ligature-split words in text items and table cells; returns the
    number of words rejoined."""
    fixed = 0
    # Furniture too: the HTML renders running headers and footers.
    for item, _level in doc.iterate_items(
        with_groups=False,
        traverse_pictures=True,
        included_content_layers=set(ContentLayer),
    ):
        if not isinstance(item, TextItem | TableItem):
            continue
        known: set[str] = set().union(
            *(page_words.get(prov.page_no, set()) for prov in item.prov)
        )
        if not known:
            continue
        if isinstance(item, TextItem):
            item.text, n = _rejoin(item.text, known)
            fixed += n
        elif isinstance(item, TableItem):
            for cell in item.data.table_cells:
                cell.text, n = _rejoin(cell.text, known)
                fixed += n
    if fixed:
        _log.info("Rejoined %d ligature-split word(s)", fixed)
    return fixed


def _rejoin(text: str, known: set[str]) -> tuple[str, int]:
    tokens = text.split(" ")
    if not any(t in LIGATURES for t in tokens):
        return text, 0
    out: list[str] = []
    fixed = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        prev = out[-1] if out else ""
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if tok not in LIGATURES:
            out.append(tok)
            i += 1
            continue
        # Only the letters touching the ligature form the word: "domain-speci"
        # contributes "speci". Longest join first: "speci fi city" ->
        # "specificity", then "the fi rst" -> "the first", then "speci fi".
        tail = t.group().lower() if (t := WORD_TAIL.search(prev)) else ""
        head = h.group().lower() if (h := WORD_HEAD.match(nxt)) else ""
        if tail and head and tail + tok + head in known:
            out[-1] = prev + tok + nxt
            i += 2
        elif head and tok + head in known:
            out.append(tok + nxt)
            i += 2
        elif tail and tail + tok in known:
            out[-1] = prev + tok
            i += 1
        else:
            out.append(tok)
            i += 1
            continue
        fixed += 1
    return " ".join(out), fixed


def attach_table_pdf_text(doc: DoclingDocument, pdf_path: Path) -> int:
    """Store the PDF text of each table box whose cells miss words of it;
    returns the number of tables that got it."""
    import pypdfium2 as pdfium

    layers = read_pdf(pdf_path)
    pdf = pdfium.PdfDocument(pdf_path)
    attached = 0
    try:
        for table in doc.tables:
            region_text = ""
            for prov in table.prov:
                if not 1 <= prov.page_no <= len(pdf):
                    continue
                layer = layers.get(prov.page_no)
                if layer is not None and layer.unreadable:
                    # Nothing to compare the cells with, nothing worth keeping.
                    continue
                if layer is not None and layer.glyph_order:
                    region_text += layer.read_box(prov.bbox)[0]
                    continue
                page = pdf[prov.page_no - 1]
                textpage = page.get_textpage()
                region_text += textpage.get_text_bounded(
                    *user_space_rect(page, prov.bbox)
                )
                textpage.close()
                page.close()
            printed = Counter(_tokens(region_text))
            if not printed:
                continue
            in_cells = Counter(
                _tokens(" ".join(cell.text for cell in table.data.table_cells))
            )
            recall = 1 - sum((printed - in_cells).values()) / sum(printed.values())
            if recall >= TABLE_TEXT_MIN_RECALL:
                continue
            if table.meta is None:
                table.meta = FloatingMeta()
            table.meta.set_custom_field(
                _META_NAMESPACE,
                _META_NAME,
                {
                    "text": PDF_HYPHENATION.sub("", region_text).strip(),
                    "cell_text_recall": round(recall, 3),
                },
            )
            attached += 1
    finally:
        pdf.close()
    if attached:
        _log.info("Kept the PDF text of %d table(s) with incomplete cells", attached)
    return attached


class GlyphStyle(NamedTuple):
    """How a piece of text is printed: ``size`` is the font size on the page
    in points (to the nearest half), heavier styles compare greater."""

    size: float
    bold: bool
    upright: bool


# Font descriptor flags (PDF 32000-1, table 123).
_FONT_ITALIC = 1 << 6
_FONT_FORCE_BOLD = 1 << 18
_BOLD_WEIGHT = 600
_BOLD_NAME = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)
_ITALIC_NAME = re.compile(r"italic|oblique", re.IGNORECASE)
_STYLE_GRID = (8, 3)


def pdf_text_styles(
    pdf_path: Path, regions: Mapping[str, ProvenanceItem]
) -> dict[str, GlyphStyle]:
    """The style most of the characters printed in each region have, keyed as
    *regions*; a region without text-layer characters is left out.

    The layout model reports boxes, not type: whether two headings are set
    alike is only in the PDF."""
    import pypdfium2 as pdfium

    by_page: dict[int, list[str]] = {}
    for key, prov in regions.items():
        by_page.setdefault(prov.page_no, []).append(key)
    styles: dict[str, GlyphStyle] = {}
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        for page_no, keys in sorted(by_page.items()):
            if not 1 <= page_no <= len(pdf):
                continue
            page = pdf[page_no - 1]
            textpage = page.get_textpage()
            try:
                for key in keys:
                    rect = user_space_rect(page, regions[key].bbox)
                    style = _region_style(textpage, rect)
                    if style is not None:
                        styles[key] = style
            finally:
                textpage.close()
                page.close()
    finally:
        pdf.close()
    return styles


def _region_style(
    textpage, rect: tuple[float, float, float, float]
) -> GlyphStyle | None:
    import ctypes

    import pypdfium2.raw as pdfium_c

    left, bottom, right, top = rect
    columns, rows = _STYLE_GRID
    x_step, y_step = (right - left) / columns, (top - bottom) / rows
    indexes = {
        textpage.get_index(
            left + (column + 0.5) * x_step,
            bottom + (row + 0.5) * y_step,
            x_step / 2,
            y_step / 2,
        )
        for column in range(columns)
        for row in range(rows)
    }
    found: Counter[GlyphStyle] = Counter()
    name = ctypes.create_string_buffer(256)
    flags = ctypes.c_int()
    matrix = pdfium_c.FS_MATRIX()
    for index in indexes:
        if index is None or index < 0:
            continue
        size = pdfium_c.FPDFText_GetFontSize(textpage.raw, index)
        # The font size is in text space; a producer may set it to 1 and
        # scale by the matrix instead.
        if pdfium_c.FPDFText_GetMatrix(textpage.raw, index, matrix):
            size *= (matrix.c**2 + matrix.d**2) ** 0.5
        if size <= 0:
            continue
        flags.value = 0
        pdfium_c.FPDFText_GetFontInfo(
            textpage.raw, index, name, len(name), ctypes.byref(flags)
        )
        font = name.value.decode("utf-8", "replace")
        weight = pdfium_c.FPDFText_GetFontWeight(textpage.raw, index)
        found[
            GlyphStyle(
                size=round(size * 2) / 2,
                bold=bool(
                    _BOLD_NAME.search(font)
                    or flags.value & _FONT_FORCE_BOLD
                    or weight >= _BOLD_WEIGHT
                ),
                upright=not (_ITALIC_NAME.search(font) or flags.value & _FONT_ITALIC),
            )
        ] += 1
    return found.most_common(1)[0][0] if found else None


def get_table_pdf_text(table: TableItem) -> dict | None:
    """The stored PDF text of a table box (``text``, ``cell_text_recall``)."""
    if table.meta is None:
        return None
    return table.meta.get_custom_part().get(TABLE_PDF_TEXT_META_KEY)


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", PDF_HYPHENATION.sub("", text)).lower()
    return _TOKEN.findall(text)
