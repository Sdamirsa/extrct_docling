# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Document structure pass: where every element of a converted paper sits.

Docling's layout model labels page regions; it gives no heading levels (every
section header is level 1, the paper's title included), calls a running line
a heading on some pages and a page header on others, and ties a caption to
its table or figure only when the two are neighbours. :func:`structure_document`
runs on the :class:`DoclingDocument` before any export and settles that, so
``document.json``, the markdown, the chunks and ``<stem>.html`` agree:

- **furniture** — a short line repeated at the same place in the top or
  bottom margin of three or more pages becomes a page header / footer;
- **captions** — a heading or paragraph that reads ``Table S11. …`` /
  ``Fig. 2`` / ``Algorithm 1 …`` becomes a caption, and a caption without a
  table or figure is tied to the nearest one of its kind on its page;
- **missed headings** — a paragraph that is only a standard section name
  (``Methods``) becomes a section header;
- **title** — the heading set largest on the first page becomes the title;
- **heading levels** — from numbering (``2.1``, ``A.1``, ``IV.``), standard
  section names, then the heading's size and position; written to
  ``SectionHeaderItem.level`` (so ``<h2>``..``<h6>`` and the chunks' heading
  path follow) and to the outline.

Labels change in place and ``self_ref`` never does. What the pass decided is
returned as a :class:`DocumentStructure` (``structure.json`` in the bundle):
the outline, one :class:`ElementInfo` per item (role, section, number, links)
and the list of relabelled items with the rule that did it.

:func:`quality_report` counts what the document holds and raises warnings
with stable codes; a blocking one means the conversion is not usable as is.

Bump :data:`STRUCTURE_VERSION` whenever a rule here, or in the layout stages
it builds on, can change a label, a level or a link: locators a consumer made
against an older bundle may then no longer hold.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Literal

from docling_core.types.doc import (
    CodeItem,
    ContentLayer,
    DocItem,
    DocItemLabel,
    DoclingDocument,
    FloatingItem,
    FormulaItem,
    ListItem,
    NodeItem,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)
from docling_core.types.doc.document import RefItem
from pydantic import BaseModel, Field

from docling.engines.run_snapshot import write_text_atomic
from docling.engines.text_repair import GlyphStyle, pdf_text_styles
from docling.utils.parser_repair import ParserRepairSummary
from docling.utils.text_layer import TextLayerSummary, pages_text

_log = logging.getLogger(__name__)

STRUCTURE_VERSION = "1"
STRUCTURE_FILENAME = "structure.json"
STRUCTURE_SCHEMA = "extrct.structure/1"

DEFAULT_FURNITURE_REPEAT_THRESHOLD = 3
# A running line sits in the top or bottom tenth of the page.
MARGIN_BAND = 0.10
_FURNITURE_MAX_CHARS = 150
_TITLE_MIN_WORDS = 4
_TITLE_SIZE_SHARE = 0.75
# Sizes estimated from boxes vary by a tenth between headings set alike
# (ascenders, descenders); sizes closer than this are one size.
_BOX_SIZE_STEP = 1.15
_NUMBERED_MIN_HEADINGS = 3
_SECTION_NUMBER_SLACK = 3
_MAX_LEVEL = 6

MIN_BODY_TEXTS_PER_PAGE = 1.0
PACKED_TEXT_MIN_CHARS_PER_PAGE = 200
HEADERLESS_MAX_PAGES = 5
TABLE_TEXT_SHARE_MAX = 0.5

DocumentRole = Literal["manuscript", "supplement"]
LevelSource = Literal["numbering", "standard-name", "font-size", "position"]
Zone = Literal[
    "front-matter", "abstract", "body", "reference", "back-matter", "supplement"
]

RULE_REPEATED_TEXT = "rule:repeated-text"
RULE_CAPTION_PATTERN = "rule:caption-pattern"
RULE_STANDARD_SECTION_NAME = "rule:standard-section-name"
RULE_TITLE = "rule:largest-heading-on-first-page"


class OutlineEntry(BaseModel):
    """One section header of the body, in reading order."""

    ref: str
    level: int
    number: str | None = None
    title: str
    page: int | None = None
    parent: str | None = None
    path: list[str] = Field(default_factory=list)
    level_source: LevelSource
    zone: Zone


class Relabel(BaseModel):
    """An item whose label the pass changed, and the rule that did."""

    ref: str
    was: str
    now: str
    rule: str
    page: int | None = None
    text: str


class ElementInfo(BaseModel):
    """What the pass knows about one item; unset fields do not apply."""

    role: str
    section_ref: str | None = None
    level: int | None = None
    level_source: LevelSource | None = None
    number: str | None = None
    parent_ref: str | None = None
    caption_ref: str | None = None
    caption_for: str | None = None
    footnote_for: str | None = None
    first_mention_ref: str | None = None
    first_mention_section_ref: str | None = None
    label_was: str | None = None
    label_source: str | None = None
    repeat_count: int | None = None


class DocumentStructure(BaseModel):
    """Result of :func:`structure_document`."""

    schema_version: str = STRUCTURE_SCHEMA
    structure_version: str = STRUCTURE_VERSION
    document_role: DocumentRole = "manuscript"
    title_ref: str | None = None
    outline: list[OutlineEntry] = Field(default_factory=list)
    relabels: list[Relabel] = Field(default_factory=list)
    elements: dict[str, ElementInfo] = Field(default_factory=dict)


class QualityWarning(BaseModel):
    code: str
    blocking: bool
    detail: str


class RepeatedHeading(BaseModel):
    text: str
    count: int


