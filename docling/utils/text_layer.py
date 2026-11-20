# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Whether a PDF's text layer says what its pages print.

A font embedded without a Unicode map leaves the text layer with the font's
glyph codes: the page prints "Sample size" and every reader of the PDF's
text gets ``6DPSOH\\x03VL]H``. Two kinds were found on 4,723 pages of trial
papers and their supplements (2026-11-20), in 5 of 87 PDFs:

- **Glyph order.** The codes are glyph numbers of a TrueType font in the
  standard order, where a glyph sits 29 places below its ASCII code. The
  text is recovered exactly (:func:`glyph_order_char`).
- **Unmapped.** The codes were handed out as the characters came (``!"#$%``
  for the first five glyphs of the font). Only the page image says what is
  printed: such text needs OCR.

The unit is a font object on a page, as pdfium reports it: a font is
readable or it is not, and one page can mix both (a heading font, a form's
answers, one run in the middle of a line).
"""

from __future__ import annotations

import ctypes
import logging
import re
from array import array
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from docling_core.types.doc import BoundingBox
from pydantic import BaseModel, Field

from docling.utils.locks import pypdfium2_lock

if TYPE_CHECKING:
    from pypdfium2 import PdfPage, PdfTextPage

_log = logging.getLogger(__name__)

GLYPH_ORDER_SHIFT = 29
_FIRST_GLYPH, _LAST_ASCII_GLYPH = 3, 97
# Glyphs 98 to 171 of the standard order (TrueType ``post`` format 1), then
# the marks as Microsoft's fonts number them: one lower than the standard,
# which holds a glyph for the non-breaking space at 172.
_GLYPHS_FROM_98 = (
    "ÄÅÇÉÑÖÜáàâäãåçéèêëíìîïñóòôöõúùûü"
    "†°¢£§•¶ß®©™´¨≠ÆØ∞±≤≥¥µ∂∑∏π∫ªºΩæø¿¡¬√ƒ≈∆«»…"  # noqa: RUF001
    "ÀÃÕŒœ–—“”‘’"  # noqa: RUF001
)
UNKNOWN_CHAR = "\ufffd"

# A font object is judged by the characters it has on one page.
_MIN_CONTROL_CHARS = 2
_MIN_CONTROL_SHARE = 0.05
_MAX_LOWER_SHARE = 0.1
_MAX_SYMBOLS_DECODED = 0.08
_MAX_UNKNOWN_DECODED = 0.1
_MIN_CHARS_FOR_PROOF = 20
_MIN_LETTER_SHARE_FOR_PROOF = 0.5
_PARTLY_READABLE_LOWER_SHARE = 0.3
_MIN_CHARS_FOR_SYMBOLS = 30
_MIN_SYMBOL_SHARE = 0.15
_MIN_DISTINCT_SYMBOLS = 6
# A page with this share of unreadable characters is read by OCR as a whole;
# from the lower share on it is named in the record.
UNREADABLE_PAGE_SHARE = 0.3
REPORTED_PAGE_SHARE = 0.02

_SYMBOLS = frozenset("!\"#$&'*+?@[\\]^_`{|}~")
_SAME_CHAR_RUN = re.compile(r"(.)\1{2,}", re.DOTALL)
# pdfium marks a line-end hyphenation with U+0002 or U+FFFE.
_NOT_COUNTED = frozenset(" \t\x02\ufffe\uffff")


class FontReading(str, Enum):
    READABLE = "readable"
    GLYPH_ORDER = "glyph_order"
    UNMAPPED = "unmapped"


def glyph_order_char(code: int) -> str:
    """The character a font in the standard glyph order prints for *code*."""
    if _FIRST_GLYPH <= code <= _LAST_ASCII_GLYPH:
        return chr(code + GLYPH_ORDER_SHIFT)
    if 98 <= code < 98 + len(_GLYPHS_FROM_98):
        return _GLYPHS_FROM_98[code - 98]
    return UNKNOWN_CHAR


@dataclass
class _Profile:
    chars: int = 0
    control: int = 0
    symbols: int = 0
    distinct_symbols: int = 0
    letters: int = 0
    lower: int = 0
    unknown: int = 0


def _profile(text: str) -> _Profile:
    # Leaders and rules ("......", "_____") say nothing about a font.
    kept = [ch for ch in _SAME_CHAR_RUN.sub("", text) if ch not in _NOT_COUNTED]
    symbols = [ch for ch in kept if ch in _SYMBOLS]
    return _Profile(
        chars=len(kept),
        control=sum(1 for ch in kept if ord(ch) < 32),
        symbols=len(symbols),
        distinct_symbols=len(set(symbols)),
        letters=sum(ch.isalpha() for ch in kept),
        lower=sum(ch.islower() for ch in kept),
        unknown=kept.count(UNKNOWN_CHAR),
    )


def _by_control(raw: _Profile) -> bool:
    return (
        raw.control >= _MIN_CONTROL_CHARS
        and raw.control >= _MIN_CONTROL_SHARE * raw.chars
    )


def _decodes_cleanly(text: str, raw: _Profile) -> _Profile | None:
    """The profile of *text* read in glyph order, when that reading holds
    next to no stray symbol and no glyph number past the known part."""
    if not _by_control(raw) or raw.lower > _MAX_LOWER_SHARE * raw.chars:
        return None
    decoded = _profile("".join(glyph_order_char(ord(ch)) for ch in text))
    if (
        decoded.symbols <= _MAX_SYMBOLS_DECODED * decoded.chars
        and decoded.unknown <= _MAX_UNKNOWN_DECODED * decoded.chars
    ):
        return decoded
    return None


def proves_glyph_order(text: str) -> bool:
    """Whether one font's characters on a page show on their own that the
    font is read by glyph number: enough of them, and words once decoded. A
    symbol font with three characters must not pass for one."""
    decoded = _decodes_cleanly(text, _profile(text))
    return (
        decoded is not None
        and decoded.chars >= _MIN_CHARS_FOR_PROOF
        and decoded.letters >= _MIN_LETTER_SHARE_FOR_PROOF * decoded.chars
    )


def read_font(text: str, *, glyph_order_proven: bool) -> tuple[FontReading, int]:
    """How the characters *text* of one font object on one page read, and
    how many of them are affected. *text* holds the characters pdfium
    reports for the font, without the spaces and line breaks pdfium adds.
    *glyph_order_proven*: some font of the document is read by glyph number
    beyond doubt, so a font with few characters (section numbers, a short
    heading) may be read the same way."""
    raw = _profile(text)
    if not raw.chars:
        return FontReading.READABLE, 0
    if glyph_order_proven and _decodes_cleanly(text, raw) is not None:
        return FontReading.GLYPH_ORDER, raw.chars
    if _by_control(raw):
        # A font that is readable but for some glyphs loses only those.
        partly = raw.lower >= _PARTLY_READABLE_LOWER_SHARE * raw.chars
        return FontReading.UNMAPPED, raw.control if partly else raw.chars
    if (
        raw.chars >= _MIN_CHARS_FOR_SYMBOLS
        and raw.symbols >= _MIN_SYMBOL_SHARE * raw.chars
        and raw.lower <= _MAX_LOWER_SHARE * raw.chars
        and raw.distinct_symbols >= _MIN_DISTINCT_SYMBOLS
    ):
        return FontReading.UNMAPPED, raw.chars
    return FontReading.READABLE, 0


@dataclass(frozen=True)
class PageGeometry:
    """Where a pdfium page's displayed area lies in PDF user space."""

    box: tuple[float, float, float, float]
    rotation: int
    height: float

    @classmethod
    def of(cls, page: PdfPage) -> PageGeometry:
        return cls(
            box=page.get_bbox(), rotation=page.get_rotation(), height=page.get_height()
        )

    def user_space_rect(self, bbox: BoundingBox) -> tuple[float, float, float, float]:
        """*bbox* as the ``(left, bottom, right, top)`` PDF user-space
        rectangle pdfium's text API takes.

        Docling measures from the top-left corner of the page as displayed:
        from the visible box (CropBox within MediaBox) and after ``/Rotate``.
        User space is unrotated and its origin is wherever the PDF puts it:
        some journals crop 34 pt off every side, and a box read without that
        offset reads the text 34 pt away.
        """
        box = bbox.to_top_left_origin(self.height)
        left, bottom, right, top = self.box
        if self.rotation == 90:
            return left + box.t, bottom + box.l, left + box.b, bottom + box.r
        if self.rotation == 180:
            return right - box.r, bottom + box.t, right - box.l, bottom + box.b
        if self.rotation == 270:
            return right - box.b, top - box.r, right - box.t, top - box.l
        return left + box.l, top - box.b, left + box.r, top - box.t


