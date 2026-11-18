# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A local VLM through Ollama: the client, the prompts and the response
schemas (passed as ``format``, so the model's output is grammar-bound JSON).

- **simple**: the whole figure → panels with structure and values.
- **overview**: the whole figure → what it is, whether it holds data at
  all, and its charts (the gate before any reading, and the check on the
  panel splitter).
- **grounded**: one panel crop → structure plus, per data point, where its
  mark is (0-1000 grid of the crop); the pipeline turns positions into
  values with the axis maps and keeps the model's number as the fallback.

The figure's words with their positions go into the prompt as text, so the
model copies printed labels instead of reading them off the pixels.

Replies are streamed: a call that passes its deadline or the token limit
keeps the complete points it has produced (:func:`salvage_json`) instead of
losing the whole reply. Point fields that do not apply are left out, which
makes a reply about a third as long as one that spells out every null.
"""

from __future__ import annotations

import base64
import io
import json
import time
from typing import Any, TypeVar

import httpx
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from docling.engines.figure_data.schema import (
    AxisScale,
    Box,
    CallTiming,
    Orientation,
    PanelKind,
    RunningModel,
    Word,
    inline_refs,
)

GRID = 1000
_MAX_PROMPT_WORDS = 160
_LOOP_TAIL = 120
_LOOP_REPEATS = 4

_Response = TypeVar("_Response", bound=BaseModel)


class OllamaError(RuntimeError):
    """Ollama is unreachable, refused the request, or returned no valid JSON."""


class OllamaClient:
    """Minimal ``/api/chat`` + ``/api/ps`` client."""

    def __init__(
        self,
        url: str,
        *,
        timeout_s: float = 600,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(base_url=url, timeout=timeout_s, transport=transport)

    def close(self) -> None:
        self._http.close()

    def chat(
        self,
        *,
        model: str,
        prompt: str,
        images: list[Image.Image],
        schema: dict[str, Any] | None,
        options: dict[str, Any],
        keep_alive: str,
        label: str,
        panel: str | None = None,
        deadline_s: float | None = None,
    ) -> tuple[str, CallTiming]:
        """The reply text; the call is cut after *deadline_s* seconds and
        returns what was generated until then (``CallTiming.cut``)."""
        body: dict[str, Any] = {
            "model": model,
            "stream": True,
            "think": False,
            "keep_alive": keep_alive,
            "options": options,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [encode_image(image) for image in images],
                }
            ],
        }
        if schema is not None:
            body["format"] = schema
        started = time.perf_counter()
        parts: list[str] = []
        last: dict[str, Any] = {}
        cut = False
        try:
            with self._http.stream("POST", "/api/chat", json=body) as response:
                if response.status_code != 200:
                    response.read()
                    raise OllamaError(
                        f"Ollama {response.status_code}: {response.text[:300]}"
                    )
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    last = json.loads(line)
                    parts.append(str(last.get("message", {}).get("content", "")))
                    if last.get("done"):
                        break
                    late = (
                        deadline_s is not None
                        and time.perf_counter() - started > deadline_s
                    )
                    if late or (len(parts) % 40 == 0 and _loops("".join(parts))):
                        cut = True
                        break
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        timing = CallTiming(
            panel=panel,
            prompt=label,
            wall_s=round(time.perf_counter() - started, 3),
            total_s=_seconds(last.get("total_duration")),
            load_s=_seconds(last.get("load_duration")),
            prompt_eval_s=_seconds(last.get("prompt_eval_duration")),
            eval_s=_seconds(last.get("eval_duration")),
            prompt_tokens=last.get("prompt_eval_count"),
            eval_tokens=last.get("eval_count"),
            cut=cut or last.get("done_reason") == "length",
        )
        return "".join(parts), timing

    def chat_json(
        self,
        response_model: type[_Response],
        **kwargs: Any,
    ) -> tuple[_Response, CallTiming]:
        text, timing = self.chat(
            schema=inline_refs(response_model.model_json_schema()), **kwargs
        )
        try:
            return response_model.model_validate_json(text), timing
        except ValidationError as exc:
            kept = salvage_json(text)
            if kept is not None:
                try:
                    timing.cut = True
                    return response_model.model_validate(kept), timing
                except ValidationError:
                    pass
            raise OllamaError(
                f"{response_model.__name__} not parsed from {text[:200]!r}: {exc}"
            ) from exc

    def ps(self) -> list[RunningModel]:
        try:
            response = self._http.get("/api/ps")
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        return [
            RunningModel.model_validate(m) for m in response.json().get("models", [])
        ]

    def unload(self, model: str) -> None:
        try:
            self._http.post(
                "/api/generate", json={"model": model, "keep_alive": 0, "prompt": ""}
            )
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc


def salvage_json(text: str) -> dict[str, Any] | None:
    """The object in a reply that stops mid-way through its last list (the
    token limit, the deadline): everything up to the last complete item."""
    end = text.rfind("}")
    while end > 0:
        for closing in ("]}", "]}]}"):
            try:
                value = json.loads(text[: end + 1] + closing)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        end = text.rfind("}", 0, end)
    return None


def _loops(text: str) -> bool:
    """The reply repeats itself: its last stretch already stands in it
    several times over (a model caught on one point writes it until the
    token limit)."""
    tail = text[-_LOOP_TAIL:]
    return len(text) > _LOOP_REPEATS * _LOOP_TAIL and text.count(tail) >= _LOOP_REPEATS


def _seconds(nanoseconds: int | None) -> float | None:
    return round(nanoseconds / 1e9, 3) if nanoseconds is not None else None


def encode_image(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def fit_image(image: Image.Image, max_side: int) -> Image.Image:
    if max(image.size) <= max_side:
        return image
    ratio = max_side / max(image.size)
    size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(size, Image.Resampling.LANCZOS)


# --- response schemas ---------------------------------------------------------


class VlmAxis(BaseModel):
    name: str | None
    unit: str | None
    scale: AxisScale | None
    min: float | None
    max: float | None


class VlmSeries(BaseModel):
    name: str
    color: str | None


class VlmRow(BaseModel):
    category: str | None
    x: str | None
    series: str | None
    value: float | None
    err_lo: float | None
    err_hi: float | None
    label_printed: str | None


class VlmPanel(BaseModel):
    id: str
    box: list[int] = Field(min_length=4, max_length=4)
    title: str | None
    kind: PanelKind
    orientation: Orientation | None
    x_axis: VlmAxis
    y_axis: VlmAxis
    series: list[VlmSeries]
    rows: list[VlmRow]


class SimpleResponse(BaseModel):
    panels: list[VlmPanel]


class VlmPoint(BaseModel):
    """One data mark. Only the fields without a default are always written
    (a model leaves out whatever it may); the others it leaves out when
    they do not apply. The ``_pos`` fields are grid positions, named so
    that they are not taken for axis values."""

    category: str | None
    x: str | None
    series: str | None
    px: int | None
    py: int | None
    start_pos: int | None = None
    lo_pos: int | None = None
    hi_pos: int | None = None
    value: float | None
    err_lo: float | None = None
    err_hi: float | None = None
    label: str | None = None


class GroundedResponse(BaseModel):
    title: str | None
    kind: PanelKind
    orientation: Orientation | None
    x_axis: VlmAxis
    y_axis: VlmAxis
    series: list[VlmSeries]
    points: list[VlmPoint]


class VlmChart(BaseModel):
    id: str
    kind: PanelKind
    box: list[int] = Field(min_length=4, max_length=4)


class OverviewResponse(BaseModel):
    description: str
    has_data: bool
    charts: list[VlmChart]


# --- prompts ------------------------------------------------------------------

SIMPLE_PROMPT = """You read charts in scientific papers. Extract the data plotted in this figure.
- One panel per separate chart; id = its printed letter (a, b, ...) or 1, 2, ... in reading order; box = [x0, y0, x1, y1] of the panel on a 0-1000 grid of the image.
- One row per (category or x value, series). value is in axis units (pie: the slice percentage); err_lo / err_hi are the absolute ends of error bars or confidence intervals, not deltas.
- Prefer numbers printed in the figure and copy them into label_printed exactly as printed.
- Use null for anything you cannot read. Never invent values.
Text printed in the figure (text @ x,y on the 0-1000 grid):
{words}"""

OVERVIEW_PROMPT = """This is a figure from a scientific paper. Say what it is, decide whether it shows numeric data, and list its charts.
- description: what the figure shows, in one short sentence.
- has_data: true only when the figure plots or prints data values that could go into a table: bars, lines, points, boxes, intervals, pie slices, heatmap cells, or curves with a printed statistic. A diagram, workflow, architecture, photo, screenshot or raw signal trace (ECG, waveform) has no such values: has_data false and no charts.
- charts: one entry per separate chart, in reading order. Every plot with its own axes, and every pie, is its own chart, also when they sit in a grid, share a legend, or stand under one panel letter. id = the chart's printed letter when each chart has its own, else 1, 2, 3, ...; kind = the chart type; box = [x0, y0, x1, y1] on a 0-1000 grid of the image (x from the left, y from the top).
Text printed in the figure (text @ x,y on the 0-1000 grid):
{words}"""

GROUNDED_PROMPT = """You read one chart from a scientific paper. Give its structure and locate every data mark.
- kind, orientation, axes (name, unit, scale, axis min and max). series = the legend entries with their colours; none when the chart has a single unnamed series.
- points: one per (category or x value, series), each once. category = the tick label of the mark, exactly as printed (null on a numeric x axis); x = its position on a numeric x axis (null otherwise); series = its legend entry, exactly as printed (null only when the chart has no legend). Never repeat the category as the series.
- px, py = where the mark is on a 0-1000 grid of this image (x from the left, y from the top):
  bar: the middle of the bar's end edge (the top edge of a vertical bar, the right edge of a horizontal one), not a point inside the bar;
  stacked bar: the far end of the segment, with start_pos = the grid position of its near end along the value axis;
  line or scatter: the marker;
  box plot: the median line, with lo_pos and hi_pos = the grid positions of the two whisker ends along the value axis;
  interval or forest plot: the centre marker, with lo_pos and hi_pos = the grid positions of the two ends of the interval along the value axis;
  pie: null.
  start_pos, lo_pos and hi_pos are positions on the same 0-1000 grid (y for a vertical value axis, x for a horizontal one), never axis values.
- value = the number the mark stands for, read against the axis (pie: the slice's percentage). label = the number printed at the mark, exactly as printed. err_lo, err_hi = the interval's ends as numbers, when they are printed.
- A curve with a statistic printed for it (a ROC curve with its AUC in the legend): one point per curve with category = the curve's name, series = the statistic's name (AUC, AUROC), value and label = the printed number, px and py null. Do not trace the curve.
- A line chart: one point per marker; without markers, one point per x tick. When the x axis has no tick labels, x = 1, 2, 3, ... in order.
- Leave out start_pos, lo_pos, hi_pos, err_lo, err_hi and label where they do not apply. Use null for a value you cannot read and never invent one. If this image is not a data chart, return no points.
Text printed in this chart (text @ x,y on the 0-1000 grid):
{words}{context}"""


def words_block(
    words: list[Word], region: Box, *, limit: int = _MAX_PROMPT_WORDS
) -> str:
    """``text @ x,y`` lines on the 0-1000 grid of *region*, reading order."""
    x0, y0, x1, y1 = region
    width, height = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    ordered = sorted(words, key=lambda w: (round(w.cy / 8), w.cx))[:limit]
    lines = [
        f"{w.text} @ {round((w.cx - x0) / width * GRID)},{round((w.cy - y0) / height * GRID)}"
        for w in ordered
    ]
    return "\n".join(lines) if lines else "(none found)"


def grid_to_px(value: float | None, start: float, size: float) -> float | None:
    return start + value / GRID * size if value is not None else None


def overview_prompt(words: list[Word], region: Box) -> str:
    return OVERVIEW_PROMPT.format(words=words_block(words, region))


def simple_prompt(words: list[Word], region: Box) -> str:
    return SIMPLE_PROMPT.format(words=words_block(words, region))


def grounded_prompt(
    words: list[Word], region: Box, *, axis_hint: str | None, shared: list[str]
) -> str:
    context = ""
    if axis_hint:
        context += f"\nAxis ticks found: {axis_hint}"
    if shared:
        context += "\nText shared by all panels (legend, axis titles): " + "; ".join(
            shared[:40]
        )
    return GROUNDED_PROMPT.format(words=words_block(words, region), context=context)