class QualityReport(BaseModel):
    """Counts of what a converted document holds, and warnings.

    Warning codes: ``no_body_text`` (blocking: nothing readable came out),
    ``few_text_blocks`` (blocking: the text is there but packed into fewer
    blocks than pages, so paragraphs and headings are lost), ``no_headings``,
    ``repeated_heading_text``, ``text_mostly_in_tables``,
    ``pages_without_content``; and from the PDF's text layer
    (:func:`text_layer_warnings`): ``text_layer_decoded``,
    ``text_layer_read_by_ocr``, ``text_layer_unreadable`` (blocking: OCR was
    off), ``text_layer_partly_unreadable``; and from the repair of Docling's
    PDF parser (:func:`parser_repair_warnings`): ``parser_text_repaired``.
    """

    pages: int = 0
    label_counts: dict[str, int] = Field(default_factory=dict)
    layer_counts: dict[str, int] = Field(default_factory=dict)
    page_label_counts: dict[int, dict[str, int]] = Field(default_factory=dict)
    body_text_items: int = 0
    body_text_chars: int = 0
    section_headers: int = 0
    pages_without_text: list[int] = Field(default_factory=list)
    chars_in_tables_share: float | None = None
    repeated_heading_texts: list[RepeatedHeading] = Field(default_factory=list)
    text_layer: TextLayerSummary | None = None
    parser_repair: ParserRepairSummary | None = None
    warnings: list[QualityWarning] = Field(default_factory=list)

    @property
    def blocking(self) -> list[QualityWarning]:
        return [warning for warning in self.warnings if warning.blocking]


# --- text patterns ------------------------------------------------------------

_DECIMAL = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,4})\.?\s+(?=\S)")
_ROMAN = re.compile(r"^((?:X{0,2})(?:IX|IV|V?I{0,3}))\.\s+(?=\S)")
_LETTER = re.compile(
    r"^(?:Appendix\s+)?([A-Z](?:\.\d{1,2}){1,3}|[A-Z](?=\.\s))\.?\s+(?=\S)"
)
_APPENDIX_LETTER = re.compile(r"^Appendix\s+([A-Z])\b[.:]?\s*")
# "A Implementation Details": a letter scheme only when the document's
# headings run A, B, ... (a title starting "A Knowledge ..." is alone).
_BARE_LETTER = re.compile(r"^([A-Z])\s+(?=[A-Z])")
# "1) Stent Detection": a step below whatever numbered heading precedes it.
_PAREN = re.compile(r"^((?:\d{1,2}|[a-z])\))\s+(?=\S)")

_SECTION_ZONES: tuple[tuple[Zone, str], ...] = (
    ("abstract", r"(?:structured\s+|graphical\s+)?abstract|summary"),
    (
        "body",
        r"introduction|background|(?:materials?|patients|subjects)\s+and\s+methods"
        r"|methods?|methodology|experiments?|results?|results\s+and\s+discussion"
        r"|discussion|conclusions?|limitations|related\s+work|case\s+presentation"
        r"|case\s+reports?|case\s+description",
    ),
    ("reference", r"references|bibliography|literature\s+cited|works\s+cited"),
    (
        "back-matter",
        r"acknowledge?ments?|funding(?:\s+sources?)?|data\s+availability(?:\s+statement)?"
        r"|code\s+availability|data\s+and\s+code\s+availability|author\s+contributions?"
        r"|contributors|competing\s+interests?|conflicts?\s+of\s+interests?"
        r"|declarations?(?:\s+of\s+.+)?|disclosures?|ethic(?:s|al)\s+.+|consent(?:\s+.+)?"
        r"|additional\s+information|abbreviations|author\s+information"
        r"|figure\s+legends?|figures|tables",
    ),
    (
        "supplement",
        r"supplementa(?:ry|l)\s+.+|appendix(?:\s+.+)?|appendices|extended\s+data(?:\s+.+)?",
    ),
)
_SECTION_NAMES = tuple(
    (zone, re.compile(rf"^(?:{pattern})$", re.IGNORECASE))
    for zone, pattern in _SECTION_ZONES
)

# Names a paragraph must consist of to be taken for a missed heading: fewer
# than the names that classify a heading, since a stray "Tables" or "Summary"
# is as likely a label in a diagram.
_PROMOTABLE = re.compile(
    r"^(?:abstract|introduction|background|(?:materials?|patients)\s+and\s+methods"
    r"|methods?|results?|discussion|conclusions?|references|acknowledge?ments?"
    r"|funding|data\s+availability(?:\s+statement)?|code\s+availability"
    r"|author\s+contributions?|competing\s+interests?|conflicts?\s+of\s+interests?"
    r"|case\s+(?:presentation|reports?|description)"
    r"|supplementa(?:ry|l)\s+(?:materials?|information|data))$",
    re.IGNORECASE,
)

_CAPTION = re.compile(
    r"^(?P<prefix>(?:Supplementa(?:ry|l)|Suppl\.?|Extended\s+Data|Online|Appendix)\s+)?"
    r"(?P<e>e)?(?P<kind>Table|Tab\.|Figure|Fig\.?|Algorithm|Alg\.|Box|Scheme|Listing)\s*"
    r"(?P<id>[A-Z]?\.?\d+[A-Za-z]?(?:\.\d+)?)(?![A-Za-z0-9])"
    r"(?P<sep>\s*[.:|])?",
    re.IGNORECASE,
)
_CAPTION_KINDS = {
    "table": "table",
    "tab.": "table",
    "figure": "figure",
    "fig.": "figure",
    "fig": "figure",
    "algorithm": "algorithm",
    "alg.": "algorithm",
    "box": "box",
    "scheme": "scheme",
    "listing": "listing",
}
_CAPTION_WORDS = {
    "table": "Table",
    "figure": "Figure",
    "algorithm": "Algorithm",
    "box": "Box",
    "scheme": "Scheme",
    "listing": "Listing",
}
_MENTION_WORDS = {
    "table": r"Tab(?:le|\.)s?",
    "figure": r"Fig(?:ure|\.)?s?\.?",
    "algorithm": r"Alg(?:orithm|\.)s?",
    "box": r"Box(?:es)?",
    "scheme": r"Schemes?",
    "listing": r"Listings?",
}
_MENTION_PREFIX = re.compile(
    r"(?:Supplementa(?:ry|l)|Suppl\.?|Extended\s+Data|Online|Appendix)\s+$",
    re.IGNORECASE,
)
_PAGE_NUMBER_EDGE = re.compile(r"^\d+\s+|\s+\d+$")
_PAGE_N = re.compile(r"\bpage\s+\d+(?:\s+of\s+\d+)?\b")
_INTRODUCTION = re.compile(r"^introduction[.:]?$", re.IGNORECASE)


