# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Check extracted text against the PDF's own text layer (pypdfium2).

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
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from pathlib import Path

from docling_core.types.doc import DoclingDocument, TableItem, TextItem
from docling_core.types.doc.document import FloatingMeta, MetaUtils

_log = logging.getLogger(__name__)

TABLE_TEXT_MIN_RECALL = 0.95
_META_NAMESPACE = "amir"
_META_NAME = "pdf_text"
TABLE_PDF_TEXT_META_KEY = MetaUtils.create_meta_field_name(
    namespace=_META_NAMESPACE, name=_META_NAME
)
_TOKEN = re.compile(r"[a-z0-9]{2,}")

_LIGATURES = {"fi", "fl", "ff", "ffi", "ffl"}
_WORD = re.compile(r"[a-z]+")
_TAIL = re.compile(r"[A-Za-z]*$")
_HEAD = re.compile(r"^[A-Za-z]*")
# pdfium marks a line-end hyphenation as U+FFFE or U+0002.
_HYPHENATION = re.compile(r"[￾\x02­]\s*")


def pdf_page_words(pdf_path: Path) -> dict[int, set[str]]:
    """Lower-case words of each page's text layer, keyed by 1-based page."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_path)
    try:
        pages: dict[int, set[str]] = {}
        for index in range(len(pdf)):
            page = pdf[index]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            textpage.close()
            page.close()
            text = unicodedata.normalize("NFKC", _HYPHENATION.sub("", text)).lower()
            pages[index + 1] = set(_WORD.findall(text))
        return pages
    finally:
        pdf.close()


def repair_ligature_splits(
    doc: DoclingDocument, page_words: dict[int, set[str]]
) -> int:
    """Rejoin ligature-split words in text items and table cells; returns the
    number of words rejoined."""
    fixed = 0
    for item, _level in doc.iterate_items(with_groups=False, traverse_pictures=True):
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
    if not any(t in _LIGATURES for t in tokens):
        return text, 0
    out: list[str] = []
    fixed = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        prev = out[-1] if out else None
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok not in _LIGATURES:
            out.append(tok)
            i += 1
            continue
        # Only the letters touching the ligature form the word: "domain-speci"
        # contributes "speci". Longest join first: "speci fi city" ->
        # "specificity", then "the fi rst" -> "the first", then "speci fi".
        tail = _TAIL.search(prev).group().lower() if prev is not None else ""
        head = _HEAD.match(nxt).group().lower() if nxt is not None else ""
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

    pdf = pdfium.PdfDocument(pdf_path)
    attached = 0
    try:
        for table in doc.tables:
            region_text = ""
            for prov in table.prov:
                if not 1 <= prov.page_no <= len(pdf):
                    continue
                page = pdf[prov.page_no - 1]
                bbox = prov.bbox.to_bottom_left_origin(page.get_height())
                textpage = page.get_textpage()
                region_text += textpage.get_text_bounded(bbox.l, bbox.b, bbox.r, bbox.t)
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
                    "text": _HYPHENATION.sub("", region_text).strip(),
                    "cell_text_recall": round(recall, 3),
                },
            )
            attached += 1
    finally:
        pdf.close()
    if attached:
        _log.info("Kept the PDF text of %d table(s) with incomplete cells", attached)
    return attached


def get_table_pdf_text(table: TableItem) -> dict | None:
    """The stored PDF text of a table box (``text``, ``cell_text_recall``)."""
    if table.meta is None:
        return None
    return table.meta.get_custom_part().get(TABLE_PDF_TEXT_META_KEY)


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", _HYPHENATION.sub("", text)).lower()
    return _TOKEN.findall(text)
