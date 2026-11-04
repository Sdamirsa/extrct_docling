# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""HTML bounding-box viewer for :class:`PdfEngine` results.

Produces a single ``preview.html`` (plus one PNG per page) showing each page
image with absolutely-positioned overlays — one per :class:`DocItem` from
:meth:`DoclingDocument.iterate_items`.

UI:

* Top header carries summary stats (pages, figures, tables, chunks).
* Hover shows the node's label as a small tag.
* Click any bbox to open the side panel — formatted for **the kind of
  node**: pictures show caption + figure type + VLM description + generic
  classifier label + image thumbnail; tables show caption + dimensions + the rendered HTML
  table; text shows the heading path + body text. Raw JSON is available
  via a collapsible "Show raw" toggle.
* Noise-flagged pictures (journal logos, repeated banners) render with a
  dashed gray border and a ``noise`` badge so a reviewer can spot them
  at a glance.
"""

from __future__ import annotations

import base64
import html
import io
import json
import logging
import re
from pathlib import Path
from typing import Literal

from docling_core.types.doc import PictureItem, TableItem

from docling.datamodel.base_models import ConversionStatus, Page
from docling.datamodel.document import ConversionResult
from docling.engines.artifacts import crop_stem
from docling.engines.figure_typing import get_figure_type
from docling.engines.picture_filter import PictureNoiseFlag

_log = logging.getLogger(__name__)

LABEL_COLOURS: dict[str, str] = {
    "title": "#d62728",
    "section_header": "#ff7f0e",
    "text": "#1f77b4",
    "paragraph": "#1f77b4",
    "list_item": "#17becf",
    "caption": "#9467bd",
    "footnote": "#8c564b",
    "page_header": "#7f7f7f",
    "page_footer": "#7f7f7f",
    "table": "#2ca02c",
    "picture": "#e377c2",
    "chart": "#bcbd22",
    "formula": "#bcbd22",
    "code": "#e377c2",
    "reference": "#17becf",
}
LABEL_DEFAULT = "#888888"


class PreviewError(RuntimeError):
    """Raised when the viewer cannot produce a preview."""


def render_html_preview(
    result: ConversionResult,
    target_dir: Path,
    *,
    image_scale: float = 1.5,
    page_image_subdir: str = "images",
    noise_flags: list[PictureNoiseFlag] | None = None,
    chunks_jsonl: Path | None = None,
) -> Path:
    """Render an HTML viewer for *result* into *target_dir*."""
    if result.status not in {
        ConversionStatus.SUCCESS,
        ConversionStatus.PARTIAL_SUCCESS,
    }:
        raise PreviewError(
            f"Cannot render preview from conversion with status {result.status}"
        )
    if not result.pages:
        raise PreviewError("Cannot render preview: result has no pages.")
    if result.document is None:
        raise PreviewError("Cannot render preview: result has no document.")

    target_dir.mkdir(parents=True, exist_ok=True)
    images_dir = target_dir / page_image_subdir
    images_dir.mkdir(exist_ok=True)

    noise_by_self_ref: dict[str, PictureNoiseFlag] = {}
    for flag in noise_flags or []:
        if flag.self_ref:
            noise_by_self_ref[flag.self_ref] = flag

    counters = {"picture": 0, "table": 0}
    indexed = _index_items_by_page(result, noise_by_self_ref, counters, target_dir)

    noise_count = sum(flag.is_noise for flag in noise_by_self_ref.values())
    summary = _summary_block(result, indexed, noise_count, chunks_jsonl)

    page_blocks: list[str] = []
    for page in result.pages:
        page_block = _render_page_block(
            page,
            indexed.get(page.page_no, []),
            images_dir,
            image_scale=image_scale,
        )
        if page_block is not None:
            page_blocks.append(page_block)

    if not page_blocks:
        raise PreviewError(
            "No page images were rendered. Build PdfEngine with with_page_images=True."
        )

    html_doc = _HTML_TEMPLATE.format(
        title=html.escape(result.input.file.name if result.input else "preview"),
        summary=summary,
        legend=_render_legend(),
        pages="\n".join(page_blocks),
    )

    target = target_dir / "preview.html"
    target.write_text(html_doc, encoding="utf-8")
    _log.info("Wrote HTML preview to %s", target)
    return target


_IMAGE_REF = re.compile(r"images/[A-Za-z0-9_.-]+\.png")


def embed_html_images(preview_html: Path, *, page_jpeg_quality: int = 80) -> Path:
    """Write ``preview.embedded.html`` — *preview_html* with every
    ``images/*.png`` reference inlined as a data URI, so the file works on
    its own. Page renders are re-encoded as JPEG to keep the size shareable;
    figure/table crops stay lossless PNG.
    """
    from PIL import Image

    base_dir = preview_html.parent
    cache: dict[str, str] = {}

    def _data_uri(rel: str) -> str:
        if rel not in cache:
            path = base_dir / rel
            if not path.exists():
                cache[rel] = rel
            elif Path(rel).name.startswith("page_"):
                buf = io.BytesIO()
                with Image.open(path) as img:
                    img.convert("RGB").save(
                        buf, format="JPEG", quality=page_jpeg_quality, optimize=True
                    )
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                cache[rel] = f"data:image/jpeg;base64,{encoded}"
            else:
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                cache[rel] = f"data:image/png;base64,{encoded}"
        return cache[rel]

    html_doc = preview_html.read_text(encoding="utf-8")
    embedded = _IMAGE_REF.sub(lambda m: _data_uri(m.group(0)), html_doc)
    target = base_dir / "preview.embedded.html"
    target.write_text(embedded, encoding="utf-8")
    _log.info("Wrote standalone HTML preview to %s", target)
    return target


def _summary_block(
    result: ConversionResult,
    indexed: dict[int, list[tuple]],
    noise_count: int,
    chunks_jsonl: Path | None,
) -> str:
    pages = len(result.pages)
    pictures = sum(
        1 for ents in indexed.values() for e in ents if e[4]["kind"] == "picture"
    )
    tables = sum(
        1 for ents in indexed.values() for e in ents if e[4]["kind"] == "table"
    )
    chunks = 0
    if chunks_jsonl is not None and chunks_jsonl.exists():
        with chunks_jsonl.open(encoding="utf-8") as fh:
            chunks = sum(1 for _ in fh)

    chips = [
        f'<span class="chip">{pages}<small>pages</small></span>',
        f'<span class="chip chip-picture">{pictures}<small>figures</small></span>',
        f'<span class="chip chip-table">{tables}<small>tables</small></span>',
        f'<span class="chip chip-chunk">{chunks}<small>chunks</small></span>',
    ]
    if noise_count:
        chips.append(
            f'<span class="chip chip-noise">{noise_count}<small>noise</small></span>'
        )
    return f'<div class="summary">{"".join(chips)}</div>'


def _index_items_by_page(
    result: ConversionResult,
    noise_by_self_ref: dict[str, PictureNoiseFlag],
    counters: dict[str, int],
    pdf_dir: Path,
) -> dict[int, list[tuple]]:
    by_page: dict[int, list[tuple]] = {}
    for item, level in result.document.iterate_items():
        display = _display_metadata(
            item, result.document, noise_by_self_ref, counters, pdf_dir
        )
        prov_list = getattr(item, "prov", None) or []
        for prov_idx, prov in enumerate(prov_list):
            by_page.setdefault(prov.page_no, []).append(
                (item, level, prov_idx, prov, display)
            )
    return by_page


def _display_metadata(
    item,
    doc,
    noise_by_self_ref: dict[str, PictureNoiseFlag],
    counters: dict[str, int],
    pdf_dir: Path,
) -> dict:
    """Compute the data the side-panel renders for this item."""
    kind = (
        "picture"
        if isinstance(item, PictureItem)
        else "table"
        if isinstance(item, TableItem)
        else "text"
    )
    label = item.label.value if hasattr(item.label, "value") else str(item.label)
    self_ref = getattr(item, "self_ref", "") or ""
    raw = item.model_dump(mode="json", exclude={"image"})

    info: dict = {
        "kind": kind,
        "label": label,
        "self_ref": self_ref,
        "raw": raw,
    }

    if kind == "picture":
        crop = _crop_path(pdf_dir, "picture", counters)
        flag = noise_by_self_ref.get(self_ref)
        figure_type = get_figure_type(item)
        info.update(
            {
                "image_path": crop,
                "caption_text": _caption_text(item, doc),
                "figure_type": figure_type.label if figure_type else None,
                "figure_type_confidence": (
                    figure_type.confidence if figure_type else None
                ),
                "vlm_caption": _picture_vlm_caption(item),
                "generic_classifier_label": _picture_classifier_label(item),
                "is_noise": bool(getattr(flag, "is_noise", False)),
                "noise_reason": getattr(flag, "noise_reason", None),
            }
        )
    elif kind == "table":
        crop = _crop_path(pdf_dir, "table", counters)
        try:
            table_html = item.export_to_html(doc=doc, add_caption=False)
        except Exception:
            table_html = None
        data = item.data
        info.update(
            {
                "image_path": crop,
                "caption_text": _caption_text(item, doc),
                "num_rows": data.num_rows if data is not None else 0,
                "num_cols": data.num_cols if data is not None else 0,
                "table_html": table_html,
            }
        )
    else:
        info.update(
            {
                "text": getattr(item, "text", "") or "",
            }
        )
    return info


def _crop_path(
    pdf_dir: Path, kind: Literal["picture", "table"], counters: dict[str, int]
) -> str | None:
    """The item's crop as written by the artifacts writer, or None when it has
    none (no image, or artifacts not saved)."""
    rel = f"images/{crop_stem(kind, counters[kind])}.png"
    counters[kind] += 1
    return rel if (pdf_dir / rel).is_file() else None


def _caption_text(item, doc) -> str:
    if hasattr(item, "caption_text"):
        try:
            return item.caption_text(doc) or ""
        except Exception:
            return ""
    return ""


def _picture_vlm_caption(item) -> str | None:
    for ann in getattr(item, "annotations", None) or []:
        text = getattr(ann, "text", None)
        kind = (getattr(ann, "kind", None) or type(ann).__name__).lower()
        if text and "description" in kind:
            return text
    for ann in getattr(item, "annotations", None) or []:
        text = getattr(ann, "text", None)
        if text:
            return text
    return None


def _picture_classifier_label(item) -> str | None:
    for ann in getattr(item, "annotations", None) or []:
        kind = (getattr(ann, "kind", None) or type(ann).__name__).lower()
        if "classification" in kind or "classifier" in kind:
            preds = getattr(ann, "predicted_classes", None) or getattr(
                ann, "predictions", None
            )
            if preds:
                first = preds[0]
                return getattr(first, "class_name", None) or getattr(
                    first, "label", None
                )
    return None


def _render_page_block(
    page: Page,
    page_items: list[tuple],
    images_dir: Path,
    *,
    image_scale: float,
) -> str | None:
    image = page.get_image(scale=image_scale)
    if image is None or page.size is None:
        _log.warning(
            "Skipping page %s: no rendered image (set generate_page_images=True).",
            page.page_no,
        )
        return None

    image_path = images_dir / f"page_{page.page_no:04d}.png"
    image.save(image_path, format="PNG")

    overlays = "\n".join(
        _render_overlay(
            item,
            level,
            prov_idx,
            prov,
            display,
            page_height=page.size.height,
            image_scale=image_scale,
        )
        for (item, level, prov_idx, prov, display) in page_items
    )

    rel_image = image_path.relative_to(images_dir.parent).as_posix()
    img_w = int(page.size.width * image_scale)
    img_h = int(page.size.height * image_scale)

    return _PAGE_TEMPLATE.format(
        page_no=page.page_no,
        item_count=len(page_items),
        image_src=html.escape(rel_image),
        img_w=img_w,
        img_h=img_h,
        overlays=overlays,
    )


def _render_overlay(
    item,
    level: int,
    prov_idx: int,
    prov,
    display: dict,
    *,
    page_height: float,
    image_scale: float,
) -> str:
    tl = prov.bbox.to_top_left_origin(page_height=page_height)
    left = tl.l * image_scale
    top = tl.t * image_scale
    width = (tl.r - tl.l) * image_scale
    height = (tl.b - tl.t) * image_scale

    label_value = display["label"]
    colour = LABEL_COLOURS.get(label_value, LABEL_DEFAULT)

    payload = {**display, "_level": level, "_prov_index": prov_idx}
    payload_json = html.escape(json.dumps(payload, ensure_ascii=False))

    css_classes = ["bbox"]
    if display.get("is_noise"):
        css_classes.append("bbox-noise")
    noise_badge = (
        '<span class="bbox-noise-badge">noise</span>' if display.get("is_noise") else ""
    )
    class_attr = " ".join(css_classes)

    return (
        f'<div class="{class_attr}" data-label="{html.escape(label_value)}" '
        f'data-self-ref="{html.escape(display["self_ref"])}" '
        f'data-payload="{payload_json}" '
        f'style="left:{left:.1f}px; top:{top:.1f}px; '
        f"width:{width:.1f}px; height:{height:.1f}px; "
        f'border-color:{colour}; background-color:{colour}22;">'
        f'<span class="bbox-tag" style="background:{colour};">{html.escape(label_value)}</span>'
        f"{noise_badge}"
        f"</div>"
    )


def _render_legend() -> str:
    items = "".join(
        f'<span class="legend-item"><span class="legend-swatch" '
        f'style="background:{colour};"></span>{html.escape(label)}</span>'
        for label, colour in LABEL_COLOURS.items()
    )
    return f'<div class="legend">{items}</div>'


_PAGE_TEMPLATE = """
<section class="page" id="page-{page_no}">
  <h2>Page {page_no} <small>({item_count} nodes)</small></h2>
  <div class="page-canvas" style="width:{img_w}px; height:{img_h}px;">
    <img src="{image_src}" width="{img_w}" height="{img_h}" alt="page {page_no}"/>
    {overlays}
  </div>
</section>
""".strip()


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Docling preview — {title}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0; padding: 0; background: #f3f3f4; color: #222;
  }}
  header {{
    position: sticky; top: 0; background: #fff; border-bottom: 1px solid #ddd;
    padding: 12px 20px; z-index: 10;
  }}
  header h1 {{ margin: 0; font-size: 16px; font-weight: 600; }}
  header .hint {{ color: #777; font-size: 12px; margin-top: 4px; }}
  .summary {{ display: flex; gap: 12px; margin-top: 8px; flex-wrap: wrap; }}
  .chip {{
    display: inline-flex; align-items: baseline; gap: 4px;
    padding: 4px 10px; border-radius: 12px; background: #eef0f3;
    font-size: 13px; font-weight: 600;
  }}
  .chip small {{ font-weight: 400; color: #666; font-size: 11px; }}
  .chip-picture {{ background: #fce4ec; }}
  .chip-table {{ background: #e8f5e9; }}
  .chip-chunk {{ background: #e3f2fd; }}
  .chip-noise {{ background: #f5f5f5; color: #888; }}
  .legend {{ margin-top: 8px; font-size: 12px; display: flex; flex-wrap: wrap; gap: 12px; }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 4px; }}
  .legend-swatch {{
    display: inline-block; width: 12px; height: 12px; border-radius: 2px;
  }}
  main {{ padding: 20px; padding-right: 480px; }}
  section.page {{
    background: #fff; margin: 0 auto 32px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 4px; width: max-content;
  }}
  section.page h2 {{
    margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #444;
  }}
  section.page h2 small {{ font-weight: 400; color: #888; margin-left: 8px; }}
  .page-canvas {{ position: relative; }}
  .page-canvas img {{ display: block; user-select: none; }}
  .bbox {{
    position: absolute; border: 2px solid; box-sizing: border-box;
    pointer-events: auto; cursor: pointer; transition: background-color 0.1s;
  }}
  .bbox:hover {{ background-color: rgba(255, 230, 0, 0.35) !important; z-index: 5; }}
  .bbox.selected {{
    background-color: rgba(255, 200, 0, 0.55) !important;
    z-index: 6; outline: 2px solid #000;
  }}
  .bbox.bbox-noise {{
    border-style: dashed !important; border-color: #888 !important;
    background-color: rgba(150, 150, 150, 0.06) !important; opacity: 0.85;
  }}
  .bbox-tag {{
    position: absolute; top: -16px; left: -2px; padding: 1px 4px;
    color: #fff; font-size: 9px; font-weight: 600;
    border-radius: 2px 2px 0 0; white-space: nowrap; opacity: 0.85;
    pointer-events: none;
  }}
  .bbox-noise-badge {{
    position: absolute; bottom: -14px; right: -2px; padding: 1px 4px;
    color: #555; background: #fff; border: 1px solid #aaa;
    font-size: 9px; font-weight: 600; border-radius: 2px;
    pointer-events: none;
  }}
  .bbox.cited {{
    outline: 3px solid #e33; outline-offset: 1px;
    background-color: rgba(227, 51, 51, 0.25) !important; z-index: 4;
  }}
  .citation-link {{
    display: block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px; word-break: break-all; background: #f7f7f7;
    padding: 4px 6px; border-radius: 2px; user-select: all;
  }}
  #panel {{
    position: fixed; top: 0; right: 0; width: 460px; height: 100vh;
    background: #fff; border-left: 1px solid #ddd; box-shadow: -2px 0 6px rgba(0,0,0,0.05);
    display: flex; flex-direction: column; z-index: 20;
  }}
  #panel-header {{
    padding: 12px 16px; background: #fafafa;
    border-bottom: 1px solid #eee; flex-shrink: 0;
  }}
  #panel-header h2 {{ margin: 0; font-size: 14px; font-weight: 600; color: #333; }}
  #panel-header .self-ref {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px; color: #666; margin-top: 2px;
  }}
  #panel-body {{
    flex: 1; overflow: auto; padding: 12px 16px;
    font-size: 13px; line-height: 1.5;
  }}
  #panel-empty {{ color: #888; font-style: italic; }}
  #panel-close {{
    float: right; border: 0; background: transparent; cursor: pointer;
    color: #888; font-size: 16px; padding: 0; margin-left: 8px;
  }}
  #panel-close:hover {{ color: #222; }}
  .panel-field {{ margin-bottom: 10px; }}
  .panel-field-label {{
    font-size: 11px; font-weight: 600; color: #666;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;
  }}
  .panel-field-value {{ word-break: break-word; }}
  .panel-thumbnail {{
    max-width: 100%; max-height: 240px; border: 1px solid #eee;
    border-radius: 2px; margin-top: 4px;
  }}
  .panel-noise-banner {{
    background: #fff8e1; border: 1px solid #f1c40f; color: #7a5b00;
    padding: 6px 10px; border-radius: 4px; font-size: 12px; margin-bottom: 12px;
  }}
  .panel-table {{
    max-width: 100%; overflow: auto; border: 1px solid #eee;
    border-radius: 2px; padding: 4px; background: #fafafa; font-size: 12px;
  }}
  .panel-table table {{ border-collapse: collapse; }}
  .panel-table td, .panel-table th {{
    border: 1px solid #ddd; padding: 2px 4px;
  }}
  details.panel-raw {{ margin-top: 14px; color: #666; font-size: 12px; }}
  details.panel-raw summary {{ cursor: pointer; }}
  details.panel-raw pre {{
    background: #f7f7f7; border: 1px solid #eee; padding: 8px;
    border-radius: 2px; overflow: auto; max-height: 300px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px;
  }}
</style>
</head>
<body>
<header>
  <h1>Docling preview — {title}</h1>
  <div class="hint">Click any bounding box to inspect node metadata. Dashed boxes are filtered as noise. Append <code>?ref=self_ref[,self_ref...]</code> to this page's URL (values from <code>chunks.jsonl</code> / <code>nodes.jsonl</code>, e.g. <code>#/texts/12</code>) to jump to and highlight cited evidence.</div>
  {summary}
  {legend}
</header>
<main>
{pages}
</main>
<aside id="panel">
  <div id="panel-header">
    <button id="panel-close" title="Clear selection">&times;</button>
    <h2 id="panel-title">Node inspector</h2>
    <div class="self-ref" id="panel-self-ref"></div>
  </div>
  <div id="panel-body">
    <span id="panel-empty">Click a bounding box to see this node's data here.</span>
  </div>
</aside>
<script>
(function() {{
  const panelTitle = document.getElementById('panel-title');
  const panelSelfRef = document.getElementById('panel-self-ref');
  const panelBody = document.getElementById('panel-body');
  const panelClose = document.getElementById('panel-close');
  let selected = null;

  function clearSelection() {{
    if (selected) selected.classList.remove('selected');
    selected = null;
    panelTitle.textContent = 'Node inspector';
    panelSelfRef.textContent = '';
    panelBody.innerHTML = '<span id="panel-empty">Click a bounding box to see this node\\'s data here.</span>';
  }}

  function field(label, value, opts) {{
    if (value === null || value === undefined || value === '') return '';
    opts = opts || {{}};
    const safe = opts.raw ? value : escapeHtml(String(value));
    return '<div class="panel-field"><div class="panel-field-label">' +
      escapeHtml(label) + '</div><div class="panel-field-value">' + safe + '</div></div>';
  }}

  function escapeHtml(s) {{
    return s.replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
  }}

  function renderPicture(data) {{
    let html = '';
    if (data.is_noise) {{
      html += '<div class="panel-noise-banner">⚠ Flagged as noise: ' +
        escapeHtml(data.noise_reason || 'unknown') + '. This picture is hidden from the markdown export.</div>';
    }}
    html += field('Caption', data.caption_text);
    if (data.figure_type) {{
      html += field('Figure type (BiomedCLIP)', data.figure_type +
        ' (' + Math.round(100 * data.figure_type_confidence) + '%)');
    }}
    html += field('VLM description', data.vlm_caption);
    html += field('Generic classifier (noise filter only)', data.generic_classifier_label);
    if (data.image_path) {{
      html += field('Image', '<img class="panel-thumbnail" src="' + escapeHtml(data.image_path) + '"/>', {{raw: true}});
    }}
    return html;
  }}

  function renderTable(data) {{
    let html = field('Caption', data.caption_text);
    html += field('Dimensions', data.num_rows + ' rows by ' + data.num_cols + ' cols');
    if (data.table_html) {{
      html += field('Rendered table', '<div class="panel-table">' + data.table_html + '</div>', {{raw: true}});
    }}
    if (data.image_path) {{
      html += field('Cropped image', '<img class="panel-thumbnail" src="' + escapeHtml(data.image_path) + '"/>', {{raw: true}});
    }}
    return html;
  }}

  function renderText(data) {{
    return field('Text', data.text);
  }}

  function showNode(box) {{
    if (selected) selected.classList.remove('selected');
    box.classList.add('selected');
    selected = box;
    const payload = JSON.parse(box.dataset.payload || '{{}}');
    panelTitle.textContent = payload.label || '(unlabelled)';
    panelSelfRef.textContent = payload.self_ref || '';

    let html = '';
    if (payload.self_ref) {{
      const link = window.location.pathname + '?ref=' + encodeURIComponent(payload.self_ref);
      html += field('Citation link (copy for this node)',
        '<code class="citation-link">' + escapeHtml(link) + '</code>', {{raw: true}});
    }}
    if (payload.kind === 'picture') html += renderPicture(payload);
    else if (payload.kind === 'table') html += renderTable(payload);
    else html += renderText(payload);

    html += '<details class="panel-raw"><summary>Show raw JSON</summary><pre>' +
      escapeHtml(JSON.stringify(payload.raw, null, 2)) + '</pre></details>';
    panelBody.innerHTML = html;
  }}

  function highlightRefs(refs) {{
    let first = null;
    refs.forEach(function(ref) {{
      document.querySelectorAll('.bbox[data-self-ref="' + ref + '"]').forEach(function(box) {{
        box.classList.add('cited');
        if (!first) first = box;
      }});
    }});
    if (first) {{
      first.scrollIntoView({{block: 'center'}});
      showNode(first);
    }} else {{
      console.warn('preview.html: no bbox matched ref(s)', refs);
    }}
  }}

  document.querySelectorAll('.bbox').forEach(function(box) {{
    box.addEventListener('click', function(e) {{
      e.stopPropagation();
      showNode(box);
    }});
  }});

  panelClose.addEventListener('click', clearSelection);
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') clearSelection();
  }});

  const refParam = new URLSearchParams(window.location.search).get('ref');
  if (refParam) {{
    highlightRefs(refParam.split(',').map(function(r) {{ return r.trim(); }}).filter(Boolean));
  }}
}})();
</script>
</body>
</html>
"""
