# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Put chart data where readers of a bundle look.

- ``PictureItem.meta``: the full record as the custom field
  ``amir__chart_data``; Docling's ``tabular_chart`` (a ``TableData``: first
  column category or x, one column per series, a panel column when there
  are several) built from the panels whose median confidence reaches
  ``min_confidence_for_markdown``, its ``title`` the sentence that says a
  model read it (:func:`docling.engines.figure_data.report.embed_note`).
  The markdown and the chunks show note and table at the figure, after the
  description a model wrote of it, marked as model output (see
  :mod:`docling.engines.serializers`); the HTML in its model-metadata box;
- ``figures.jsonl``: a ``chart_data`` key per row (and with it the HTML
  manifest). A figure that was looked at and holds no data has a record
  without panels whose ``uncertain`` says why;
- ``chunks.jsonl``: rebuilt, so that the tables can be retrieved;
- ``run.json``: a ``figure_to_data`` block (which run of the step wrote
  this); absent when the step never ran on the bundle;
- ``check.json``: the ``figure_data`` block (:mod:`docling.engines.export_check`).
"""

from __future__ import annotations

import json
import logging
import statistics
from pathlib import Path
from typing import Any

from docling_core.types.doc import (
    DoclingDocument,
    PictureItem,
    TableCell,
    TableData,
)
from docling_core.types.doc.document import (
    PictureMeta,
    TabularChartMetaField,
)
from PIL import Image, ImageDraw

from docling.engines.figure_data.evidence import (
    FIGURES_FILENAME,
    picture_by_ref,
)
from docling.engines.figure_data.schema import (
    CHART_DATA_META_KEY,
    ChartData,
    FigureDataResult,
    Panel,
    Value,
)
from docling.engines.run_snapshot import (
    RUN_JSON_FILENAME,
    read_run_record,
    write_text_atomic,
)

_log = logging.getLogger(__name__)

_META_NAMESPACE, _META_NAME = CHART_DATA_META_KEY.split("__", 1)
CREATED_BY = "extrct figure-to-data"
_LEGACY_CREATED_BY = "extrct figure-data"
RUN_BLOCK_KEY = "figure_to_data"
_PANEL_COLOURS = ("#d81b60", "#1e88e5", "#43a047", "#fb8c00", "#8e24aa", "#00897b")


def get_chart_data(picture: PictureItem) -> dict[str, Any] | None:
    """The stored ``extrct.figure-data/1`` record of *picture*, if any."""
    if picture.meta is None:
        return None
    return picture.meta.get_custom_part().get(CHART_DATA_META_KEY)


def panel_confidence(panel: Panel) -> float | None:
    values = [v.confidence for v in panel.data if v.confidence is not None]
    return statistics.median(values) if values else None


def chart_table(chart: ChartData, min_confidence: float) -> TableData | None:
    """The panels at or above *min_confidence* as one table, or None."""
    panels = [
        p
        for p in chart.panels
        if p.data and (panel_confidence(p) or 0.0) >= min_confidence
    ]
    if not panels:
        return None
    with_panel = len(panels) > 1
    series = list(dict.fromkeys(v.series or "value" for p in panels for v in p.data))
    first = (
        "x" if all(v.category is None for p in panels for v in p.data) else "category"
    )
    header = (["panel"] if with_panel else []) + [first] + series
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for panel in panels:
        for value in panel.data:
            key = (panel.id, _row_label(value))
            rows.setdefault(key, {})[value.series or "value"] = _cell_text(value)
    grid = [header] + [
        ([panel_id] if with_panel else [])
        + [label]
        + [cells.get(s, "") for s in series]
        for (panel_id, label), cells in rows.items()
    ]
    return TableData(
        num_rows=len(grid),
        num_cols=len(header),
        table_cells=[
            TableCell(
                text=text,
                start_row_offset_idx=r,
                end_row_offset_idx=r + 1,
                start_col_offset_idx=c,
                end_col_offset_idx=c + 1,
                column_header=r == 0,
                row_header=r > 0 and c == (1 if with_panel else 0),
            )
            for r, row in enumerate(grid)
            for c, text in enumerate(row)
        ],
    )


def attach_chart_data(
    picture: PictureItem,
    chart: ChartData,
    *,
    min_confidence: float,
    created_by: str,
    note: str,
) -> bool:
    """Store *chart* on *picture*; True when a ``tabular_chart`` was set.
    *note* is the sentence the exports print at the figure: above the
    table of the charts that reach *min_confidence*, or on its own, as a
    pointer to the full reading, when none does. A figure without values
    gets no ``tabular_chart``."""
    if picture.meta is None:
        picture.meta = PictureMeta()
    picture.meta.set_custom_field(_META_NAMESPACE, _META_NAME, chart.dump())
    with_data = [p for p in chart.panels if p.data]
    if not with_data:
        # Drop a table an earlier run of the step left; keep anyone else's.
        previous = picture.meta.tabular_chart
        if previous is not None and (previous.created_by or "").startswith(
            (CREATED_BY, _LEGACY_CREATED_BY)
        ):
            picture.meta.tabular_chart = None
        return False
    table = chart_table(chart, min_confidence)
    shown = sum((panel_confidence(p) or 0.0) >= min_confidence for p in with_data)
    if table is None:
        note += (
            " The values are not shown here: they are under the confidence "
            "threshold (a check failed, or nothing printed in the figure "
            "confirms them)."
        )
    elif shown < len(with_data):
        note += (
            f" {len(with_data) - shown} of {len(with_data)} charts are not "
            "shown here (under the confidence threshold)."
        )
    confidences = [c for p in with_data if (c := panel_confidence(p)) is not None]
    picture.meta.tabular_chart = TabularChartMetaField(
        title=note,
        chart_data=table or TableData(num_rows=0, num_cols=0, table_cells=[]),
        created_by=created_by,
        confidence=round(statistics.median(confidences), 3) if confidences else None,
    )
    return True


def created_by(result: FigureDataResult) -> str:
    return f"{CREATED_BY} {result.method} ({result.model or 'no model'})"


def draw_overlay(
    image_path: Path,
    result: FigureDataResult,
    target: Path,
    *,
    px_per_crop: float = 1.0,
) -> None:
    """The panels and the marks the engine placed, drawn on the image they
    were read from (*px_per_crop* image pixels per pixel of the bundle's
    crop, in which the record is written)."""
    with Image.open(image_path) as opened:
        image = opened.convert("RGB")
    scale = px_per_crop
    if max(image.size) < 1200:
        factor = max(1, round(1200 / max(image.size)))
        image = image.resize((image.width * factor, image.height * factor))
        scale *= factor
    draw = ImageDraw.Draw(image)
    colours = {
        p.id: _PANEL_COLOURS[i % len(_PANEL_COLOURS)]
        for i, p in enumerate(result.chart_data.panels)
    }
    for panel in result.chart_data.panels:
        box = [v * scale for v in panel.bbox_px]
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        draw.rectangle(box, outline=colours[panel.id], width=2)
        draw.text((box[0] + 3, box[1] + 2), panel.id, fill=colours[panel.id])
    for point in result.overlay:
        x, y = point.x * scale, point.y * scale
        colour = colours.get(point.panel, "#000000")
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), outline=colour, width=2)
        draw.text((x + 4, y - 6), point.label[:24], fill=colour)
    image.save(target)


def embed_results(
    bundle_dir: Path,
    results: list[tuple[FigureDataResult, str]],
    *,
    min_confidence: float,
    run_block: dict[str, Any],
    pdf_path: Path | None = None,
) -> int:
    """Write *results* (each with the note that goes above its table) into
    an existing bundle: ``document.json``, ``figures.jsonl``, the markdown
    files, ``chunks.jsonl``, the HTML, ``run.json`` and ``check.json`` (each
    when the bundle has it). Returns how many figures carry a record."""
    # These modules import this package.
    from docling.engines.chunker import (
        DEFAULT_MAX_TOKENS,
        DEFAULT_TOKENIZER,
        write_document_chunks,
    )
    from docling.engines.export_check import check_bundle, write_bundle_check
    from docling.engines.html_export import rebuild_document_html
    from docling.engines.pdf_engine import rewrite_bundle_markdown

    doc = DoclingDocument.load_from_json(bundle_dir / "document.json")
    attached = 0
    for result, note in results:
        figure = result.chart_data.figure
        picture = picture_by_ref(doc, figure.self_ref) if figure is not None else None
        if picture is None:
            continue
        attach_chart_data(
            picture,
            result.chart_data,
            min_confidence=min_confidence,
            created_by=created_by(result),
            note=note,
        )
        attached += 1
    doc.save_as_json(bundle_dir / "document.json")
    update_figure_rows(bundle_dir / FIGURES_FILENAME, doc)
    rewrite_bundle_markdown(doc, bundle_dir)
    record = read_run_record(bundle_dir)
    if (bundle_dir / "chunks.jsonl").is_file():
        config = record.engine_config if record is not None else {}
        write_document_chunks(
            doc,
            bundle_dir,
            tokenizer_repo=str(config.get("chunk_tokenizer") or DEFAULT_TOKENIZER),
            max_tokens=int(config.get("chunk_max_tokens") or DEFAULT_MAX_TOKENS),
        )
    run_json = bundle_dir / RUN_JSON_FILENAME
    if run_json.is_file():
        snapshot = json.loads(run_json.read_text(encoding="utf-8"))
        snapshot[RUN_BLOCK_KEY] = run_block
        write_text_atomic(
            run_json, json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
        )
    if (bundle_dir / f"{bundle_dir.name}.html").is_file():
        rebuild_document_html(bundle_dir)
    if (bundle_dir / "check.json").is_file():
        write_bundle_check(bundle_dir, check_bundle(bundle_dir, pdf_path=pdf_path))
    _log.info("Embedded figure data of %d figure(s) into %s", attached, bundle_dir)
    return attached


def update_figure_rows(figures_jsonl: Path, doc: DoclingDocument) -> None:
    """Set the ``chart_data`` key of each ``figures.jsonl`` row from its
    picture's meta."""
    if not figures_jsonl.is_file():
        return
    lines: list[str] = []
    for line in figures_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        picture = picture_by_ref(doc, row["self_ref"]) if row.get("self_ref") else None
        if picture is not None:
            row["chart_data"] = get_chart_data(picture)
        lines.append(json.dumps(row, ensure_ascii=False))
    figures_jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row_label(value: Value) -> str:
    if value.category is not None:
        return value.category
    if isinstance(value.x, float):
        return f"{value.x:g}"
    return str(value.x) if value.x is not None else ""


def _cell_text(value: Value) -> str:
    if value.value is None:
        return ""
    text = f"{value.value:g}"
    if value.err_lo is not None and value.err_hi is not None:
        text += f" [{value.err_lo:g}, {value.err_hi:g}]"
    return text