@dataclass
class PageTextLayer:
    """One page's text layer, read through its fonts.

    ``chars`` holds one entry per pdfium character index: the character the
    page prints there where the font could be read (glyph order decoded),
    else what the text layer holds. ``generated`` marks the spaces and line
    breaks pdfium adds between them.
    """

    page_no: int
    chars: list[str] = field(default_factory=list)
    generated: list[bool] = field(default_factory=list)
    decoded: list[bool] = field(default_factory=list)
    visible: int = 0
    glyph_order: int = 0
    unmapped: int = 0
    # Character centres in PDF user space, and what places a box of the
    # displayed page in that space.
    x: array = field(default_factory=lambda: array("d"))
    y: array = field(default_factory=lambda: array("d"))
    geometry: PageGeometry | None = None

    @property
    def affected(self) -> bool:
        return bool(self.glyph_order or self.unmapped)

    @property
    def unmapped_share(self) -> float:
        return self.unmapped / self.visible if self.visible else 0.0

    @property
    def unreadable(self) -> bool:
        """Too much of what the page prints cannot be read from its text
        layer: the page is to be read by OCR."""
        return self.unmapped_share >= UNREADABLE_PAGE_SHARE

    def text(self) -> str:
        """The page's text, as ``PdfTextPage.get_text_range`` gives it but
        with the glyph-order fonts decoded."""
        return _joined(self.chars)

    def read_box(self, bbox: BoundingBox) -> tuple[str, int]:
        """The text of the characters whose centre lies in a box of the
        displayed page, as ``PdfTextPage.get_text_bounded`` gives it but with
        the glyph-order fonts decoded; and how many of them were decoded."""
        assert self.geometry is not None
        left, bottom, right, top = self.geometry.user_space_rect(bbox)
        parts: list[str] = []
        decoded = 0
        inside_before = False
        for index, char in enumerate(self.chars):
            if self.generated[index]:
                # pdfium's own spaces and line breaks follow what they separate.
                if inside_before:
                    parts.append(char)
                continue
            inside_before = (
                left <= self.x[index] <= right and bottom <= self.y[index] <= top
            )
            if inside_before:
                parts.append(char)
                decoded += self.decoded[index]
        return _joined(parts).strip(), decoded