class _Caption(BaseModel):
    kind: str
    number: str
    explicit: bool


def _parse_caption(text: str) -> _Caption | None:
    match = _CAPTION.match(text.strip())
    if match is None:
        return None
    kind = _CAPTION_KINDS[match.group("kind").lower()]
    prefix = " ".join((match.group("prefix") or "").split())
    if prefix:
        prefix = " ".join(word.capitalize() for word in prefix.split()) + " "
    word = ("e" if match.group("e") else "") + _CAPTION_WORDS[kind]
    return _Caption(
        kind=kind,
        number=f"{prefix}{word} {match.group('id')}",
        explicit=match.group("sep") is not None,
    )


def _section_zone(title: str) -> Zone | None:
    """The zone a heading with this (unnumbered) title opens, if the title is
    a standard section name."""
    name = " ".join(title.split())
    # "Methods." and "Funding:" are names; "Supplementary Information ." is
    # the tail of a sentence the layout model took for a heading.
    if name[-1:] in ".:":
        name = name[:-1]
        if name != name.rstrip():
            return None
    for zone, pattern in _SECTION_NAMES:
        if pattern.match(name):
            return zone
    return None


class _Numbering(BaseModel):
    scheme: Literal["decimal", "roman", "letter", "paren"]
    number: str
    depth: int
    title: str


class _Scheme(BaseModel):
    """How a document numbers its headings, as far as it bears on parsing one."""

    roman: bool = False
    bare_letters: frozenset[str] = frozenset()
    # Largest number a top-level section can have: a heading "75 commonly
    # asked questions" in a paper of five numbered sections is not section 75.
    max_section: int = _SECTION_NUMBER_SLACK

    @classmethod
    def of(cls, texts: list[str]) -> _Scheme:
        texts = [" ".join(text.split()) for text in texts]
        # "I." and "V." are letters unless the document also has "II." or "IV.".
        roman = any(
            (match := _ROMAN.match(text)) is not None and len(match.group(1)) > 1
            for text in texts
        )
        sections = {
            match.group(1).split(".")[0]
            for text in texts
            if (match := _DECIMAL.match(text)) is not None
        }
        return cls(
            roman=roman,
            bare_letters=_bare_letter_scheme(texts),
            max_section=len(sections) + _SECTION_NUMBER_SLACK,
        )


def _parse_numbering(text: str, scheme: _Scheme) -> _Numbering | None:
    text = " ".join(text.split())
    match = _DECIMAL.match(text)
    if match is not None and int(match.group(1).split(".")[0]) <= scheme.max_section:
        number = match.group(1)
        return _Numbering(
            scheme="decimal",
            number=number,
            depth=number.count(".") + 1,
            title=text[match.end() :],
        )
    if scheme.roman:
        match = _ROMAN.match(text)
        if match is not None and match.group(1):
            return _Numbering(
                scheme="roman",
                number=match.group(1),
                depth=1,
                title=text[match.end() :],
            )
    match = _LETTER.match(text)
    if match is not None:
        number = match.group(1)
        return _Numbering(
            scheme="letter",
            number=number,
            depth=number.count(".") + 1,
            title=text[match.end() :],
        )
    match = _APPENDIX_LETTER.match(text)
    if match is not None:
        return _Numbering(
            scheme="letter", number=match.group(1), depth=1, title=text[match.end() :]
        )
    match = _BARE_LETTER.match(text)
    if match is not None and match.group(1) in scheme.bare_letters:
        return _Numbering(
            scheme="letter", number=match.group(1), depth=1, title=text[match.end() :]
        )
    match = _PAREN.match(text)
    if match is not None:
        return _Numbering(
            scheme="paren", number=match.group(1), depth=1, title=text[match.end() :]
        )
    return None


def _bare_letter_scheme(texts: list[str]) -> frozenset[str]:
    """Letters that number headings without a dot ("A Implementation
    Details"), accepted when they run from A through at least B."""
    letters = {
        match.group(1)
        for text in texts
        if (match := _BARE_LETTER.match(text)) is not None
    }
    run: set[str] = set()
    for offset in range(26):
        letter = chr(ord("A") + offset)
        if letter not in letters:
            break
        run.add(letter)
    return frozenset(run) if len(run) >= 2 else frozenset()


# --- document helpers ---------------------------------------------------------


def _flow(doc: DoclingDocument) -> list[DocItem]:
    """Every item, all layers, in reading order (a figure's children after it)."""
    return [
        item
        for item, _level in doc.iterate_items(
            traverse_pictures=True, included_content_layers=set(ContentLayer)
        )
        if isinstance(item, DocItem)
    ]


def _floats(doc: DoclingDocument) -> list[FloatingItem]:
    return [item for item in _flow(doc) if isinstance(item, FloatingItem)]


def _inside_floats(doc: DoclingDocument) -> dict[str, str]:
    """``ref -> ref of the table or picture it lies in`` for everything below
    a table or picture other than its captions and footnotes."""
    inside: dict[str, str] = {}
    for holder in (*doc.pictures, *doc.tables):
        own = {ref.cref for ref in (*holder.captions, *holder.footnotes)}
        stack = [ref for ref in holder.children if ref.cref not in own]
        while stack:
            ref = stack.pop()
            if ref.cref in inside:
                continue
            inside[ref.cref] = holder.self_ref
            stack.extend(ref.resolve(doc).children)
    return inside


