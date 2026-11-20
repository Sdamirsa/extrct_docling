# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""``extrct.figure-data/1``: the chart data of a figure, written by the engine
and by labelers alike, plus the run options and the evidence of one figure.

Coordinates: ``Panel.bbox_px`` is in pixels of the bundle's crop
(``Figure.image_path``); ``Figure.bbox`` is ``[l, t, r, b]`` in PDF points
from the top-left of the page as displayed (Docling's frame). Evidence
(:class:`Word`, :class:`VectorMark`) is in pixels of the job's work image
(:attr:`FigureJob.image_path`), ``px_per_crop`` times the crop.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Literal

from docling_core.types.doc.document import MetaUtils
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

SCHEMA_ID = "extrct.figure-data/1"
CHART_DATA_META_KEY = MetaUtils.create_meta_field_name(
    namespace="amir", name="chart_data"
)

SourceKind = Literal["vector", "raster", "mixed", "unknown"]
PanelKind = Literal[
    "bar",
    "stacked_bar",
    "grouped_bar",
    "line",
    "scatter",
    "box",
    "forest",
    "kaplan_meier",
    "pie",
    "heatmap",
    "other",
]
ValueSource = Literal["printed", "vector", "raster", "vlm", "human", "agent"]
AxisScale = Literal["linear", "log", "categorical"]
Orientation = Literal["vertical", "horizontal"]
FigureDataMode = Literal["simple", "measured"]
# How a figure is read: a local model through Ollama with the measured
# engine, a cloud model's API (the charts listed, then the figure read in
# one call), or an agent that works through the figure with tools.
FigureMethod = Literal["ollama", "cloud", "agent"]
FigureDataChoice = Literal["off", "ollama", "cloud", "agent"]
# Where the model runs. ``ollama``: a local Ollama. ``openai-compatible``:
# a chat-completions API endpoint with a key (OpenRouter by default).
# ``claude-cli``: the Claude Code CLI with its own login, the agent's
# runtime.
Backend = Literal["ollama", "openai-compatible", "claude-cli"]
StepTiming = Literal["each", "end"]
DEFAULT_CLAUDE_MODEL = "claude-sonnet-5-5"
# The same model as OpenRouter names it.
DEFAULT_ENDPOINT_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_OLLAMA_MODEL = "gemma4:26b-a4b-it-qat"
DEFAULT_BACKENDS: dict[str, str] = {
    "ollama": "ollama",
    "cloud": "openai-compatible",
    "agent": "claude-cli",
}
DEFAULT_MODELS: dict[str, str] = {
    "ollama": DEFAULT_OLLAMA_MODEL,
    "openai-compatible": DEFAULT_ENDPOINT_MODEL,
    "claude-cli": DEFAULT_CLAUDE_MODEL,
}
# auto: the reading model lists the charts and the rules cut by that list
# (``panels.cut_from_list``); rules: the rule splitter alone; gutters: the
# rule splitter without its axes step; off: one chart; vlm (ollama): the
# model's boxes as they are.
PanelSplit = Literal["auto", "rules", "gutters", "off", "vlm"]
Box = tuple[float, float, float, float]

DEFAULT_ELIGIBLE_TYPES = frozenset(
    {
        "bar_chart",
        "line_chart",
        "scatter_plot",
        "box_plot",
        "forest_plot",
        "kaplan_meier",
        "roc_curve",
        "heatmap",
        "pie_chart",
    }
)


class Figure(BaseModel):
    bundle: str
    self_ref: str
    image_path: str | None = None
    page: int | None = None
    bbox: list[float] | None = None


class Axis(BaseModel):
    name: str | None = None
    unit: str | None = None
    scale: AxisScale | None = None
    range: list[float] | None = None
    ticks: list[str | float] | None = None


class Axes(BaseModel):
    x: Axis | None = None
    y: Axis | None = None


class Series(BaseModel):
    name: str
    color: str | None = None


class Value(BaseModel):
    category: str | None = None
    x: float | str | None = None
    series: str | None = None
    value: float | None = None
    err_lo: float | None = None
    err_hi: float | None = None
    label_printed: str | None = None
    source: ValueSource | None = None
    confidence: float | None = None


class Panel(BaseModel):
    id: str
    bbox_px: list[float] = Field(min_length=4, max_length=4)
    title: str | None = None
    kind: PanelKind | None = None
    orientation: Orientation | None = None
    axes: Axes | None = None
    series: list[Series] = Field(default_factory=list)
    data: list[Value] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Labeler(BaseModel):
    kind: Literal["human", "agent", "engine"]
    name: str | None = None
    date: str | None = None
    time_minutes: float | None = None


class ChartData(BaseModel):
    """One figure's data; predictions and ground truth share it."""

    model_config = ConfigDict(validate_by_name=True, serialize_by_alias=True)

    schema_id: str = Field(default=SCHEMA_ID, alias="schema")
    figure: Figure | None = None
    source_kind: SourceKind = "unknown"
    panels: list[Panel] = Field(default_factory=list)
    labeler: Labeler | None = None
    # What the figure shows, in the reader's words.
    description: str | None = None
    uncertain: list[str] = Field(default_factory=list)

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def chart_data_json_schema() -> dict[str, Any]:
    """JSON Schema of :class:`ChartData` (``$defs`` resolved inline)."""
    return inline_refs(ChartData.model_json_schema(by_alias=True))


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """*schema* with every ``$ref`` to ``#/$defs/...`` replaced by its
    definition: Ollama turns the ``format`` schema into a grammar and does
    not follow references everywhere."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                target = copy.deepcopy(defs[ref.removeprefix("#/$defs/")])
                extra = {k: v for k, v in node.items() if k != "$ref"}
                return resolve({**target, **extra})
            return {k: resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


class FigureDataOptions(BaseModel):
    """Configuration of the figure-to-data step, recorded with every run of
    it (``figure-to-data/runs/``). ``model`` and ``backend`` default to the
    method's own (:data:`DEFAULT_MODELS`, :data:`DEFAULT_BACKENDS`)."""

    method: FigureMethod = "ollama"
    backend: Backend = "ollama"
    # Default: the backend's own (:data:`DEFAULT_MODELS`).
    model: str = DEFAULT_OLLAMA_MODEL
    # The Ollama method's engine: measured (panels, axes, pointed marks) or
    # simple (one call on the whole figure).
    mode: FigureDataMode = "measured"
    ollama_url: str = "http://127.0.0.1:11434"
    keep_alive: str = "10m"
    # The cloud method's endpoint (any OpenAI-compatible chat-completions
    # API) and the environment variable, also looked up in ``.env``, that
    # holds its key. The key itself is never an option and never recorded.
    cloud_base_url: str = "https://openrouter.ai/api/v1"
    cloud_api_key_env: str = "OPENROUTER_API_KEY"
    # The reply and the model's thinking share this limit. On the densest
    # bench figure (264 values) Sonnet 5.5 used 24,000 tokens, 4,000 of
    # them thinking; Gemini 3.8 Flash thought for 26,000 and was cut at
    # 32,000 with a third of the values written.
    cloud_max_output_tokens: int = 64000
    # How hard the cloud model is asked to think, sent as
    # ``reasoning_effort``; None leaves it to the endpoint's default.
    # "medium" by the maintainer's decision (2026-11-20). Measured on one
    # paper with Sonnet 5.5 against "high": a third cheaper and twice as
    # fast, the values it returns as often right (258 of 268), but it
    # leaves the unlabelled values of dense charts out (258 of 573 values
    # right against 378). ``amir-figdata read --effort high`` reads those.
    cloud_reasoning_effort: str | None = "medium"
    # The same for the cloud method's first call, which only lists the
    # charts of the figure. Gemini 3.8 Flash thought for four minutes about
    # that at "high" and lists as well at "low".
    cloud_list_reasoning_effort: str | None = "low"
    # The Claude Code executable the agent method runs.
    claude_command: str = "claude"
    # Images sent to a cloud model are scaled down to this long side.
    cloud_max_side_px: int = 2000
    # Set on every session, so that a run does not depend on the effort
    # level saved in the user's own Claude Code settings.
    claude_effort: str = "high"
    # A session is stopped past this spend (as the CLI reports it).
    max_cost_usd_per_figure: float = 2.0
    samples: int = Field(default=1, ge=1)
    panel_split: PanelSplit = "auto"
    crop_dpi: int = 220
    min_confidence_for_markdown: float = 0.7
    eligible_types: frozenset[str] = DEFAULT_ELIGIBLE_TYPES
    # No new call starts once a figure has taken this long; a call that
    # runs longer than the per-call budget is cut and keeps what it has.
    time_budget_s_per_figure: float = 600
    time_budget_s_per_call: float = 120
    num_ctx: int = 16384
    # A read caught in a loop stops here instead of filling the context.
    max_output_tokens: int = 8192
    vlm_max_side_px: int = 1600
    request_timeout_s: float = 600

    @model_validator(mode="before")
    @classmethod
    def _method_defaults(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        filled = dict(data)
        method = filled.get("method") or "ollama"
        if filled.get("backend") is None:
            filled["backend"] = DEFAULT_BACKENDS.get(method, "ollama")
        if filled.get("model") is None:
            filled["model"] = DEFAULT_MODELS.get(
                filled["backend"], DEFAULT_OLLAMA_MODEL
            )
        return filled

    @field_serializer("eligible_types")
    def _sorted_types(self, types: frozenset[str]) -> list[str]:
        # run.json configs are compared across processes; set order is not stable.
        return sorted(types)


class Word(BaseModel):
    """A word printed in the figure; ``bbox`` in work-image pixels."""

    text: str
    bbox: Box
    source: Literal["pdf", "ocr"]

    @property
    def cx(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def cy(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


class VectorMark(BaseModel):
    """A PDF path object inside the figure box, in work-image pixels."""

    bbox: Box
    fill: str | None = None
    stroke: str | None = None
    points: list[tuple[float, float]] = Field(default_factory=list)
    closed: bool = False
    is_rect: bool = False


class FigureJob(BaseModel):
    """Everything the readers get about one figure."""

    figure: Figure
    crop_path: Path
    image_path: Path
    px_per_crop: float = 1.0
    native_bitmap: bool = False
    figure_type: str | None = None
    caption: str | None = None
    words: list[Word] = Field(default_factory=list)
    marks: list[VectorMark] = Field(default_factory=list)
    image_objects: int = 0
    source_kind: SourceKind = "unknown"

    def to_crop(self, box: Box) -> list[float]:
        return [round(v / self.px_per_crop, 1) for v in box]


class PlacedValue(BaseModel):
    """A value and where its mark is, in work-image pixels (for fusion of
    readers and the overlay)."""

    value: Value
    x_px: float | None = None
    y_px: float | None = None


class PanelRead(BaseModel):
    """What a geometric reader made of one panel."""

    kind: PanelKind
    orientation: Orientation | None = None
    series: list[Series] = Field(default_factory=list)
    values: list[PlacedValue] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CallTiming(BaseModel):
    """One model call (an Ollama ``/api/chat`` call, a cloud call) or one
    agent session."""

    panel: str | None = None
    prompt: str
    wall_s: float
    total_s: float | None = None
    load_s: float | None = None
    prompt_eval_s: float | None = None
    eval_s: float | None = None
    prompt_tokens: int | None = None
    eval_tokens: int | None = None
    # The reply was stopped by the deadline or the token limit.
    cut: bool = False
    # Cloud and agent runs: what the provider's CLI or API reported.
    cost_usd: float | None = None
    turns: int | None = None
    tool_calls: int | None = None


class RunningModel(BaseModel):
    """A row of ``ollama ps``."""

    name: str
    size: int = 0
    size_vram: int = 0
    context_length: int | None = None
    expires_at: str | None = None


class OverlayPoint(BaseModel):
    """A data mark to draw on the crop (crop pixels)."""

    panel: str
    x: float
    y: float
    label: str


class FigureDataResult(BaseModel):
    """One figure's run: its chart data plus how it was obtained."""

    chart_data: ChartData
    mode: FigureDataMode = "measured"
    method: FigureMethod = "ollama"
    backend: Backend = "ollama"
    model: str | None = None
    panel_split: str | None = None
    seconds: float = 0.0
    calls: list[CallTiming] = Field(default_factory=list)
    ollama_ps: list[RunningModel] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    overlay: list[OverlayPoint] = Field(default_factory=list)

    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens or 0 for c in self.calls)

    @property
    def eval_tokens(self) -> int:
        return sum(c.eval_tokens or 0 for c in self.calls)

    @property
    def cost_usd(self) -> float | None:
        costs = [c.cost_usd for c in self.calls if c.cost_usd is not None]
        return round(sum(costs), 4) if costs else None
