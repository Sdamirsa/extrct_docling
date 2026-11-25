# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Repair of a fault of Docling's PDF parser, docling-parse 7.28: the words
of tightly justified text run together.

**Temporary.** Remove this module when docling-parse separates these words
itself (a conversion with ``PdfPipelineOptions.repair_parser_text`` off then
shows no page this repair changes); what to test is in
``.claude/reference/quality/2026-11-25-parser-faults-and-upgrade-plan.md``.

In tightly justified text set without space characters (JAMA papers)
docling-parse takes some gaps between words for letter spacing:
"tionanddeathinpatientswithheartfailure". 7.28 separates more of them than
7.20 did (41811324 p2: 1.3 % of its words fused, 7.20 4.6 %), but judges
these gaps in em of the run's own letter spacing since 7.25, so the space
factors of ``DecodeConfig`` no longer move them and 7.20's repair (a decode
with factor 0.20) does nothing; on a synthetic Helvetica page it joins words
up to 0.125 em apart, as 7.20 did. The glyphs say where the words are: in
the runs of the fused pages measured, the gap between two glyphs at a
word's end was 0.11 to 0.15 of the line's height and at most 0 inside a
word (glyph boxes overlap). A page with :data:`MIN_FUSED_RUNS` runs of
:data:`FUSED_RUN_LETTERS`+ letters is decoded again with its glyphs (the
backend keeps none), and on a line holding such a run, a gap between two
glyphs wider than :data:`WORD_GAP` of the line's height, with no space
there, becomes one (so also after a comma or a digit: "(LBBB).It",
"12months"); word cells on that line are cut there. Letters never change;
a long word printed as one ("electrophysiological", a German compound) has
no such gap and stays whole.

7.20's other fault, letters read as look-alikes ("RepoƌtiŶg SuŵŵaƌǇ"),
7.28 reads right; ``check.json`` -> ``text_quality`` still names such pages.
This is unlike ``docling.utils.text_layer``, which reads PDFs whose text
layer itself does not say what the pages print, and stays.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from docling_core.types.doc import BoundingBox
from docling_core.types.doc.page import BoundingRectangle
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from docling_core.types.doc.page import SegmentedPdfPage, TextCell

# Runs of this many letters are two or more words run together; no page of
# the controls held one, the fused pages 2.3 to 4.6 % of their words.
FUSED_RUN_LETTERS = 18
MIN_FUSED_RUNS = 3
WORD_GAP = 0.06
MAX_ONE_LETTER_RISE = 0.01
MAX_CHAR_DIFFERENCE = 0.005

_WORD = re.compile(r"[A-Za-z]+")
_RUN = re.compile(f"[A-Za-z]{{{FUSED_RUN_LETTERS},}}")


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
    """The pages of one PDF decoded again by docling-parse with their glyphs,
    the line and word cells spaced where the glyphs of a run stand apart
    (:func:`respaced`); cells measured from the top-left corner, as the
    backend gives them."""

    def __init__(self, source: Path | BytesIO) -> None:
        from docling_parse.pdf_parser import DoclingPdfParser

        stream = BytesIO(source.getvalue()) if isinstance(source, BytesIO) else source
        self._document = DoclingPdfParser().load(path_or_stream=stream, lazy=True)

    def page(self, page_no: int) -> SegmentedPdfPage:
        page = self._document.get_page(page_no)
        height = page.dimension.height
        for cell in (*page.textline_cells, *page.word_cells, *page.char_cells):
            cell.to_top_left_origin(height)
        page.textline_cells, page.word_cells = respaced(page)
        return page

    def close(self) -> None:
        self._document.unload()


