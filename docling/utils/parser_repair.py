# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Repairs of two faults of Docling's PDF parser, docling-parse 7.20.

**Temporary.** docling-parse 7.28 reads both right on every page measured
(2026-11-25). Remove this module when the upgrade is validated and a
conversion with ``PdfPipelineOptions.repair_parser_text`` off shows it
changes nothing; the plan, with what to test, is in
``.claude/reference/quality/2026-11-25-parser-faults-and-upgrade-plan.md``.

Found on the 416 bundles of trial papers and supplements converted
2026-11-20 to 2026-11-24:

- **Look-alike letters** (1 bundle, 6 pages). For some fonts (a Calibri subset
  written by Word) the parser gives a glyph number for the character, a
  letter of Latin Extended-A/B: "RepoƌtiŶg SuŵŵaƌǇ" where the page prints
  "Reporting Summary", "śłŜ" for "(1)", "łŃ months" for "12 months".
  pdfium reads the same characters right. A cell's character of that block
  that pdfium reads as a printable ASCII character at the same place (the
  two texts aligned) takes pdfium's; a real "ł" or "Š" reads the same in
  both and stays.
- **Fused words** (27 bundles; 82 pages of 17 repaired). In tightly
  justified text without space characters (JAMA papers) the parser joins
  two words whose gap is
  under 0.33 of the font's space width: "studiesandsmallrandomizedclinical
  trials". A page with such runs is decoded again with 0.20, which separated
  the words on every page measured and split none there; on a normal NEJM
  page 0.20 splits words (one-letter tokens 1.1 % -> 5.5 %), so the new
  decode is kept only where the runs go, words stay whole and the page's
  characters are the same.

This is unlike ``docling.utils.text_layer``, which reads PDFs whose text
layer itself does not say what the pages print, and stays.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from docling_core.types.doc.page import SegmentedPdfPage

# Glyph numbers of the letters, digits and brackets of the fonts seen fall
# in these blocks: Latin Extended-A/B, IPA, spacing and combining marks, the
# Greek signs below the letters, the Coptic forms the Calibri subset gave its
# digits, Cyrillic (a glyph number read for ">="). The Greek letters are
# left out: a Symbol font prints them from ASCII codes, so pdfium reads
# "81 m" where the page prints and Docling reads micrometres; taking
# pdfium's would turn a unit into another. A real Polish or Cyrillic letter
# reads the same in pdfium and stays. The check names a page from this many
# the PDF's text lacks.
LOOKALIKE = re.compile("[\u0100-\u0385\u03d8-\u04ff]")
MIN_PAGE_LOOKALIKES = 3
# Runs of this many letters are two or more words run together; no page of
# the controls held one, the fused pages 2.3 to 4.6 % of their words.
FUSED_RUN_LETTERS = 18
MIN_FUSED_RUNS = 3
RESPACED_SPACE_FACTOR = 0.20
MAX_ONE_LETTER_RISE = 0.01
MAX_CHAR_DIFFERENCE = 0.005

_WORD = re.compile(r"[A-Za-z]+")
# pdfium marks a line-end hyphen with U+0002 or U+FFFE.
_PDFIUM_HYPHENS = str.maketrans({"\x02": "-", "\ufffe": "-"})


def lookalike_letters(texts: Iterable[str]) -> int:
    """How many characters of the look-alike blocks *texts* hold."""
    return sum(len(LOOKALIKE.findall(text)) for text in texts)


def letters_from_pdfium(text: str, pdfium: str) -> tuple[str, int]:
    """*text* (a cell of Docling's parser) with each character of the
    look-alike blocks that pdfium reads as a printable ASCII character at the
    same place taking pdfium's, and how many did. The two are aligned without
    their spaces and pdfium's non-ASCII marks (a bullet), which could never
    replace one (:func:`_aligned`), so a neighbour's character in pdfium's
    box does not shift the places."""
    theirs = [
        ch
        for ch in pdfium.translate(_PDFIUM_HYPHENS)
        if not ch.isspace()
        and (ch.isascii() or not unicodedata.category(ch).startswith(("P", "S")))
    ]
    ours = [index for index, ch in enumerate(text) if not ch.isspace()]
    chars = list(text)
    replaced = 0
    for mine, other in _aligned([chars[i] for i in ours], theirs):
        index = ours[mine]
        if _stands_for(chars[index], theirs[other]) and chars[index] != theirs[other]:
            chars[index] = theirs[other]
            replaced += 1
    return "".join(chars), replaced


