# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Rejoin words the PDF parser split around a ligature glyph.

With some fonts Docling's parser emits a ligature glyph (``ﬁ``, ``ﬂ``...) as a
word of its own: "specificity" becomes "speci fi city", "first" becomes
"fi rst", in ``TextItem.text`` and table cells alike, so the markdown, chunks
and HTML can't be searched for the word. pypdfium2 reads the same PDF
correctly, so a split is rejoined only when the joined word occurs in
pdfium's text of the same page. ``TextItem.orig`` keeps the parser's text.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

from docling_core.types.doc import DoclingDocument, TableItem, TextItem

_log = logging.getLogger(__name__)

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
