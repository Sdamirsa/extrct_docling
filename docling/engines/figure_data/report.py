# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""``figure-to-data.md``: one figure's reading for a person or an agent.

The file says first that a model read these numbers from the image, with
which method and model, then gives one table per chart and what was left
unread. The same record as JSON (``extrct.figure-data/1``) stands beside
it. :func:`embed_note` is the sentence that goes with the table wherever
it is embedded in the paper's own exports.
"""

from __future__ import annotations

from docling.engines.figure_data.evidence import job_stem
from docling.engines.figure_data.prepare import (
    CONTEXT_FILENAME,
    STEP_DIRNAME,
    STEP_VERSION,
    PreparedFigure,
)
from docling.engines.figure_data.schema import (
    Axis,
    ChartData,
    FigureDataResult,
    Panel,
    Value,
)

READING_MD = "figure-to-data.md"
READING_JSON = "figure-to-data.json"
_METHODS = {
    "ollama": "a local model through the measured engine",
    "cloud": "a cloud model's API, asked once for the figure",
    "agent": "an agent session on this figure",
}


def embed_note(result: FigureDataResult) -> str:
    """What stands above the table in the markdown, the HTML and the chunks."""
    chart = result.chart_data
    folder = job_stem(chart.figure.self_ref) if chart.figure is not None else ""
    date = chart.labeler.date if chart.labeler is not None else None
    return (
        "Figure data, read from the image by a vision model "
        f"(method {result.method}, model {result.model or 'none'}"
        + (f", {date}" if date else "")
        + "). These are not the authors' numbers: check them against the "
        f"figure. Full reading: {STEP_DIRNAME}/{folder}/{READING_MD}."
    )


def figure_markdown(
    result: FigureDataResult,
    prepared: PreparedFigure,
    *,
    run_id: str,
    min_confidence: float,
) -> str:
    chart = result.chart_data
    figure = prepared.figure
    date = chart.labeler.date if chart.labeler is not None else ""
    lines = [
        f"# Figure data: {job_stem(figure.self_ref)} of {figure.bundle}"
        + (f" (page {figure.page})" if figure.page is not None else ""),
        "",
        "> **Machine-read from the figure.** Nothing here is taken from the "
        "paper's text or tables, and none of it was checked by a person.",
        f"> Method `{result.method}` ({_METHODS[result.method]}), model "
        f"`{result.model or 'none'}`, {date}, figure-to-data step {STEP_VERSION}.",
        f"> Values can be wrong or missing: check them against `{prepared.image}` "
        "before relying on them.",
        "",
        f"**Caption in the paper:** {prepared.caption or '(none found)'}",
        "",
    ]
    if chart.description:
        lines += [f"**What the figure shows (model):** {chart.description}", ""]
    values = sum(len(panel.data) for panel in chart.panels)
    if not values:
        reason = chart.uncertain[0] if chart.uncertain else "nothing was read"
        lines += [f"**No data read:** {reason}", ""]
    low = False
    for panel in chart.panels:
        lines += _panel_lines(panel, min_confidence)
        low = low or any(_is_low(v, min_confidence) for v in panel.data)
    if low:
        lines += [
            f"`*` marks a value whose confidence is under {min_confidence:g}: it "
            "failed a check (see Checks) or was not confirmed by anything "
            "printed in the figure. Such values are left out of the table "
            "embedded in the paper's exports.",
            "",
        ]
    rest = chart.uncertain[1:] if not values else chart.uncertain
    if rest:
        lines += ["## Not read, or uncertain", ""]
        lines += [f"- {item}" for item in rest]
        lines.append("")
    if result.issues:
        lines += ["## Checks", ""]
        lines += [f"- {issue}" for issue in result.issues[:40]]
        if len(result.issues) > 40:
            lines.append(f"- ... {len(result.issues) - 40} more in the run record")
        lines.append("")
    if values:
        lines += [
            "Column `from`: `printed` a number printed in the figure; `vector` "
            "measured on the PDF's drawing by code; `raster` measured on the "
            "pixels at a mark the model pointed to; `vlm`, `agent` the model's "
            "own reading against the axis.",
            "",
        ]
    lines += [
        "---",
        f"Same record for programs: `{READING_JSON}` (`{chart.schema_id}`). "
        f"What the reader was given: `{prepared.image}`, `{CONTEXT_FILENAME}`. "
        f"How it was run: `../runs/{run_id}.json`.",
        "",
    ]
    return "\n".join(lines)


def _panel_lines(panel: Panel, min_confidence: float) -> list[str]:
    kind = panel.kind or "chart"
    if panel.orientation is not None:
        kind += f", {panel.orientation}"
    lines = [
        f"## Chart {panel.id}"
        + (f": {panel.title}" if panel.title else "")
        + f" ({kind})",
        "",
    ]
    axes = [
        text
        for name, axis in (
            ("x", panel.axes.x if panel.axes else None),
            ("y", panel.axes.y if panel.axes else None),
        )
        if (text := _axis_text(name, axis)) is not None
    ]
    if axes:
        lines += ["; ".join(axes) + ".", ""]
    if not panel.data:
        lines += ["No values read.", ""]
    else:
        lines += _table(panel, min_confidence)
        lines.append("")
    if panel.notes:
        lines += [f"- Note: {note}" for note in panel.notes]
        lines.append("")
    return lines


def _table(panel: Panel, min_confidence: float) -> list[str]:
    """One row per value: unambiguous for a program, and it keeps the
    interval, the printed label and where the value comes from."""
    rows = [
        "| category | x | series | value | low | high | printed | from | confidence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for value in panel.data:
        mark = "*" if _is_low(value, min_confidence) else ""
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(value.category),
                    _cell(value.x),
                    _cell(value.series),
                    _cell(value.value) + mark,
                    _cell(value.err_lo),
                    _cell(value.err_hi),
                    _cell(value.label_printed),
                    _cell(value.source),
                    _cell(value.confidence),
                ]
            )
            + " |"
        )
    return rows


def _axis_text(name: str, axis: Axis | None) -> str | None:
    if axis is None:
        return None
    parts = [f"{name} axis"]
    if axis.name:
        parts.append(f'"{axis.name}"')
    if axis.unit:
        parts.append(f"[{axis.unit}]")
    if axis.scale:
        parts.append(axis.scale)
    if axis.range is not None and len(axis.range) == 2:
        parts.append(f"{axis.range[0]:g} to {axis.range[1]:g}")
    return " ".join(parts) if len(parts) > 1 else None


def _is_low(value: Value, min_confidence: float) -> bool:
    return value.confidence is not None and value.confidence < min_confidence


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value).replace("|", "\\|").replace("\n", " ")