def _page_of(item: DocItem) -> int | None:
    return item.prov[0].page_no if item.prov else None


def _glyph_size(item: DocItem) -> float | None:
    """Height of a line of the item's text, in points, from its box: the box
    height for one line, and for several the size a box of that area needs
    for that many characters."""
    if not item.prov or not isinstance(item, TextItem):
        return None
    box = item.prov[0].bbox
    height, width = abs(box.t - box.b), abs(box.r - box.l)
    chars = len(item.text.strip())
    if height <= 0 or width <= 0 or not chars:
        return None
    return min(height, math.sqrt(2 * width * height / chars))


def _relative_y(item: DocItem, doc: DoclingDocument) -> float | None:
    """Centre of the item's box as a fraction of the page height, 0 at the
    top."""
    if not item.prov:
        return None
    prov = item.prov[0]
    page = doc.pages.get(prov.page_no)
    if page is None or page.size.height <= 0:
        return None
    box = prov.bbox.to_top_left_origin(page.size.height)
    return ((box.t + box.b) / 2) / page.size.height


def _retype(
    doc: DoclingDocument,
    item: TextItem,
    label: DocItemLabel,
    *,
    content_layer: ContentLayer | None = None,
) -> TextItem:
    """Replace *item* in ``doc.texts`` by an item of *label*'s class with the
    same ``self_ref``, tree position, provenance and text."""
    index = int(item.self_ref.rsplit("/", 1)[1])
    fields = item.model_dump(exclude={"label", "level"})
    fields["label"] = label
    if content_layer is not None:
        fields["content_layer"] = content_layer
    cls: type[TextItem]
    if label == DocItemLabel.SECTION_HEADER:
        cls = SectionHeaderItem
    elif label == DocItemLabel.TITLE:
        cls = TitleItem
    else:
        cls = TextItem
    new = cls.model_validate(fields)
    doc.texts[index] = new
    return new


def _reparent(doc: DoclingDocument, item: NodeItem, parent: NodeItem) -> None:
    if item.parent is not None:
        old = item.parent.resolve(doc)
        old.children = [ref for ref in old.children if ref.cref != item.self_ref]
    parent.children.append(RefItem(cref=item.self_ref))
    item.parent = RefItem(cref=parent.self_ref)


