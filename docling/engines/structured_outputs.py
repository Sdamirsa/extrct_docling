# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Per-PDF ``tables.jsonl`` and ``figures.jsonl`` — agent-friendly views.

These derive value-add fields from the ``DoclingDocument`` that ``nodes.jsonl``
doesn't expose flat:

* For tables: ``markdown`` / ``html`` renderings, cell offsets/spans, and a
  resolved ``caption_text``.
* For figures: ``figure_type`` + ``figure_type_confidence`` (BiomedCLIP,
  see :mod:`docling.engines.figure_typing`), ``vlm_caption`` (when picture
  description is on), ``generic_classifier_label`` (Docling's generic
  document-figure classifier — no medical classes, only meaningful for the
  noise filter), ``caption_text`` resolved from caption refs, and
  ``chart_data`` (``extrct.figure-data/1``, see
  :mod:`docling.engines.figure_data`) when the figure's numbers were read.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docling_core.types.doc import PictureItem, TableItem

from docling.engines.artifacts import crops_by_self_ref
from docling.engines.figure_data.publish import get_chart_data
from docling.engines.figure_typing import get_figure_type
from docling.engines.picture_filter import PictureNoiseFlag
from docling.engines.text_repair import table_structure_model

if TYPE_CHECKING:
    from docling.datamodel.document import ConversionResult

_log = logging.getLogger(__name__)

_TABLES_FILENAME = "tables.jsonl"
_FIGURES_FILENAME = "figures.jsonl"


class StructuredOutputsError(RuntimeError):
    """Raised when structured-output extraction cannot complete."""


@dataclass
class StructuredOutputPaths:
    """Paths returned by :func:`write_structured_outputs`."""

    tables_jsonl: Path | None
    figures_jsonl: Path | None
    table_count: int
    figure_count: int


def write_structured_outputs(
    result: ConversionResult,
    pdf_dir: Path,
    *,
    picture_image_paths: list[Path] | None = None,
    table_image_paths: list[Path] | None = None,
    picture_noise_flags: list[PictureNoiseFlag] | None = None,
) -> StructuredOutputPaths:
    """Write ``tables.jsonl`` + ``figures.jsonl`` if the doc has any of each.

    ``picture_image_paths`` and ``table_image_paths`` are the crops the
    artifacts writer wrote; each row's ``image_path`` is its own item's crop,
    or None when the item had no image.
    """
    if result.document is None:
        raise StructuredOutputsError("ConversionResult has no document.")

    pdf_dir.mkdir(parents=True, exist_ok=True)
    doc = result.document
    crops = crops_by_self_ref(
        doc, [*(picture_image_paths or []), *(table_image_paths or [])]
    )
    noise_flags = {
        flag.self_ref: flag
        for flag in picture_noise_flags or []
        if flag.self_ref is not None
    }

    table_rows: list[dict] = []
    figure_rows: list[dict] = []

    for item, _level in doc.iterate_items():
        if isinstance(item, PictureItem):
            figure_rows.append(
                _figure_row(
                    item,
                    len(figure_rows),
                    doc,
                    crops.get(item.self_ref),
                    pdf_dir,
                    noise_flags.get(item.self_ref),
                )
            )
        elif isinstance(item, TableItem):
            table_rows.append(
                _table_row(
                    item, len(table_rows), doc, crops.get(item.self_ref), pdf_dir
                )
            )

    tables_path = (
        _write_jsonl(pdf_dir / _TABLES_FILENAME, table_rows) if table_rows else None
    )
    figures_path = (
        _write_jsonl(pdf_dir / _FIGURES_FILENAME, figure_rows) if figure_rows else None
    )

    _log.info(
        "Structured outputs: %d tables, %d figures written under %s",
        len(table_rows),
        len(figure_rows),
        pdf_dir,
    )
    return StructuredOutputPaths(
        tables_jsonl=tables_path,
        figures_jsonl=figures_path,
        table_count=len(table_rows),
        figure_count=len(figure_rows),
    )


def _write_jsonl(target: Path, rows: list[dict]) -> Path:
    with target.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return target