def respaced(page: SegmentedPdfPage) -> tuple[list[TextCell], list[TextCell]]:
    """The page's line and word cells with a space wherever, on a line that
    holds a run of :data:`FUSED_RUN_LETTERS`+ letters, two glyphs stand more
    than :data:`WORD_GAP` of the cell's height apart with no space between
    them; a word cell on such a line is cut into one per word there. Upright
    cells only."""
    glyphs = [
        (cell.rect.to_bounding_box(), cell.text)
        for cell in page.char_cells
        if cell.text.strip() and round(cell.rect.angle_360) == 0
    ]
    fused_lines = []
    lines = []
    for cell in page.textline_cells:
        gaps = _word_gaps(cell, glyphs) if _RUN.search(cell.text) else {}
        if gaps:
            fused_lines.append(cell.rect.to_bounding_box())
        lines.append(_spaced(cell, gaps) if gaps else cell)
    words: list[TextCell] = []
    for cell in page.word_cells:
        box = cell.rect.to_bounding_box()
        on_line = any(_centre_in(box, line) for line in fused_lines)
        gaps = _word_gaps(cell, glyphs) if on_line else {}
        words.extend(_cut(cell, gaps) if gaps else [cell])
    for index, cell in enumerate(words):
        cell.index = index
    return lines, words


def _word_gaps(
    cell: TextCell, glyphs: list[tuple[BoundingBox, str]]
) -> dict[int, float]:
    """The places in the cell's text a space goes before, each with the x of
    its gap. A cell whose characters its glyphs hold other than once in a row
    is left alone."""
    if round(cell.rect.angle_360) != 0:
        return {}
    box = cell.rect.to_bounding_box()
    mine = sorted((g for g in glyphs if _centre_in(g[0], box)), key=lambda g: g[0].l)
    # The glyph that printed each character (a ligature prints two).
    glyph_of = [number for number, (_, text) in enumerate(mine) for _ in text]
    printed = "".join(text for _, text in mine)
    squeezed = "".join(ch for ch in cell.text if not ch.isspace())
    at = printed.find(squeezed)
    if not squeezed or at < 0 or printed.find(squeezed, at + 1) >= 0:
        return {}
    widest = WORD_GAP * abs(box.b - box.t)
    gaps: dict[int, float] = {}
    k = at
    for offset, ch in enumerate(cell.text):
        if ch.isspace():
            continue
        if k > at and not cell.text[offset - 1].isspace():
            left, right = glyph_of[k - 1], glyph_of[k]
            before, after = mine[left][0], mine[right][0]
            if left != right and after.l - before.r > widest:
                gaps[offset] = (before.r + after.l) / 2
        k += 1
    return gaps


def _spaced(cell: TextCell, gaps: dict[int, float]) -> TextCell:
    text = "".join(" " + ch if i in gaps else ch for i, ch in enumerate(cell.text))
    return cell.model_copy(update={"text": text, "orig": text})


def _cut(cell: TextCell, gaps: dict[int, float]) -> list[TextCell]:
    box = cell.rect.to_bounding_box()
    places = sorted(gaps)
    edges = [box.l, *(gaps[place] for place in places), box.r]
    pieces = []
    for number, (start, end) in enumerate(zip([0, *places], [*places, len(cell.text)])):
        text = cell.text[start:end].strip()
        piece = BoundingBox(
            l=edges[number],
            t=box.t,
            r=edges[number + 1],
            b=box.b,
            coord_origin=box.coord_origin,
        )
        pieces.append(
            cell.model_copy(
                update={
                    "text": text,
                    "orig": text,
                    "rect": BoundingRectangle.from_bounding_box(piece),
                }
            )
        )
    return pieces


def _centre_in(glyph: BoundingBox, box: BoundingBox, slack: float = 0.5) -> bool:
    x = (glyph.l + glyph.r) / 2
    y = (glyph.t + glyph.b) / 2
    top, bottom = min(box.t, box.b), max(box.t, box.b)
    return box.l - slack <= x <= box.r + slack and top - slack <= y <= bottom + slack


class ParserRepairSummary(BaseModel):
    """Pages whose text cells of Docling's PDF parser were repaired
    (:mod:`docling.utils.parser_repair`, temporary): ``respaced_pages``
    whose words run together were spaced by the gaps between their
    glyphs."""

    respaced_pages: list[int] = Field(default_factory=list)

    @property
    def affected(self) -> bool:
        return bool(self.respaced_pages)