class _Pass:
    """State of one :func:`structure_document` run."""

    def __init__(
        self, doc: DoclingDocument, pdf_path: Path | None, repeat_threshold: int
    ) -> None:
        self.doc = doc
        self.pdf_path = pdf_path
        self.repeat_threshold = repeat_threshold
        self.relabels: dict[str, Relabel] = {}
        self.repeat_counts: dict[str, int] = {}

    def styles(self, items: list[SectionHeaderItem]) -> dict[str, GlyphStyle]:
        """How each heading is printed: read from the PDF when there is one,
        else a size estimated from its box (no weight, no slant)."""
        if self.pdf_path is not None:
            return pdf_text_styles(
                self.pdf_path,
                {item.self_ref: item.prov[0] for item in items if item.prov},
            )
        sizes = {
            item.self_ref: size
            for item in items
            if (size := _glyph_size(item)) is not None
        }
        styles: dict[str, GlyphStyle] = {}
        step_start = 0.0
        for ref, size in sorted(sizes.items(), key=lambda pair: pair[1]):
            if size > _BOX_SIZE_STEP * step_start:
                step_start = size
            styles[ref] = GlyphStyle(size=round(step_start), bold=False, upright=True)
        return styles

    def relabel(
        self,
        item: TextItem,
        label: DocItemLabel,
        rule: str,
        *,
        content_layer: ContentLayer | None = None,
    ) -> TextItem:
        new = _retype(self.doc, item, label, content_layer=content_layer)
        first = self.relabels.get(item.self_ref)
        self.relabels[item.self_ref] = Relabel(
            ref=item.self_ref,
            was=first.was if first is not None else str(item.label.value),
            now=str(label.value),
            rule=rule,
            page=_page_of(item),
            text=item.text[:120],
        )
        return new

    def body_texts(self) -> list[TextItem]:
        """Text items of the body that are not inside a table or figure."""
        inside = _inside_floats(self.doc)
        return [
            item
            for item in _flow(self.doc)
            if isinstance(item, TextItem)
            and item.content_layer == ContentLayer.BODY
            and item.self_ref not in inside
        ]

    # -- furniture -------------------------------------------------------------

    def relabel_furniture(self) -> None:
        groups: dict[tuple[str, bool], list[TextItem]] = defaultdict(list)
        for item in self.body_texts():
            if item.label not in (DocItemLabel.TEXT, DocItemLabel.SECTION_HEADER):
                continue
            text = " ".join(item.text.lower().split())
            if not text or len(text) > _FURNITURE_MAX_CHARS or len(item.prov) != 1:
                continue
            y = _relative_y(item, self.doc)
            if y is None or MARGIN_BAND < y < 1 - MARGIN_BAND:
                continue
            # A page number at either end ("12 Z. Arow et al.") does not make
            # the line a different one; other digits do ("SI.1.2 Example 3").
            key = (
                "#"
                if text.isdigit()
                else _PAGE_N.sub("page #", _PAGE_NUMBER_EDGE.sub("", text))
            )
            groups[key, y <= MARGIN_BAND].append(item)
        for (_key, at_top), items in groups.items():
            pages = {item.prov[0].page_no for item in items}
            if len(pages) < self.repeat_threshold:
                continue
            label = DocItemLabel.PAGE_HEADER if at_top else DocItemLabel.PAGE_FOOTER
            for item in items:
                self.relabel(
                    item,
                    label,
                    RULE_REPEATED_TEXT,
                    content_layer=ContentLayer.FURNITURE,
                )
                self.repeat_counts[item.self_ref] = len(pages)

    # -- captions --------------------------------------------------------------

    def relabel_captions(self) -> None:
        for item in self.body_texts():
            caption = _parse_caption(item.text)
            if caption is None:
                continue
            if item.label == DocItemLabel.SECTION_HEADER or (
                item.label == DocItemLabel.TEXT and caption.explicit
            ):
                self.relabel(item, DocItemLabel.CAPTION, RULE_CAPTION_PATTERN)

    def link_captions(self) -> None:
        """Tie each caption no table or figure owns to the nearest one of its
        kind on its page that has no caption yet."""
        doc = self.doc
        floats = _floats(doc)
        owned = {ref.cref for holder in floats for ref in holder.captions}
        targets: dict[str, tuple[type[FloatingItem], ...]] = {
            "table": (TableItem,),
            "figure": (PictureItem,),
            "algorithm": (CodeItem,),
            "listing": (CodeItem,),
            "box": (TableItem, PictureItem),
            "scheme": (PictureItem, TableItem),
        }
        for item in self.body_texts():
            if item.label != DocItemLabel.CAPTION or item.self_ref in owned:
                continue
            caption = _parse_caption(item.text)
            if caption is None or not item.prov:
                continue
            prov = item.prov[0]
            candidates = [
                holder
                for holder in floats
                if isinstance(holder, targets[caption.kind])
                and holder.content_layer == ContentLayer.BODY
                and not holder.captions
                and holder.prov
                and holder.prov[0].page_no == prov.page_no
            ]
            if not candidates:
                continue
            nearest = min(
                candidates, key=lambda holder: _gap(prov.bbox, holder.prov[0].bbox)
            )
            nearest.captions.append(RefItem(cref=item.self_ref))
            _reparent(doc, item, nearest)

    # -- headings --------------------------------------------------------------

    def promote_section_names(self) -> None:
        for item in self.body_texts():
            if item.label != DocItemLabel.TEXT or len(item.prov) != 1:
                continue
            text = " ".join(item.text.split())
            # "Funding:" is a run-in label whose value the layout split off.
            if _PROMOTABLE.match(text.rstrip(".")) is None:
                continue
            self.relabel(item, DocItemLabel.SECTION_HEADER, RULE_STANDARD_SECTION_NAME)

    def headings(self) -> list[SectionHeaderItem]:
        return [
            item for item in self.body_texts() if isinstance(item, SectionHeaderItem)
        ]

    def pick_title(self) -> TitleItem | None:
        """The paper's title among the headings of the first page: set larger
        than the section headings, at least ``_TITLE_MIN_WORDS`` words, and
        the longest of those in about the largest type (a journal's name is
        set as large and is shorter)."""
        existing = [item for item in self.body_texts() if isinstance(item, TitleItem)]
        if existing:
            return existing[0]
        headings = self.headings()
        scheme = _Scheme.of([h.text for h in headings])
        styles = self.styles(headings)
        sections = [
            styles[h.self_ref].size
            for h in headings
            if _is_anchor(h.text, scheme) and h.self_ref in styles
        ]
        section_size = median(sections) if sections else 0.0
        candidates = [
            heading
            for heading in headings
            if not _is_anchor(heading.text, scheme)
            and len(heading.text.split()) >= _TITLE_MIN_WORDS
            and heading.self_ref in styles
            and styles[heading.self_ref].size > section_size
        ]
        if not candidates:
            return None
        first_page = min(_page_of(heading) or 0 for heading in candidates)
        on_first = [h for h in candidates if (_page_of(h) or 0) == first_page]
        largest = max(styles[h.self_ref].size for h in on_first)
        best = max(
            (
                h
                for h in on_first
                if styles[h.self_ref].size >= _TITLE_SIZE_SHARE * largest
            ),
            key=lambda h: len(h.text),
        )
        title = self.relabel(best, DocItemLabel.TITLE, RULE_TITLE)
        assert isinstance(title, TitleItem)
        return title

    def level_headings(self) -> list[OutlineEntry]:
        headings = self.headings()
        scheme = _Scheme.of([h.text for h in headings])
        styles = self.styles(headings)
        intro = next(
            (
                index
                for index, h in enumerate(headings)
                if _INTRODUCTION.match(_unnumbered(h.text, scheme))
            ),
            None,
        )

        # What each heading's text alone says about it.
        known: dict[str, _Known] = {}
        for index, heading in enumerate(headings):
            number = _parse_numbering(heading.text, scheme)
            title = " ".join(heading.text.split())
            if number is not None and number.scheme != "paren":
                level = number.depth + int(number.scheme == "letter" and scheme.roman)
                zone = (
                    "supplement"
                    if number.scheme == "letter" and not scheme.roman
                    else _section_zone(number.title) or "body"
                )
                known[heading.self_ref] = _Known(
                    level=level, zone=zone, source="numbering", abstract_part=False
                )
            elif number is None and (zone := _section_zone(title)) is not None:
                known[heading.self_ref] = _Known(
                    level=1,
                    zone=zone,
                    source="standard-name",
                    # Before the Introduction, "Methods" and "Results" are the
                    # parts of a structured abstract.
                    abstract_part=zone == "body"
                    and intro is not None
                    and index < intro,
                )

        level_of_style: dict[GlyphStyle, int] = {}
        for heading in headings:
            fact, style = known.get(heading.self_ref), styles.get(heading.self_ref)
            if fact is not None and style is not None and not fact.abstract_part:
                level_of_style[style] = min(
                    fact.level, level_of_style.get(style, _MAX_LEVEL)
                )
        top_styles = Counter(
            styles[h.self_ref]
            for h in headings
            if h.self_ref in styles
            and (fact := known.get(h.self_ref)) is not None
            and fact.level == 1
            and not fact.abstract_part
        )
        top_style = top_styles.most_common(1)[0][0] if top_styles else None
        first_known = next(
            (index for index, h in enumerate(headings) if h.self_ref in known), None
        )
        after = headings[first_known:] if first_known is not None else []
        unknown_styles = {
            styles[h.self_ref]
            for h in after
            if h.self_ref not in known and h.self_ref in styles
        }
        # The document marks levels by type when a sub-heading is set lighter
        # than the sections, or numbered sub-sections are, or sections are
        # numbered at all (a sub-section then is numbered too, so an
        # unnumbered heading set like the sections is one of them). Where
        # every heading is set alike, an unnamed one is taken to be a part of
        # the named section it follows.
        by_type = top_style is not None and (
            any(style < top_style for style in unknown_styles)
            or any(level > 1 for level in level_of_style.values())
            or sum(1 for fact in known.values() if fact.source == "numbering")
            >= _NUMBERED_MIN_HEADINGS
        )
        previous = 0
        for style in sorted(unknown_styles | set(level_of_style), reverse=True):
            previous = (
                max(level_of_style[style], previous)
                if style in level_of_style
                else previous + 1
            )
            level_of_style[style] = previous

        outline: list[OutlineEntry] = []
        stack: list[OutlineEntry] = []
        anchor_level: int | None = None
        zone: Zone = "front-matter" if known else "body"
        for heading in headings:
            fact = known.get(heading.self_ref)
            number = _parse_numbering(heading.text, scheme)
            title = (
                number.title if number is not None else " ".join(heading.text.split())
            )
            style = styles.get(heading.self_ref)
            source: LevelSource
            if fact is not None and fact.abstract_part:
                level = 2 if zone == "abstract" and anchor_level == 1 else 1
                source, zone = fact.source, "abstract"
                anchor_level = anchor_level or level
            elif fact is not None:
                level, source = fact.level, fact.source
                anchor_level = level
                if level == 1:
                    zone = fact.zone
            elif number is not None:
                level, source = (anchor_level or 0) + 1, "numbering"
            elif anchor_level is None:
                level, source = 1, "position"
            elif by_type and style is not None:
                level, source = level_of_style[style], "font-size"
            else:
                level, source = anchor_level + 1, "position"
            if fact is None:
                # No level is skipped on the way down.
                level = min(level, (stack[-1].level if stack else 0) + 1)
                if level == 1 and anchor_level is not None:
                    zone = (
                        "back-matter"
                        if zone in ("reference", "back-matter")
                        else "supplement"
                        if zone == "supplement"
                        else "body"
                    )
            level = min(level, _MAX_LEVEL)

            while stack and stack[-1].level >= level:
                stack.pop()
            entry = OutlineEntry(
                ref=heading.self_ref,
                level=level,
                number=number.number if number is not None else None,
                title=title,
                page=_page_of(heading),
                parent=stack[-1].ref if stack else None,
                path=[*(e.title for e in stack), title],
                level_source=source,
                zone=zone,
            )
            heading.level = level
            stack.append(entry)
            outline.append(entry)
        return outline


