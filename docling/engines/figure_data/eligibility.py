# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Which figures get read: not noise, and typed as a chart by BiomedCLIP
(``options.eligible_types``) or by Docling's generic picture classifier
(it calls charts reliably; BiomedCLIP confuses line and box plots)."""

from __future__ import annotations

from pathlib import Path

from docling_core.types.doc import DoclingDocument, PictureItem

from docling.engines.artifacts import crops_by_self_ref
from docling.engines.figure_data.evidence import FigureRow
from docling.engines.figure_data.schema import FigureDataOptions
from docling.engines.figure_typing import get_figure_type
from docling.engines.picture_filter import PictureNoiseFlag

CHART_CLASSIFIER_LABELS = frozenset(
    {"bar_chart", "line_chart", "pie_chart", "scatter_plot", "box_plot", "heatmap"}
)


def is_eligible(row: FigureRow, options: FigureDataOptions) -> bool:
    if row.is_noise or row.image_path is None:
        return False
    return (
        row.figure_type in options.eligible_types
        or row.generic_classifier_label in CHART_CLASSIFIER_LABELS
    )


def rows_from_document(
    doc: DoclingDocument,
    pdf_dir: Path,
    picture_images: list[Path],
    noise_flags: list[PictureNoiseFlag],
) -> list[FigureRow]:
    """The rows ``figures.jsonl`` will hold, for a conversion in progress."""
    crops = crops_by_self_ref(doc, picture_images)
    flags = {f.self_ref: f for f in noise_flags if f.self_ref is not None}
    rows: list[FigureRow] = []
    for item, _level in doc.iterate_items():
        if not isinstance(item, PictureItem):
            continue
        crop = crops.get(item.self_ref)
        flag = flags.get(item.self_ref)
        figure_type = get_figure_type(item)
        rows.append(
            FigureRow(
                self_ref=item.self_ref,
                image_path=crop.relative_to(pdf_dir).as_posix() if crop else None,
                figure_type=figure_type.label if figure_type else None,
                generic_classifier_label=flag.classifier_label if flag else None,
                is_noise=flag.is_noise if flag else None,
                caption_text=item.caption_text(doc),
            )
        )
    return rows