def _stands_for(char: str, other: str) -> bool:
    return bool(LOOKALIKE.match(char)) and other.isascii() and other.isprintable()


def _aligned(ours: list[str], theirs: list[str]) -> list[tuple[int, int]]:
    """The places of *ours* and *theirs* paired by the cheapest edit: equal
    characters, and a look-alike against a printable ASCII character, cost
    nothing; another pair, or a character of one side only, costs one."""
    rows, cols = len(ours), len(theirs)
    if not rows or not cols:
        return []
    cost = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        cost[i][0] = i
    for j in range(1, cols + 1):
        cost[0][j] = j
    for i in range(1, rows + 1):
        mine = ours[i - 1]
        above, row = cost[i - 1], cost[i]
        for j in range(1, cols + 1):
            other = theirs[j - 1]
            pair = 0 if mine == other or _stands_for(mine, other) else 1
            row[j] = min(above[j - 1] + pair, above[j] + 1, row[j - 1] + 1)
    pairs: list[tuple[int, int]] = []
    i, j = rows, cols
    while i and j:
        mine, other = ours[i - 1], theirs[j - 1]
        pair = 0 if mine == other or _stands_for(mine, other) else 1
        if cost[i][j] == cost[i - 1][j - 1] + pair:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif cost[i][j] == cost[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


@dataclass(frozen=True)
class Spacing:
    """How the words of a page's text are spaced."""

    words: int
    fused: int
    one_letter: int
    chars: int

    @property
    def one_letter_share(self) -> float:
        return self.one_letter / self.words if self.words else 0.0


def spacing(texts: Iterable[str]) -> Spacing:
    """Words, runs of :data:`FUSED_RUN_LETTERS`+ letters, one-letter words
    other than "a" and "I", and characters other than spaces."""
    joined = "\n".join(texts)
    words = _WORD.findall(joined)
    return Spacing(
        words=len(words),
        fused=sum(len(word) >= FUSED_RUN_LETTERS for word in words),
        one_letter=sum(len(word) == 1 and word not in "aAI" for word in words),
        chars=sum(not ch.isspace() for ch in joined),
    )


def needs_respacing(found: Spacing) -> bool:
    return found.fused >= MIN_FUSED_RUNS


def respacing_holds(before: Spacing, after: Spacing) -> bool:
    """The page decoded again keeps its characters, has at most half the
    runs and splits no more words than it joined."""
    return (
        abs(after.chars - before.chars) <= MAX_CHAR_DIFFERENCE * before.chars
        and after.fused * 2 <= before.fused
        and after.one_letter_share - before.one_letter_share <= MAX_ONE_LETTER_RISE
    )


class Respacer:
    """The pages of one PDF decoded again by docling-parse with the space
    factor :data:`RESPACED_SPACE_FACTOR`, its other settings as the backend
    has them; cells measured from the top-left corner, as the backend gives
    them."""

    def __init__(self, source: Path | BytesIO) -> None:
        from docling_parse.pdf_parser import DecodeConfig, DoclingPdfParser

        stream = BytesIO(source.getvalue()) if isinstance(source, BytesIO) else source
        self._document = DoclingPdfParser().load(
            path_or_stream=stream,
            lazy=True,
            decode_config=DecodeConfig(
                line_space_width_factor_for_merge_with_space=RESPACED_SPACE_FACTOR,
                word_space_width_factor_for_merge=RESPACED_SPACE_FACTOR,
            ),
        )

    def page(self, page_no: int) -> SegmentedPdfPage:
        page = self._document.get_page(page_no)
        height = page.dimension.height
        for cell in (*page.textline_cells, *page.word_cells, *page.char_cells):
            cell.to_top_left_origin(height)
        return page

    def close(self) -> None:
        self._document.unload()


class ParserRepairSummary(BaseModel):
    """Pages whose text cells of Docling's PDF parser were repaired
    (:mod:`docling.utils.parser_repair`, temporary): ``respaced_pages``
    decoded again with tighter word spacing; ``letter_pages`` with letters
    read as look-alikes replaced by pdfium's (``letters`` of them, in the
    text lines)."""

    respaced_pages: list[int] = Field(default_factory=list)
    letter_pages: list[int] = Field(default_factory=list)
    letters: int = 0

    @property
    def affected(self) -> bool:
        return bool(self.respaced_pages or self.letter_pages)