class _Known(BaseModel):
    """What a heading's text alone says: it is numbered or carries a
    standard section name."""

    level: int
    zone: Zone
    source: LevelSource
    abstract_part: bool


def _unnumbered(text: str, scheme: _Scheme) -> str:
    number = _parse_numbering(text, scheme)
    return number.title if number is not None else " ".join(text.split())


def _is_anchor(text: str, scheme: _Scheme) -> bool:
    """Whether a heading's level follows from its text alone."""
    number = _parse_numbering(text, scheme)
    if number is not None:
        return number.scheme != "paren"
    return _section_zone(text) is not None


def _gap(a, b) -> float:
    """Vertical distance between two boxes of a page (0 when they overlap)."""
    a_low, a_high = sorted((a.t, a.b))
    b_low, b_high = sorted((b.t, b.b))
    return max(0.0, a_low - b_high, b_low - a_high)


# --- the pass -----------------------------------------------------------------


def structure_document(
    doc: DoclingDocument,
    *,
    pdf_path: Path | None = None,
    document_role: DocumentRole = "manuscript",
    repeat_threshold: int = DEFAULT_FURNITURE_REPEAT_THRESHOLD,
) -> DocumentStructure:
    """Settle labels, heading levels and caption links of *doc* in place and
    return what was decided (see the module docstring).

    With *pdf_path* (the PDF *doc* was converted from) headings are ranked by
    the type they are set in; without it, by the size of their boxes."""
    run = _Pass(doc, pdf_path, repeat_threshold)
    run.relabel_furniture()
    run.relabel_captions()
    run.promote_section_names()
    title = run.pick_title()
    outline = run.level_headings()
    run.link_captions()

    elements = _describe_elements(doc, outline, run)
    structure = DocumentStructure(
        document_role=document_role,
        title_ref=title.self_ref if title is not None else None,
        outline=outline,
        relabels=list(run.relabels.values()),
        elements=elements,
    )
    _log.info(
        "structure: %d sections (max level %d), %d relabelled, title %s",
        len(outline),
        max((entry.level for entry in outline), default=0),
        len(structure.relabels),
        structure.title_ref,
    )
    return structure


