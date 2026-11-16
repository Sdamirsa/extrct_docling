# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A local VLM through Ollama: the client, the prompts and the response
schemas (passed as ``format``, so the model's output is grammar-bound JSON).

- **simple**: the whole figure → panels with structure and values.
- **grounded**: one panel crop → structure plus, per data point, where its
  mark is (0-1000 grid of the crop); the pipeline turns positions into
  values with the axis maps and keeps the model's number as the fallback.
- **panel boxes**: the panels' boxes (0-1000 grid), the panel splitter's
  fallback.

The figure's words with their positions go into the prompt as text, so the
model copies printed labels instead of reading them off the pixels.
"""

from __future__ import annotations

import base64
import io
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
    ) -> tuple[str, CallTiming]:
        body: dict[str, Any] = {
            "model": model,
            "stream": False,
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
        try:
            response = self._http.post("/api/chat", json=body)
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        wall = time.perf_counter() - started
        if response.status_code != 200:
            raise OllamaError(f"Ollama {response.status_code}: {response.text[:300]}")
        data = response.json()
        timing = CallTiming(
            panel=panel,
            prompt=label,
            wall_s=round(wall, 3),
            total_s=_seconds(data.get("total_duration")),
            load_s=_seconds(data.get("load_duration")),
            prompt_eval_s=_seconds(data.get("prompt_eval_duration")),
            eval_s=_seconds(data.get("eval_duration")),
            prompt_tokens=data.get("prompt_eval_count"),
            eval_tokens=data.get("eval_count"),
        )
        return str(data.get("message", {}).get("content", "")), timing

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
    category: str | None
    x: str | None
    series: str | None
    px: int | None
    py: int | None
    start_pos: int | None
    lo_pos: int | None
    hi_pos: int | None
    value: float | None
    err_lo: float | None
    err_hi: float | None
    label_printed: str | None


class GroundedResponse(BaseModel):
    title: str | None
    kind: PanelKind
    orientation: Orientation | None
    x_axis: VlmAxis
    y_axis: VlmAxis
    series: list[VlmSeries]
    points: list[VlmPoint]


class VlmBox(BaseModel):
    id: str
    box: list[int] = Field(min_length=4, max_length=4)


class PanelBoxesResponse(BaseModel):
    panels: list[VlmBox]


# --- prompts ------------------------------------------------------------------

SIMPLE_PROMPT = """You read charts in scientific papers. Extract the data plotted in this figure.
- One panel per separate chart; id = its printed letter (a, b, ...) or 1, 2, ... in reading order; box = [x0, y0, x1, y1] of the panel on a 0-1000 grid of the image.
- One row per (category or x value, series). value is in axis units (pie: the slice percentage); err_lo / err_hi are the absolute ends of error bars or confidence intervals, not deltas.
- Prefer numbers printed in the figure and copy them into label_printed exactly as printed.
- Use null for anything you cannot read. Never invent values.
Text printed in the figure (text @ x,y on the 0-1000 grid):
{words}"""

GROUNDED_PROMPT = """You read one chart panel from a scientific paper. Give its structure and locate every data point.
- kind, orientation, axes (name, unit, scale, axis min and max), series with their legend colours.
- points: one per (category or x value, series). px, py = the data mark on a 0-1000 grid of this image: a bar's end (centre of its top, or right end if horizontal); a stacked segment's far end, with start_pos = its near end along the value axis; a line or scatter marker; null for pie slices. lo_pos / hi_pos = error bar or CI ends along the value axis on the same grid, else null.
- value = the number you read; label_printed = a number printed at the mark, exactly as printed, else null. Use null when unsure; never invent.
Text printed in this panel (text @ x,y on the 0-1000 grid):
{words}{context}"""

PANEL_BOXES_PROMPT = """This figure from a scientific paper may hold several charts (panels). Return each chart's box as [x0, y0, x1, y1] on a 0-1000 grid of the image, including its title and axis labels, and its id: the printed panel letter (a, b, ...) or 1, 2, ... in reading order. One box for a single chart."""


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
