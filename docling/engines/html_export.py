# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Standalone ``<stem>.html`` — one file a human can read and an agent can parse.

Docling's own HTML serializer renders the body (headings, lists, tables with
merged cells, captions, formulas, images inlined as data URIs). On top of it
this module adds what the rest of the bundle knows, so the file stands alone:

- every block carries ``id`` / ``data-self-ref`` / ``data-label`` /
  ``data-page`` / ``data-bbox``, so a quote can be cited back to a page region
  and joined against ``document.json`` / ``chunks.jsonl`` by ``self_ref``;
- nothing Docling extracted is left out — unlike the markdown and chunks,
  which drop it as noise: page headers / footers (``data-content-layer``),
  logos and badges (``data-noise``), text inside figures (a collapsed
  ``details.extrct-figure-text`` in the figure) and table footnotes, which
  Docling's serializer skips;
- every block says where it sits (:mod:`docling.engines.structure`): its
  role, the section header it is under, heading level and number, and the
  links between a table or figure and its caption; the title is ``<h1>`` and
  section headers ``<h2>``..``<h6>`` by level;
- figures carry the BiomedCLIP type as data attributes, and model-generated
  metadata is labelled as such (the paper's caption stays the caption);
- a ``<script type="application/json" id="extrct-manifest">`` holds the
  figures / tables / chunks rows, the outline and ``run.json``.
"""

from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from typing import Any

from docling_core.transforms.serializer.base import SerializationResult
from docling_core.transforms.serializer.html import (
    HTMLDocSerializer,
    HTMLMetaSerializer,
    HTMLParams,
)
from docling_core.types.doc import (
    ContentLayer,
    DocItem,
    DocItemLabel,
    DoclingDocument,
    FloatingItem,
    FormulaItem,
    ImageRefMode,
    ListItem,
    PictureItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.document import BaseMeta, ListGroup, NodeItem
from typing_extensions import override

from docling.engines.figure_data.schema import CHART_DATA_META_KEY
from docling.engines.figure_typing import META_KEY, get_figure_type
from docling.engines.picture_filter import PictureNoiseFlag, read_noise_flags
from docling.engines.run_snapshot import engine_provenance
from docling.engines.structure import (
    DocumentStructure,
    ElementInfo,
    read_structure,
    structure_document,
)
from docling.engines.text_repair import TABLE_PDF_TEXT_META_KEY, get_table_pdf_text

_log = logging.getLogger(__name__)

MANIFEST_ID = "extrct-manifest"
MANIFEST_SCHEMA = "extrct.document-html/1"

# The generic picture classifier is unreliable on medical figures (it calls
# ECGs "Line chart"); its label stays in the manifest, not in the visible meta.
# The chart-data record is in the manifest; its table is tabular_chart.
_BLOCKED_META = {"classification", TABLE_PDF_TEXT_META_KEY, CHART_DATA_META_KEY}

_HOW_TO_READ = (
    "Every content block in the body carries id, data-self-ref (same refs as "
    "document.json and chunks.jsonl self_refs), data-label (Docling item "
    "label), data-page and data-bbox. data-page / data-bbox are parallel "
    "lists, one entry per provenance region: pages space-separated, boxes "
    "';'-separated as l,t,r,b in PDF points with a top-left origin "
    "(page sizes in document.pages). Figures add data-figure-type and "
    "data-figure-type-confidence. Captions come from the paper; the "
    "'description' meta (VLM) and 'predicted figure type' (BiomedCLIP) are "
    "model-generated. Everything Docling extracted from the PDF is in the "
    "body: page headers/footers carry data-content-layer='furniture'; logos "
    "and badges carry data-noise (the reason) and match is_noise in figures; "
    "text printed inside a figure (axis labels, diagram boxes, screenshot "
    "text) sits in a details.extrct-figure-text element inside that figure; "
    "table footnotes follow their table in div.extrct-table-notes. A table "
    "whose cells (typed by the table model) miss words printed in its box "
    "has data-cell-text-recall and, in details.extrct-table-pdf-text after "
    "it, the box's text as the PDF text layer has it. A "
    "formula is an image plus, in div.extrct-formula-text, its characters "
    "as printed in the PDF text layer (not LaTeX). Numbered list items "
    "(references '[12]', steps '1.') start with span.extrct-marker. Skip "
    "[data-noise] and [data-content-layer] elements to read only the "
    "paper's running content. figures/tables/chunks are the rows of "
    "figures.jsonl / tables.jsonl (without the html column, which is the "
    "body table) / chunks.jsonl; image_path is relative to the bundle "
    "folder, the images themselves are inlined in the body. run.engine is "
    "the release that converted the PDF; html_written_by the one that wrote "
    "this file (they differ when the HTML was regenerated from a bundle). "
    "Where an element sits (structure.structure_version names the rule set; "
    "the same records are in structure.json): the paper's title is the h1 "
    "with data-role='title'; section headers are h2..h6 with data-level (1 = "
    "main section), data-level-source (numbering | standard-name | font-size "
    "| position: what decided the level), data-number where numbered and "
    "data-parent-ref (the header above). Every element has data-role: title, "
    "front-matter, abstract, section, body, reference, back-matter, "
    "supplement, figure, table, figure-caption, table-caption, "
    "algorithm-caption (box-, scheme-, listing-), figure-text, table-text, "
    "footnote, formula, code, form, page-header, page-footer, watermark. "
    "Body elements have data-section-ref, the self_ref of the innermost "
    "section header they sit under; structure.outline lists the headers "
    "with level, number, title, page, parent, path and zone. A table or "
    "figure has data-number as its caption prints it ('Table 2', 'Figure "
    "S1', 'Supplementary Table 1') and data-caption-ref; the caption has "
    "data-for and the same data-number; a table footnote has data-for. "
    "data-first-mention-ref / data-first-mention-section-ref name the first "
    "running-text element that cites the number and the section it is in: "
    "use them where a manuscript prints its figures after the references. "
    "A list item has data-parent-ref, the id of its list. An element whose "
    "label a rule changed has data-label-was and data-label-source "
    "(rule:repeated-text, a line repeated in the margin of data-repeat-count "
    "pages; rule:caption-pattern; rule:standard-section-name; "
    "rule:largest-heading-on-first-page); structure.relabels lists them. "
    "data-content-layer='background' is text printed across the page (a "
    "watermark). data-document-role='supplement' is on every element of a "
    "supplement, and run.related names its manuscript."
)

# ElementInfo field -> attribute, in the order written.
_STRUCTURE_ATTRS = (
    ("role", "data-role"),
    ("level", "data-level"),
    ("level_source", "data-level-source"),
    ("number", "data-number"),
    ("section_ref", "data-section-ref"),
    ("parent_ref", "data-parent-ref"),
    ("caption_ref", "data-caption-ref"),
    ("caption_for", "data-for"),
    ("footnote_for", "data-for"),
    ("first_mention_ref", "data-first-mention-ref"),
    ("first_mention_section_ref", "data-first-mention-section-ref"),
    ("label_was", "data-label-was"),
    ("label_source", "data-label-source"),
    ("repeat_count", "data-repeat-count"),
)

_EXTRA_CSS = """
.extrct-about { font-size: 0.9em; background: #f4f6f8; border: 1px solid #d8dde3;
  border-radius: 6px; padding: 0.8em 1em; margin-bottom: 2em; }
.extrct-about p { margin: 0.3em 0; }
.extrct-about code { font-size: 0.95em; }
[data-content-layer] { color: #888; font-size: 0.8em; }
details.extrct-outline ol { list-style: none; padding-left: 0; margin: 0.3em 0; }
details.extrct-outline li { margin: 0.1em 0; }
details.extrct-outline li[data-level="2"] { margin-left: 1.5em; }
details.extrct-outline li[data-level="3"] { margin-left: 3em; }
details.extrct-outline li[data-level="4"] { margin-left: 4.5em; }
details.extrct-outline li[data-level="5"] { margin-left: 6em; }
details.extrct-outline li[data-level="6"] { margin-left: 7.5em; }
details.extrct-outline .extrct-page { color: #888; font-size: 0.85em; }
figure[data-noise] { opacity: 0.5; }
figure[data-noise]::before { content: "noise: " attr(data-noise); display: block;
  font-size: 0.75em; color: #a33; }
details.extrct-figure-text { font-size: 0.85em; color: #444; margin-top: 0.4em; }
.extrct-table-notes { font-size: 0.85em; margin-top: 0.3em; }
.extrct-formula-text { font-family: monospace; font-size: 0.85em; color: #555; }
li[data-marker] { list-style-type: none !important; }
"""

_FIRST_TAG_RE = re.compile(r"^\s*<[a-zA-Z][a-zA-Z0-9]*")
_CAPTION_OPEN = '<div class="caption"'
_TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
_FIGURE_CLOSE = "</figure>"
# Markers that are only bullets; numbered markers ("1.", "[12]", "(a)") are
# content — reference numbers are how the text cites the bibliography.
_BULLET_MARKERS = {
    "",
    "-",
    "\u2013",
    "\u2014",
    "\u2022",
    "\u00b7",
    "\u25e6",
    "\u25aa",
    "\u25ab",
    "*",
    "\u25cb",
    "\u25cf",
    "\u25a0",
    "\u25a1",
}


class _AgentMetaSerializer(HTMLMetaSerializer):
    """Label model-generated picture metadata as such."""

    @override
    def serialize(
        self, *, item: NodeItem, doc: DoclingDocument, **kwargs: Any
    ) -> SerializationResult:
        result = super().serialize(item=item, doc=doc, **kwargs)
        text = result.text.replace(
            "<summary>Meta</summary>", "<summary>Model-generated metadata</summary>", 1
        )
        return result.model_copy(update={"text": text})

    @override
    def _serialize_meta_field(self, meta: BaseMeta, name: str) -> str | None:
        if name == META_KEY:
            raw = meta.get_custom_part().get(META_KEY) or {}
            label, conf = raw.get("label"), raw.get("confidence")
            if label is None:
                return None
            value = f"{label} (BiomedCLIP, confidence {conf:.2f})"
            return _meta_div(name, "predicted figure type", value)
        text = super()._serialize_meta_field(meta, name)
        if name == "description" and text:
            text = text.replace(
                ">description:</span>", ">description (VLM-generated):</span>", 1
            )
        if name == "tabular_chart" and meta.tabular_chart is not None:
            # Who read the table and how far to trust it; the note stands
            # alone when the values are held back.
            note = meta.tabular_chart.title
            held_back = meta.tabular_chart.chart_data.num_rows == 0
            parts = [
                _meta_div("figure_data_note", "figure data (read by a model)", note)
                if note
                else "",
                "" if held_back else (text or ""),
            ]
            text = "".join(parts) or None
        return text


class _AgentHTMLSerializer(HTMLDocSerializer):
    """Docling's HTML serializer with provenance attributes, noise marking and
    the figure / table children Docling's serializer leaves out."""

    meta_serializer: HTMLMetaSerializer = _AgentMetaSerializer()
    noise_reasons: dict[str, str] = {}
    structure: DocumentStructure | None = None

    def _attrs(self, item: DocItem) -> dict[str, str]:
        return _element_attrs(item, self.doc, self.structure)

    @override
    def serialize(
        self, *, item: NodeItem | None = None, **kwargs: Any
    ) -> SerializationResult:
        result = super().serialize(item=item, **kwargs)
        if isinstance(item, ListGroup) and result.text.lstrip().startswith("<"):
            # List items point at their list with data-parent-ref.
            text = _with_attrs(
                result.text, {"id": _anchor(item.self_ref)}, inline=False
            )
            return result.model_copy(update={"text": text})
        if not isinstance(item, DocItem):
            return result
        attrs = self._attrs(item)
        if item.self_ref in self.noise_reasons:
            attrs["data-noise"] = self.noise_reasons[item.self_ref]
        marker = item.marker.strip() if isinstance(item, ListItem) else ""
        if marker not in _BULLET_MARKERS:
            attrs["data-marker"] = marker
        text = result.text
        if text:
            inline = bool(kwargs.get("is_inline_scope"))
            text = _with_attrs(text, attrs, inline=inline)
            if "data-marker" in attrs and text.lstrip().startswith("<li"):
                open_end = text.index(">") + 1
                text = (
                    f'{text[:open_end]}<span class="extrct-marker">'
                    f"{html.escape(marker)}</span> {text[open_end:]}"
                )
            if isinstance(item, FormulaItem) and not item.text and item.orig:
                text = _with_formula_text(text, item.orig)
        if isinstance(item, PictureItem | TableItem):
            text = self._with_children(item, text, attrs, **kwargs)
        else:
            if isinstance(item, FloatingItem):
                # A code block is a floating item too: the doc serializer skips
                # its captions/footnotes as "handled by the floating item", and
                # the HTML code serializer then renders neither.
                caption = self.serialize_captions(item=item, tag="div", **kwargs).text
                text = "\n".join(
                    p for p in (text, caption, *self._footnotes(item)) if p
                )
            if isinstance(item, TextItem) and item.children:
                text = self._with_unrendered_children(item, text, **kwargs)
        return result.model_copy(update={"text": text})

    def _footnotes(self, item: FloatingItem) -> list[str]:
        return [
            f"<div{_attr_str(self._attrs(note))}>{html.escape(note.text)}</div>"
            for ref in item.footnotes
            if isinstance(note := ref.resolve(self.doc), TextItem)
        ]

    def _with_unrendered_children(
        self, item: TextItem, text: str, **kwargs: Any
    ) -> str:
        """Children of a text item that the base serializer left out — the
        caption Docling attaches to a code block, for one. List items and
        inline groups render their own children; those are already tagged."""
        kwargs = {**kwargs, "is_inline_scope": False}
        parts: list[str] = []
        for ref in item.children:
            child = ref.resolve(self.doc)
            if _rendered(child, self.doc, text):
                continue
            part = self.serialize(item=child, **kwargs).text
            if part:
                parts.append(part)
        return "\n".join([text, *parts]) if parts else text

    def _with_children(
        self,
        item: PictureItem | TableItem,
        text: str,
        attrs: dict[str, str],
        **kwargs: Any,
    ) -> str:
        """Add what the base serializer never renders for a figure or table:
        its footnotes (the doc serializer skips them as "handled by the
        floating item", but the HTML table/picture serializers don't) and its
        other children — the text Docling found inside a figure."""
        caption_refs = {ref.cref for ref in item.captions}
        footnote_refs = {ref.cref for ref in item.footnotes}
        notes = self._footnotes(item)
        kwargs = {**kwargs, "is_inline_scope": False}
        inner: list[str] = []
        for ref in item.children:
            if ref.cref in caption_refs | footnote_refs:
                continue
            part = self.serialize(item=ref.resolve(self.doc), **kwargs).text
            if part:
                inner.append(part)
        if isinstance(item, TableItem):
            pdf_text = get_table_pdf_text(item)
            if pdf_text is not None:
                inner.append(
                    '<details class="extrct-table-pdf-text"><summary>Text in this '
                    "table's box as printed in the PDF (the table model's cells hold "
                    f"{pdf_text['cell_text_recall']:.0%} of its words)</summary>"
                    f"<pre>{html.escape(pdf_text['text'])}</pre></details>"
                )
            if not notes and not inner:
                return text
            body = "\n".join(notes + inner)
            return f'{text}\n<div class="extrct-table-notes">{body}</div>'
        blocks = "\n".join(notes)
        if inner:
            blocks += (
                '<details class="extrct-figure-text"><summary>Text inside this '
                f"figure ({len(inner)} items, extracted from the PDF)</summary>\n"
                f"{chr(10).join(inner)}</details>"
            )
        if not blocks:
            return text
        if text.endswith(_FIGURE_CLOSE):
            return f"{text[: -len(_FIGURE_CLOSE)]}{blocks}{_FIGURE_CLOSE}"
        return f"<figure{_attr_str(attrs)}>{text}{blocks}{_FIGURE_CLOSE}"

    @override
    def serialize_captions(
        self, item: FloatingItem, tag: str = "figcaption", **kwargs: Any
    ) -> SerializationResult:
        # Captions are rendered inside their figure/table, bypassing serialize();
        # tag each one too, since chunks.jsonl cites captions by self_ref.
        result = super().serialize_captions(item=item, tag=tag, **kwargs)
        captions = [
            cap
            for ref in item.captions
            if isinstance(cap := ref.resolve(self.doc), TextItem)
        ]
        parts = result.text.split(_CAPTION_OPEN)
        if len(parts) != len(captions) + 1:
            return result
        text = parts[0] + "".join(
            _CAPTION_OPEN + _attr_str(self._attrs(cap)) + rest
            for cap, rest in zip(captions, parts[1:], strict=True)
        )
        return result.model_copy(update={"text": text})


def write_document_html(
    doc: DoclingDocument,
    pdf_dir: Path,
    *,
    noise_flags: list[PictureNoiseFlag] | None = None,
    figures_jsonl: Path | None = None,
    tables_jsonl: Path | None = None,
    chunks_jsonl: Path | None = None,
    run: dict[str, Any] | None = None,
    structure: DocumentStructure | None = None,
) -> Path:
    """Write ``<pdf_dir>/<pdf_dir.name>.html`` and return its path.

    The manifest holds the rows of the given ``figures.jsonl`` /
    ``tables.jsonl`` / ``chunks.jsonl`` (None: no rows) and the *run*
    snapshot. Only these are read, not whatever an earlier run left in
    *pdf_dir*; :func:`rebuild_document_html` reads an existing bundle's.
    *structure* is what the structure pass decided about *doc*; without it
    the blocks carry no role, section or link attributes.
    """
    noise_reasons = {
        f.self_ref: f.noise_reason or "unknown"
        for f in noise_flags or []
        if f.is_noise and f.self_ref is not None
    }
    serializer = _AgentHTMLSerializer(
        doc=doc,
        params=HTMLParams(
            image_mode=ImageRefMode.EMBEDDED,
            blocked_meta_names=_BLOCKED_META,
            layers=set(ContentLayer),
        ),
        noise_reasons=noise_reasons,
        structure=structure,
    )
    body_html = serializer.serialize().text

    manifest = _build_manifest(
        doc,
        figures=_read_jsonl(figures_jsonl),
        tables=_read_jsonl(tables_jsonl),
        chunks=_read_jsonl(chunks_jsonl),
        run=run,
        structure=structure,
    )
    title = manifest["document"]["title"] or doc.name
    head_extra = (
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<style>{_EXTRA_CSS}</style>"
        f'<script type="application/json" id="{MANIFEST_ID}">'
        f"{_json_for_script(manifest)}</script>"
    )
    body_html = _TITLE_RE.sub(
        lambda _: f"<title>{html.escape(title)}</title>", body_html, count=1
    )
    # Body first: the manifest inserted into <head> may contain any text.
    body_html = body_html.replace("<body>", f"<body>{_about_header(manifest)}", 1)
    body_html = body_html.replace("</head>", f"{head_extra}</head>", 1)

    target = pdf_dir / f"{pdf_dir.name}.html"
    target.write_text(body_html, encoding="utf-8")
    _log.info("PdfEngine: wrote standalone HTML to %s", target)
    return target


def rebuild_document_html(pdf_dir: Path) -> Path:
    """Regenerate ``<stem>.html`` for an existing bundle, without reconverting.

    A bundle of a release before ``structure.json`` gets the structure pass
    here, on the loaded document only: its HTML then carries roles, levels
    and the relabelling, while its ``document.json`` keeps the labels of the
    conversion (``data-label-was`` says which those were)."""
    doc = DoclingDocument.load_from_json(pdf_dir / "document.json")
    structure = read_structure(pdf_dir) or structure_document(doc)
    run_path = pdf_dir / "run.json"
    return write_document_html(
        doc,
        pdf_dir,
        noise_flags=read_noise_flags(pdf_dir / "figures.jsonl"),
        figures_jsonl=pdf_dir / "figures.jsonl",
        tables_jsonl=pdf_dir / "tables.jsonl",
        chunks_jsonl=pdf_dir / "chunks.jsonl",
        run=(
            json.loads(run_path.read_text(encoding="utf-8"))
            if run_path.exists()
            else None
        ),
        structure=structure,
    )


def _element_attrs(
    item: DocItem, doc: DoclingDocument, structure: DocumentStructure | None = None
) -> dict[str, str]:
    attrs = {
        "id": _anchor(item.self_ref),
        "data-self-ref": item.self_ref,
        "data-label": str(item.label.value),
    }
    if item.content_layer != ContentLayer.BODY:
        attrs["data-content-layer"] = item.content_layer.value
    if item.prov:
        pages, boxes = [], []
        for prov in item.prov:
            page = doc.pages.get(prov.page_no)
            bbox = (
                prov.bbox.to_top_left_origin(page.size.height)
                if page is not None
                else prov.bbox
            )
            pages.append(str(prov.page_no))
            boxes.append(",".join(f"{v:.1f}" for v in bbox.as_tuple()))
        attrs["data-page"] = " ".join(pages)
        attrs["data-bbox"] = ";".join(boxes)
    if isinstance(item, PictureItem):
        prediction = get_figure_type(item)
        if prediction is not None:
            attrs["data-figure-type"] = prediction.label
            attrs["data-figure-type-confidence"] = f"{prediction.confidence:.3f}"
    if isinstance(item, TableItem):
        attrs["data-rows"] = str(item.data.num_rows)
        attrs["data-cols"] = str(item.data.num_cols)
        pdf_text = get_table_pdf_text(item)
        if pdf_text is not None:
            attrs["data-cell-text-recall"] = f"{pdf_text['cell_text_recall']:.3f}"
    if structure is not None:
        attrs.update(_structure_attrs(structure.elements.get(item.self_ref)))
        if structure.document_role != "manuscript":
            attrs["data-document-role"] = structure.document_role
    return attrs


def _structure_attrs(info: ElementInfo | None) -> dict[str, str]:
    if info is None:
        return {}
    return {
        attr: str(value)
        for field, attr in _STRUCTURE_ATTRS
        if (value := getattr(info, field)) is not None
    }


def _rendered(node: NodeItem, doc: DoclingDocument, fragment: str) -> bool:
    """Whether *node* — for a group, every item below it — is tagged in
    *fragment*."""
    if isinstance(node, DocItem):
        return f'data-self-ref="{node.self_ref}"' in fragment
    return all(_rendered(ref.resolve(doc), doc, fragment) for ref in node.children)


def _with_formula_text(fragment: str, orig: str) -> str:
    """Formulas without a decoded LaTeX text render as an image only; add the
    characters the PDF text layer has for them."""
    block = f'<div class="extrct-formula-text">{html.escape(orig)}</div>'
    if fragment.endswith(_FIGURE_CLOSE):
        return f"{fragment[: -len(_FIGURE_CLOSE)]}{block}{_FIGURE_CLOSE}"
    return f"{fragment}{block}"


def _attr_str(attrs: dict[str, str]) -> str:
    return "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in attrs.items())


def _with_attrs(fragment: str, attrs: dict[str, str], *, inline: bool) -> str:
    attr_str = _attr_str(attrs)
    match = _FIRST_TAG_RE.match(fragment)
    if match is not None and not inline:
        return fragment[: match.end()] + attr_str + fragment[match.end() :]
    tag = "span" if inline else "div"
    return f"<{tag}{attr_str}>{fragment}</{tag}>"


def _build_manifest(
    doc: DoclingDocument,
    *,
    figures: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    run: dict[str, Any] | None,
    structure: DocumentStructure | None = None,
) -> dict[str, Any]:
    elements = structure.elements if structure is not None else {}
    for row in figures + tables:
        if row.get("self_ref"):
            row["element_id"] = _anchor(row["self_ref"])
            info = elements.get(row["self_ref"])
            if info is not None:
                row["number"] = info.number
                row["caption_ref"] = info.caption_ref
                row["section_ref"] = info.section_ref
                row["first_mention_ref"] = info.first_mention_ref
    for row in tables:
        row.pop("html", None)
    return {
        "schema": MANIFEST_SCHEMA,
        "how_to_read": _HOW_TO_READ,
        "document": {
            "name": doc.name,
            "title": _document_title(doc),
            "page_count": len(doc.pages),
            "pages": [
                {"page_no": no, "width": p.size.width, "height": p.size.height}
                for no, p in sorted(doc.pages.items())
            ],
        },
        "structure": (
            structure.model_dump(mode="json", exclude={"elements"}, exclude_none=True)
            if structure is not None
            else None
        ),
        "figures": figures,
        "tables": tables,
        "chunks": chunks,
        "run": run,
        "html_written_by": engine_provenance(),
    }


def _about_header(manifest: dict[str, Any]) -> str:
    run = manifest["run"] or {}
    source = (run.get("source") or {}).get("file_name") or manifest["document"]["name"]
    finished = (run.get("timing") or {}).get("finished_at", "")[:16].replace("T", " ")
    core = ((run.get("environment") or {}).get("packages") or {}).get("docling-core")
    engine = run.get("engine") or {}
    config = run.get("engine_config") or {}
    figures = manifest["figures"]
    noise = sum(1 for f in figures if f.get("is_noise"))

    converted = f"converted {finished} UTC" if finished else "converted"
    tools = []
    if engine.get("version"):
        commit = engine.get("git_commit")
        dirty = ", uncommitted changes" if engine.get("git_dirty") else ""
        at = f" @ {commit[:10]}{dirty}" if commit else ""
        tools.append(f"{engine.get('name')} {engine['version']}{at}")
    if core:
        tools.append(f"docling-core {core}")
    by = f" with {html.escape(' · '.join(tools))}" if tools else ""
    writer = manifest.get("html_written_by") or {}
    if (writer.get("version"), writer.get("git_commit")) != (
        engine.get("version"),
        engine.get("git_commit"),
    ):
        commit = writer.get("git_commit")
        at = f" @ {commit[:10]}" if commit else ""
        by += html.escape(
            f"; this HTML written by {writer.get('name')} {writer.get('version')}{at}"
        )
    models = [
        (
            "table structure",
            "Granite-Vision" if config.get("granite_vision_tables") else None,
        ),
        ("figure descriptions", config.get("picture_description")),
        ("figure types", config.get("figure_types")),
    ]
    model_txt = " · ".join(f"{k}: {html.escape(str(v))}" for k, v in models if v)
    lines = [
        f"<p><strong>Source:</strong> {html.escape(str(source))} · "
        f"{manifest['document']['page_count']} pages · {converted}{by}</p>",
        f"<p><strong>Contents:</strong> {len(figures) - noise} figures"
        f"{f' (+ {noise} logos/badges, kept and marked as noise)' if noise else ''} · "
        f"{len(manifest['tables'])} tables · {len(manifest['chunks'])} chunks</p>",
    ]
    if model_txt:
        lines.append(f"<p><strong>Models:</strong> {model_txt}</p>")
    outline = (manifest.get("structure") or {}).get("outline") or []
    if outline:
        entries = "".join(
            f'<li data-level="{entry["level"]}">'
            f'<a href="#{_anchor(entry["ref"])}">'
            f"{html.escape(' '.join(filter(None, (entry.get('number'), entry['title']))))}"
            f'</a> <span class="extrct-page">p{entry.get("page", "?")}</span></li>'
            for entry in outline
        )
        lines.append(
            f'<details class="extrct-outline"><summary><strong>Outline:</strong> '
            f"{len(outline)} sections</summary><ol>{entries}</ol></details>"
        )
    lines.append(
        "<p><strong>For agents:</strong> JSON manifest in "
        f'<code>&lt;script id="{MANIFEST_ID}"&gt;</code> (figures, tables, chunks, '
        "outline, run metadata, how_to_read). Each block has <code>id</code>, "
        "<code>data-self-ref</code>, <code>data-page</code>, "
        "<code>data-bbox</code>, <code>data-role</code> and "
        "<code>data-section-ref</code> (the section header it is under). "
        "Captions are the paper's; descriptions and figure types are "
        "model-generated.</p>"
    )
    return f'<header class="extrct-about">{"".join(lines)}</header>'


def _document_title(doc: DoclingDocument) -> str | None:
    """The layout model's title, if it found one; no guessing from headers
    (the first section header is often the journal name)."""
    for item, _level in doc.iterate_items():
        if (
            isinstance(item, TextItem)
            and item.label == DocItemLabel.TITLE
            and item.text
        ):
            return item.text
    return None


def _anchor(self_ref: str) -> str:
    return self_ref.lstrip("#/").replace("/", "-")


def _meta_div(name: str, label: str, value: str) -> str:
    return (
        f'<div class="docling-meta-field" data-meta-name="{html.escape(name, quote=True)}">'
        f'<span class="docling-meta-field-label">{html.escape(label)}:</span> '
        f'<span class="docling-meta-field-value">{html.escape(value)}</span></div>'
    )


def _json_for_script(data: dict[str, Any]) -> str:
    # "</" would end the <script> element early; "<\/" is the same JSON string.
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
