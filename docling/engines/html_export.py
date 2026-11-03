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
- figures carry the BiomedCLIP type as data attributes, and model-generated
  metadata is labelled as such (the paper's caption stays the caption);
- a ``<script type="application/json" id="extrct-manifest">`` holds the
  figures / tables / chunks rows and ``run.json``.
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
from docling_core.types.doc.document import BaseMeta, NodeItem
from typing_extensions import override

from docling.engines.figure_typing import META_KEY, get_figure_type
from docling.engines.picture_filter import PictureNoiseFlag

_log = logging.getLogger(__name__)

MANIFEST_ID = "extrct-manifest"
MANIFEST_SCHEMA = "extrct.document-html/1"

# The generic picture classifier is unreliable on medical figures (it calls
# ECGs "Line chart"); its label stays in the manifest, not in the visible meta.
_BLOCKED_META = {"classification"}

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
    "table footnotes follow their table in div.extrct-table-notes. A "
    "formula is an image plus, in div.extrct-formula-text, its characters "
    "as printed in the PDF text layer (not LaTeX). Numbered list items "
    "(references '[12]', steps '1.') start with span.extrct-marker. Skip "
    "[data-noise] and [data-content-layer] elements to read only the "
    "paper's running content. figures/tables/chunks are the rows of "
    "figures.jsonl / tables.jsonl (without the html column, which is the "
    "body table) / chunks.jsonl; image_path is relative to the bundle "
    "folder, the images themselves are inlined in the body."
)

_EXTRA_CSS = """
.extrct-about { font-size: 0.9em; background: #f4f6f8; border: 1px solid #d8dde3;
  border-radius: 6px; padding: 0.8em 1em; margin-bottom: 2em; }
.extrct-about p { margin: 0.3em 0; }
.extrct-about code { font-size: 0.95em; }
[data-content-layer] { color: #888; font-size: 0.8em; }
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
        return text


class _AgentHTMLSerializer(HTMLDocSerializer):
    """Docling's HTML serializer with provenance attributes, noise marking and
    the figure / table children Docling's serializer leaves out."""

    meta_serializer: HTMLMetaSerializer = _AgentMetaSerializer()
    noise_reasons: dict[str, str] = {}

    @override
    def serialize(
        self, *, item: NodeItem | None = None, **kwargs: Any
    ) -> SerializationResult:
        result = super().serialize(item=item, **kwargs)
        if not isinstance(item, DocItem):
            return result
        attrs = _element_attrs(item, self.doc)
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
        return result.model_copy(update={"text": text})

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
        notes = [
            f"<div{_attr_str(_element_attrs(note, self.doc))}>"
            f"{html.escape(note.text)}</div>"
            for ref in item.footnotes
            if isinstance(note := ref.resolve(self.doc), TextItem)
        ]
        kwargs = {**kwargs, "is_inline_scope": False}
        inner = [
            part
            for ref in item.children
            if ref.cref not in caption_refs | footnote_refs
            and (part := self.serialize(item=ref.resolve(self.doc), **kwargs).text)
        ]
        if isinstance(item, TableItem):
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
            _CAPTION_OPEN + _attr_str(_element_attrs(cap, self.doc)) + rest
            for cap, rest in zip(captions, parts[1:], strict=True)
        )
        return result.model_copy(update={"text": text})


def write_document_html(
    doc: DoclingDocument,
    pdf_dir: Path,
    *,
    noise_flags: list[PictureNoiseFlag] | None = None,
) -> Path:
    """Write ``<pdf_dir>/<pdf_dir.name>.html`` and return its path.

    Reads the sidecars already in *pdf_dir* (``figures.jsonl``,
    ``tables.jsonl``, ``chunks.jsonl``, ``run.json``) for the manifest; any
    that are missing are simply left out.
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
    )
    body_html = serializer.serialize().text

    manifest = _build_manifest(doc, pdf_dir)
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
    """Regenerate ``<stem>.html`` for an existing bundle, without reconverting."""
    doc = DoclingDocument.load_from_json(pdf_dir / "document.json")
    noise_flags = [
        PictureNoiseFlag(
            self_ref=row.get("self_ref"),
            is_noise=bool(row.get("is_noise")),
            noise_reason=row.get("noise_reason"),
            classifier_label=row.get("generic_classifier_label"),
        )
        for row in _read_jsonl(pdf_dir / "figures.jsonl")
    ]
    return write_document_html(doc, pdf_dir, noise_flags=noise_flags)


def _element_attrs(item: DocItem, doc: DoclingDocument) -> dict[str, str]:
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
    return attrs


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


def _build_manifest(doc: DoclingDocument, pdf_dir: Path) -> dict[str, Any]:
    figures = _read_jsonl(pdf_dir / "figures.jsonl")
    tables = _read_jsonl(pdf_dir / "tables.jsonl")
    chunks = _read_jsonl(pdf_dir / "chunks.jsonl")
    for row in figures + tables:
        if row.get("self_ref"):
            row["element_id"] = _anchor(row["self_ref"])
    for row in tables:
        row.pop("html", None)
    run_path = pdf_dir / "run.json"
    run = (
        json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else None
    )
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
        "figures": figures,
        "tables": tables,
        "chunks": chunks,
        "run": run,
    }


def _about_header(manifest: dict[str, Any]) -> str:
    run = manifest["run"] or {}
    source = (run.get("source") or {}).get("file_name") or manifest["document"]["name"]
    finished = (run.get("timing") or {}).get("finished_at", "")[:16].replace("T", " ")
    core = ((run.get("environment") or {}).get("packages") or {}).get("docling-core")
    config = run.get("engine_config") or {}
    figures = manifest["figures"]
    noise = sum(1 for f in figures if f.get("is_noise"))

    converted = f"converted {finished} UTC" if finished else "converted"
    by = f" with docling-core {core}" if core else ""
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
    lines.append(
        "<p><strong>For agents:</strong> JSON manifest in "
        f'<code>&lt;script id="{MANIFEST_ID}"&gt;</code> (figures, tables, chunks, '
        "run metadata, how_to_read). Each block has <code>id</code>, "
        "<code>data-self-ref</code>, <code>data-page</code>, "
        "<code>data-bbox</code>. Captions are the paper's; descriptions and "
        "figure types are model-generated.</p>"
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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
