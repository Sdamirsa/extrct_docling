# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Method ``ollama``: a local open-weight model, through the measured
engine (:mod:`docling.engines.figure_data.pipeline`).

A local model sees too little of an image to be asked for a whole figure,
and points at marks less well than it reads them, so the engine does the
parts code does better: it separates the charts, calibrates the axes from
the tick labels, asks the model for one chart at a time, follows a bar to
its end in the pixels, and takes a printed number over a measured one.
Nothing leaves the machine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docling.engines.figure_data.pipeline import read_figure
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.publish import draw_overlay
from docling.engines.figure_data.readers.vlm import (
    GROUNDED_PROMPT,
    OVERVIEW_PROMPT,
    OllamaClient,
    OllamaError,
)
from docling.engines.figure_data.schema import FigureDataOptions, FigureDataResult

OVERLAY_FILENAME = "overlay.png"


class OllamaReader:
    method = "ollama"

    def __init__(
        self, options: FigureDataOptions, *, client: OllamaClient | None = None
    ) -> None:
        self.options = options
        self.client = client or OllamaClient(
            options.ollama_url, timeout_s=options.request_timeout_s
        )

    def describe(self) -> dict[str, Any]:
        return {
            "runtime": "Ollama /api/chat, JSON-schema replies, temperature 0",
            "calls_per_figure": "one overview call, then one call per chart",
            "overview_prompt": OVERVIEW_PROMPT,
            "chart_prompt": GROUNDED_PROMPT,
        }

    def close(self) -> None:
        self.client.close()

    def unload(self) -> None:
        self.client.unload(self.options.model)

    def read(self, prepared: PreparedFigure, figure_dir: Path) -> FigureDataResult:
        job = prepared.job(figure_dir)
        result = read_figure(job, self.options, self.client)
        result.method = "ollama"
        result.backend = "ollama"
        try:
            result.ollama_ps = self.client.ps()
        except OllamaError as exc:
            result.issues.append(f"ollama ps failed: {exc}")
        if result.chart_data.panels:
            draw_overlay(
                job.image_path,
                result,
                figure_dir / OVERLAY_FILENAME,
                px_per_crop=prepared.px_per_crop,
            )
        return result