def _describe_elements(
    doc: DoclingDocument, outline: list[OutlineEntry], run: _Pass
) -> dict[str, ElementInfo]:
    by_ref = {entry.ref: entry for entry in outline}
    inside = _inside_floats(doc)
    caption_of: dict[str, str] = {}
    footnote_of: dict[str, str] = {}
    numbers: dict[str, _Caption] = {}
    for holder in _floats(doc):
        for ref in holder.captions:
            caption_of[ref.cref] = holder.self_ref
            caption = ref.resolve(doc)
            if holder.self_ref not in numbers and isinstance(caption, TextItem):
                parsed = _parse_caption(caption.text)
                if parsed is not None:
                    numbers[holder.self_ref] = parsed
        for ref in holder.footnotes:
            footnote_of[ref.cref] = holder.self_ref

    anchored = any(e.level_source in ("numbering", "standard-name") for e in outline)
    zone: Zone = "front-matter" if anchored else "body"
    section: str | None = None
    elements: dict[str, ElementInfo] = {}
    for item in _flow(doc):
        ref = item.self_ref
        info = ElementInfo(role=_role(item, zone, inside, caption_of, doc))
        if item.content_layer == ContentLayer.BODY:
            entry = by_ref.get(ref)
            if entry is not None:
                zone, section = entry.zone, ref
                info.level, info.level_source = entry.level, entry.level_source
                info.number, info.parent_ref = entry.number, entry.parent
                info.section_ref = entry.parent
            else:
                info.section_ref = section
        if isinstance(item, FloatingItem):
            if item.captions:
                info.caption_ref = item.captions[0].cref
            if ref in numbers:
                info.number = numbers[ref].number
        elif ref in caption_of:
            info.caption_for = caption_of[ref]
        elif ref in footnote_of:
            info.footnote_for = footnote_of[ref]
        if isinstance(item, TextItem) and item.label == DocItemLabel.CAPTION:
            parsed = _parse_caption(item.text)
            if parsed is not None:
                info.number = parsed.number
        if isinstance(item, ListItem) and item.parent is not None:
            info.parent_ref = item.parent.cref
        relabel = run.relabels.get(ref)
        if relabel is not None:
            info.label_was, info.label_source = relabel.was, relabel.rule
        info.repeat_count = run.repeat_counts.get(ref)
        elements[ref] = info

    for ref, caption in numbers.items():
        mention = _first_mention(doc, caption, elements)
        if mention is not None:
            elements[ref].first_mention_ref = mention
            elements[ref].first_mention_section_ref = elements[mention].section_ref
    return elements


def _role(
    item: DocItem,
    zone: Zone,
    inside: dict[str, str],
    caption_of: dict[str, str],
    doc: DoclingDocument,
) -> str:
    if item.content_layer == ContentLayer.FURNITURE:
        if item.label == DocItemLabel.PAGE_FOOTER:
            return "page-footer"
        return "page-header"
    if item.content_layer == ContentLayer.BACKGROUND:
        return "watermark"
    if item.content_layer != ContentLayer.BODY:
        return str(item.content_layer.value)
    holder_ref = inside.get(item.self_ref)
    if holder_ref is not None:
        holder = RefItem(cref=holder_ref).resolve(doc)
        return "figure-text" if isinstance(holder, PictureItem) else "table-text"
    if isinstance(item, TitleItem):
        return "title"
    if isinstance(item, SectionHeaderItem):
        return "section"
    if isinstance(item, TableItem):
        return "table"
    if isinstance(item, PictureItem):
        return "figure"
    if isinstance(item, CodeItem):
        return "code"
    if isinstance(item, FormulaItem):
        return "formula"
    if isinstance(item, TextItem):
        if item.label == DocItemLabel.CAPTION:
            parsed = _parse_caption(item.text)
            if parsed is not None:
                return f"{parsed.kind}-caption"
            holder_ref = caption_of.get(item.self_ref)
            holder = RefItem(cref=holder_ref).resolve(doc) if holder_ref else None
            if isinstance(holder, TableItem):
                return "table-caption"
            if isinstance(holder, PictureItem):
                return "figure-caption"
            return "caption"
        if item.label == DocItemLabel.FOOTNOTE:
            return "footnote"
        return zone
    return "form"


def _first_mention(
    doc: DoclingDocument, caption: _Caption, elements: dict[str, ElementInfo]
) -> str | None:
    """Ref of the first running-text item that cites *caption*'s number
    ("Fig. 3", "Tables 2")."""
    *prefix, word, ident = caption.number.split()
    kind_word = (
        rf"{re.escape(word)}s?"
        if word != _CAPTION_WORDS[caption.kind]
        else _MENTION_WORDS[caption.kind]
    )
    pattern = re.compile(rf"\b{kind_word}\s*{re.escape(ident)}(?![0-9])", re.IGNORECASE)
    running = {"abstract", "body", "back-matter", "supplement", "front-matter"}
    for ref, info in elements.items():
        if info.role not in running:
            continue
        item = RefItem(cref=ref).resolve(doc)
        if not isinstance(item, TextItem):
            continue
        for match in pattern.finditer(item.text):
            prefixed = _MENTION_PREFIX.search(item.text[: match.start()]) is not None
            if prefixed == bool(prefix):
                return ref
    return None


# --- quality ------------------------------------------------------------------