def _joined(chars: list[str]) -> str:
    # pdfium hands out UTF-16 code units: pair the surrogates.
    return "".join(chars).encode("utf-16", "surrogatepass").decode("utf-16", "replace")


@dataclass
class _PageChars:
    page_no: int
    codes: list[int] = field(default_factory=list)
    generated: list[bool] = field(default_factory=list)
    fonts: list[int] = field(default_factory=list)
    x: array = field(default_factory=lambda: array("d"))
    y: array = field(default_factory=lambda: array("d"))
    geometry: PageGeometry | None = None

    def font_texts(self) -> dict[int, str]:
        by_font: dict[int, list[str]] = {}
        for code, made_up, font in zip(self.codes, self.generated, self.fonts):
            if not made_up:
                by_font.setdefault(font, []).append(chr(code))
        return {font: "".join(chars) for font, chars in by_font.items()}


def _read_chars(textpage: PdfTextPage, page_no: int) -> _PageChars:
    import pypdfium2.raw as pdfium_c

    raw = textpage.raw
    page = _PageChars(page_no=page_no)
    for index in range(pdfium_c.FPDFText_CountChars(raw)):
        page.codes.append(pdfium_c.FPDFText_GetUnicode(raw, index))
        made_up = pdfium_c.FPDFText_IsGenerated(raw, index) == 1
        page.generated.append(made_up)
        font = 0
        if not made_up:
            text_object = pdfium_c.FPDFText_GetTextObject(raw, index)
            if text_object:
                font = (
                    ctypes.cast(
                        pdfium_c.FPDFTextObj_GetFont(text_object), ctypes.c_void_p
                    ).value
                    or 0
                )
        page.fonts.append(font)
    return page


def _read_centres(textpage: PdfTextPage, page: _PageChars) -> None:
    import pypdfium2.raw as pdfium_c

    left, right, bottom, top = (ctypes.c_double() for _ in range(4))
    for index, made_up in enumerate(page.generated):
        if made_up or not pdfium_c.FPDFText_GetCharBox(
            textpage.raw,
            index,
            ctypes.byref(left),
            ctypes.byref(right),
            ctypes.byref(bottom),
            ctypes.byref(top),
        ):
            page.x.append(float("nan"))
            page.y.append(float("nan"))
            continue
        page.x.append((left.value + right.value) / 2)
        page.y.append((bottom.value + top.value) / 2)


def _layer(page: _PageChars, *, glyph_order_proven: bool) -> PageTextLayer:
    readings = {
        font: read_font(text, glyph_order_proven=glyph_order_proven)
        for font, text in page.font_texts().items()
    }
    layer = PageTextLayer(page_no=page.page_no, generated=page.generated)
    layer.visible = sum(
        1
        for code, made_up in zip(page.codes, page.generated)
        if not made_up and chr(code) not in " \t"
    )
    for reading, affected in readings.values():
        if reading is FontReading.GLYPH_ORDER:
            layer.glyph_order += affected
        elif reading is FontReading.UNMAPPED:
            layer.unmapped += affected
    glyph_order_fonts = {
        font
        for font, (reading, _) in readings.items()
        if reading is FontReading.GLYPH_ORDER
    }
    layer.decoded = [
        not made_up and font in glyph_order_fonts
        for made_up, font in zip(page.generated, page.fonts)
    ]
    layer.chars = [
        glyph_order_char(code) if decoded else chr(code)
        for code, decoded in zip(page.codes, layer.decoded)
    ]
    layer.x, layer.y, layer.geometry = page.x, page.y, page.geometry
    return layer


