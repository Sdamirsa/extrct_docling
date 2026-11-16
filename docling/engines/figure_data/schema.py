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
from pydantic import BaseModel, ConfigDict, Field, field_serializer

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
FigureDataMode = Literal["off", "simple", "measured"]
PanelSplit = Literal["auto", "off", "vlm"]
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
    """Configuration, recorded in ``run.json`` ``engine_config.figure_data``."""

    mode: FigureDataMode = "off"
    engine: Literal["ollama"] = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "gemma4:26b-a4b-it-q8_0"
    escalation_model: str | None = "gemma4:31b-it-q8_0"
    keep_alive: str = "10m"
    samples: int = Field(default=1, ge=1)
    panel_split: PanelSplit = "auto"
    crop_dpi: int = 220
    min_confidence_for_markdown: float = 0.7
    eligible_types: frozenset[str] = DEFAULT_ELIGIBLE_TYPES
    time_budget_s_per_figure: float = 120
    num_ctx: int = 16384
    # A read caught in a loop stops here instead of filling the context.
    max_output_tokens: int = 8192
    vlm_max_side_px: int = 1600
    request_timeout_s: float = 600

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
    """One Ollama ``/api/chat`` call."""

    panel: str | None = None
    prompt: str
    wall_s: float
    total_s: float | None = None
    load_s: float | None = None
    prompt_eval_s: float | None = None
    eval_s: float | None = None
    prompt_tokens: int | None = None
    eval_tokens: int | None = None


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
    mode: FigureDataMode
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