def quality_report(doc: DoclingDocument) -> QualityReport:
    """Count what *doc* holds and warn about the signs of a conversion gone
    wrong (see :class:`QualityReport`)."""
    inside = _inside_floats(doc)
    pages = len(doc.pages)
    labels: Counter[str] = Counter()
    layers: Counter[str] = Counter()
    per_page: dict[int, Counter[str]] = {no: Counter() for no in sorted(doc.pages)}
    body_texts: list[TextItem] = []
    content_pages: set[int] = set()
    for item in _flow(doc):
        label = str(item.label.value)
        layers[str(item.content_layer.value)] += 1
        labels[label] += 1
        page_nos = {prov.page_no for prov in item.prov}
        for page_no in page_nos:
            per_page.setdefault(page_no, Counter())[label] += 1
        if item.content_layer != ContentLayer.BODY:
            continue
        if isinstance(item, TextItem) and item.self_ref not in inside:
            if item.text.strip():
                body_texts.append(item)
                content_pages.update(page_nos)
        elif isinstance(item, TableItem | PictureItem):
            content_pages.update(page_nos)

    text_pages = {prov.page_no for item in body_texts for prov in item.prov}
    body_chars = sum(len(item.text) for item in body_texts)
    table_chars = sum(
        len(cell.text)
        for table in doc.tables
        if table.content_layer == ContentLayer.BODY
        for cell in table.data.table_cells
    )
    headers = [item for item in body_texts if isinstance(item, SectionHeaderItem)]
    repeated = [
        RepeatedHeading(text=text, count=count)
        for text, count in Counter(
            " ".join(item.text.lower().split()) for item in headers
        ).most_common()
        if count >= DEFAULT_FURNITURE_REPEAT_THRESHOLD
    ]
    share = (
        table_chars / (table_chars + body_chars) if table_chars + body_chars else None
    )
    empty_pages = sorted(set(doc.pages) - content_pages)

    warnings: list[QualityWarning] = []
    if pages and not body_chars and not table_chars:
        warnings.append(
            QualityWarning(
                code="no_body_text",
                blocking=True,
                detail=f"no text in the body or in tables on {pages} pages",
            )
        )
    elif (
        len(body_texts) < MIN_BODY_TEXTS_PER_PAGE * pages
        and body_chars >= PACKED_TEXT_MIN_CHARS_PER_PAGE * pages
    ):
        warnings.append(
            QualityWarning(
                code="few_text_blocks",
                blocking=True,
                detail=(
                    f"{len(body_texts)} body text items on {pages} pages hold "
                    f"{body_chars} characters: the text is packed into a few blocks"
                ),
            )
        )
    if pages > HEADERLESS_MAX_PAGES and not headers:
        warnings.append(
            QualityWarning(
                code="no_headings",
                blocking=False,
                detail=f"no section headers on {pages} pages",
            )
        )
    if repeated:
        warnings.append(
            QualityWarning(
                code="repeated_heading_text",
                blocking=False,
                detail="; ".join(f"{r.text!r} x{r.count}" for r in repeated[:5]),
            )
        )
    if share is not None and share > TABLE_TEXT_SHARE_MAX:
        warnings.append(
            QualityWarning(
                code="text_mostly_in_tables",
                blocking=False,
                detail=f"{share:.0%} of the characters are in table cells",
            )
        )
    if empty_pages:
        warnings.append(
            QualityWarning(
                code="pages_without_content",
                blocking=False,
                detail=(
                    f"{len(empty_pages)} pages with no body text, table or "
                    f"figure: {', '.join(map(str, empty_pages[:20]))}"
                ),
            )
        )
    return QualityReport(
        pages=pages,
        label_counts=dict(sorted(labels.items())),
        layer_counts=dict(sorted(layers.items())),
        page_label_counts={
            no: dict(sorted(counts.items())) for no, counts in per_page.items()
        },
        body_text_items=len(body_texts),
        body_text_chars=body_chars,
        section_headers=len(headers),
        pages_without_text=sorted(set(doc.pages) - text_pages),
        chars_in_tables_share=round(share, 3) if share is not None else None,
        repeated_heading_texts=repeated,
        warnings=warnings,
    )


def text_layer_warnings(
    found: TextLayerSummary, *, ocr_ran: bool
) -> list[QualityWarning]:
    """What a reader of the bundle has to know about pages whose PDF text
    does not say what they print."""
    warnings: list[QualityWarning] = []
    if found.glyph_order_pages:
        warnings.append(
            QualityWarning(
                code="text_layer_decoded",
                blocking=False,
                detail=(
                    f"{len(found.glyph_order_pages)} page(s) hold text in a font "
                    "without a Unicode map, decoded from its glyph numbers: "
                    f"{pages_text(found.glyph_order_pages)}"
                ),
            )
        )
    if found.unreadable_pages:
        pages = pages_text(found.unreadable_pages)
        warnings.append(
            QualityWarning(
                code="text_layer_read_by_ocr",
                blocking=False,
                detail=(
                    f"the text layer of {len(found.unreadable_pages)} page(s) "
                    f"cannot be read; their text is what OCR read: {pages}"
                ),
            )
            if ocr_ran
            else QualityWarning(
                code="text_layer_unreadable",
                blocking=True,
                detail=(
                    f"the text layer of {len(found.unreadable_pages)} page(s) "
                    f"cannot be read and OCR is off: {pages}"
                ),
            )
        )
    if found.partly_unreadable_pages:
        warnings.append(
            QualityWarning(
                code="text_layer_partly_unreadable",
                blocking=False,
                detail="characters in a font the text layer cannot read: "
                + ", ".join(
                    f"p{page.page} {page.share:.0%}"
                    for page in found.partly_unreadable_pages[:12]
                ),
            )
        )
    return warnings


def parser_repair_warnings(found: ParserRepairSummary) -> list[QualityWarning]:
    """What was repaired in the text cells of Docling's PDF parser
    (``docling.utils.parser_repair``)."""
    if not found.respaced_pages:
        return []
    return [
        QualityWarning(
            code="parser_text_repaired",
            blocking=False,
            detail=(
                f"words run together on {len(found.respaced_pages)} page(s), spaced "
                "by the gaps between their glyphs: "
                f"{pages_text(found.respaced_pages)}"
            ),
        )
    ]


# --- bundle file --------------------------------------------------------------


def write_structure(pdf_dir: Path, structure: DocumentStructure) -> Path:
    target = pdf_dir / STRUCTURE_FILENAME
    write_text_atomic(
        target, structure.model_dump_json(indent=2, exclude_none=True) + "\n"
    )
    return target


def read_structure(pdf_dir: Path) -> DocumentStructure | None:
    """The bundle's ``structure.json``; None when it has none (a bundle of an
    earlier release)."""
    path = pdf_dir / STRUCTURE_FILENAME
    if not path.is_file():
        return None
    return DocumentStructure.model_validate_json(path.read_text(encoding="utf-8"))