def read_document(source: Path | BytesIO) -> dict[int, PageTextLayer]:
    """The pages (1-based) of a PDF whose text layer does not read as
    printed, each with its characters; an empty dict for an ordinary PDF."""
    import pypdfium2 as pdfium

    suspect: list[_PageChars] = []
    proven = False
    with pypdfium2_lock:
        pdf = pdfium.PdfDocument(
            source.getvalue() if isinstance(source, BytesIO) else source
        )
        try:
            for index in range(len(pdf)):
                page = pdf[index]
                textpage = page.get_textpage()
                try:
                    chars = _read_chars(textpage, index + 1)
                    texts = list(chars.font_texts().values())
                    # Every unreadable font shows up when glyph order is allowed.
                    if any(
                        read_font(text, glyph_order_proven=True)[0]
                        is not FontReading.READABLE
                        for text in texts
                    ):
                        _read_centres(textpage, chars)
                        chars.geometry = PageGeometry.of(page)
                        suspect.append(chars)
                        proven = proven or any(map(proves_glyph_order, texts))
                finally:
                    textpage.close()
                    page.close()
        finally:
            pdf.close()
    layers = {
        chars.page_no: layer
        for chars in suspect
        if (layer := _layer(chars, glyph_order_proven=proven)).affected
    }
    if layers:
        _log.warning(
            "Text layer not readable as printed on %d page(s): %d decoded from "
            "glyph order, %d to be read by OCR",
            len(layers),
            sum(1 for layer in layers.values() if layer.glyph_order),
            sum(1 for layer in layers.values() if layer.unreadable),
        )
    return layers


def read_pdf(path: Path) -> dict[int, PageTextLayer]:
    """:func:`read_document` of a file, remembered for the last few files:
    the conversion and its checks ask for the same PDF several times."""
    stat = path.stat()
    return _read_pdf(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


@lru_cache(maxsize=4)
def _read_pdf(path: str, size: int, modified_ns: int) -> dict[int, PageTextLayer]:
    return read_document(Path(path))


class PartlyUnreadablePage(BaseModel):
    page: int
    share: float


class TextLayerSummary(BaseModel):
    """The pages of a PDF whose text layer does not read as printed.

    ``glyph_order_pages``: text of fonts read by glyph number, decoded
    exactly. ``unreadable_pages``: too much of the page is in fonts no rule
    reads; OCR reads the page. ``partly_unreadable_pages``: some of it is
    (``share`` of the characters), and those characters are lost.
    """

    glyph_order_pages: list[int] = Field(default_factory=list)
    unreadable_pages: list[int] = Field(default_factory=list)
    partly_unreadable_pages: list[PartlyUnreadablePage] = Field(default_factory=list)

    @property
    def affected(self) -> bool:
        return bool(
            self.glyph_order_pages
            or self.unreadable_pages
            or self.partly_unreadable_pages
        )


def summary(layers: dict[int, PageTextLayer]) -> TextLayerSummary:
    return TextLayerSummary(
        glyph_order_pages=sorted(
            page_no for page_no, layer in layers.items() if layer.glyph_order
        ),
        unreadable_pages=sorted(
            page_no for page_no, layer in layers.items() if layer.unreadable
        ),
        partly_unreadable_pages=[
            PartlyUnreadablePage(page=page_no, share=round(layer.unmapped_share, 3))
            for page_no, layer in sorted(layers.items())
            if not layer.unreadable and layer.unmapped_share >= REPORTED_PAGE_SHARE
        ],
    )


def pages_text(numbers: list[int], limit: int = 12) -> str:
    """``p3, p4, p9 and 14 more``."""
    shown = ", ".join(f"p{number}" for number in numbers[:limit])
    more = len(numbers) - limit
    return f"{shown} and {more} more" if more > 0 else shown


def user_space_rect(
    page: PdfPage, bbox: BoundingBox
) -> tuple[float, float, float, float]:
    """*bbox* of the displayed *page* as the ``(left, bottom, right, top)``
    PDF user-space rectangle pdfium's text API takes."""
    return PageGeometry.of(page).user_space_rect(bbox)