def _prov_block(item: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prov in getattr(item, "prov", None) or []:
        bbox = getattr(prov, "bbox", None)
        out.append(
            {
                "page_no": getattr(prov, "page_no", None),
                "bbox": bbox.model_dump(mode="json") if bbox is not None else None,
                "charspan": list(getattr(prov, "charspan", []) or []),
            }
        )
    return out


def _safe_relative(p: Path | None, base: Path) -> str | None:
    if p is None:
        return None
    try:
        return p.relative_to(base).as_posix()
    except ValueError:
        return str(p)


def _table_row(
    item: TableItem,
    index: int,
    doc,
    image_path: Path | None,
    pdf_dir: Path,
) -> dict[str, Any]:
    try:
        markdown = item.export_to_markdown(doc=doc)
    except Exception as exc:  # pragma: no cover - defensive
        _log.warning("table %d markdown export failed: %s", index, exc)
        markdown = None
    try:
        html = item.export_to_html(doc=doc, add_caption=False)
    except Exception as exc:  # pragma: no cover - defensive
        _log.warning("table %d html export failed: %s", index, exc)
        html = None

    data = item.data
    cells = [
        {
            "text": c.text,
            "row_offset": [c.start_row_offset_idx, c.end_row_offset_idx],
            "col_offset": [c.start_col_offset_idx, c.end_col_offset_idx],
            "row_span": c.row_span,
            "col_span": c.col_span,
            "column_header": c.column_header,
            "row_header": c.row_header,
            "bbox": c.bbox.model_dump(mode="json") if c.bbox is not None else None,
        }
        for c in (data.table_cells if data is not None else [])
    ]

    return {
        "index": index,
        "self_ref": getattr(item, "self_ref", None),
        "label": item.label.value if hasattr(item.label, "value") else str(item.label),
        "prov": _prov_block(item),
        "caption_text": item.caption_text(doc) if hasattr(item, "caption_text") else "",
        "image_path": _safe_relative(image_path, pdf_dir),
        "structure_model": table_structure_model(item),
        "markdown": markdown,
        "html": html,
        "num_rows": data.num_rows if data is not None else 0,
        "num_cols": data.num_cols if data is not None else 0,
        "cells": cells,
    }


def _picture_annotation_caption(item: PictureItem) -> str | None:
    """Pull the first VLM-generated description from ``annotations`` if present."""
    for ann in getattr(item, "annotations", None) or []:
        text = getattr(ann, "text", None)
        kind = getattr(ann, "kind", None) or type(ann).__name__
        if text and "description" in str(kind).lower():
            return text
    # Fallback: first annotation with text.
    for ann in getattr(item, "annotations", None) or []:
        text = getattr(ann, "text", None)
        if text:
            return text
    return None


def _picture_classifier_label(item: PictureItem) -> str | None:
    """Pull the picture-classifier label if present."""
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


def _figure_row(
    item: PictureItem,
    index: int,
    doc,
    image_path: Path | None,
    pdf_dir: Path,
    noise_flag: PictureNoiseFlag | None = None,
) -> dict[str, Any]:
    refs = [
        r.cref for r in (getattr(item, "references", None) or []) if hasattr(r, "cref")
    ]
    classifier_label = _picture_classifier_label(item) or (
        noise_flag.classifier_label if noise_flag is not None else None
    )
    figure_type = get_figure_type(item)
    return {
        "index": index,
        "self_ref": getattr(item, "self_ref", None),
        "label": item.label.value if hasattr(item.label, "value") else str(item.label),
        "prov": _prov_block(item),
        "caption_text": item.caption_text(doc) if hasattr(item, "caption_text") else "",
        "references": refs,
        "image_path": _safe_relative(image_path, pdf_dir),
        "figure_type": figure_type.label if figure_type else None,
        "figure_type_confidence": figure_type.confidence if figure_type else None,
        "figure_type_model": figure_type.model if figure_type else None,
        "vlm_caption": _picture_annotation_caption(item),
        "generic_classifier_label": classifier_label,
        "is_noise": noise_flag is not None and noise_flag.is_noise,
        "noise_reason": noise_flag.noise_reason if noise_flag is not None else None,
        "annotations": [
            ann.model_dump(mode="json", serialize_as_any=True)
            for ann in (getattr(item, "annotations", None) or [])
        ],
        "chart_data": get_chart_data(item),
    }
