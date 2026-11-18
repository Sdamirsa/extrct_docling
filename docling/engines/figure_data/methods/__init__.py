# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The three ways a prepared figure is read. Each takes the same folder
(:mod:`docling.engines.figure_data.prepare`) and returns the same record;
which one to use is a matter of what may leave the machine, what it may
cost and how good the numbers have to be (``docs/mini-bench/chart-to-data``).

- ``ollama``: a local open-weight model inside the measured engine.
- ``cloud``: one call per figure to a cloud model's API endpoint.
- ``agent``: one agent session per figure, with a tool to look closer and
  checks fed back to it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.schema import FigureDataOptions, FigureDataResult


class FigureReader(Protocol):
    method: str

    def describe(self) -> dict[str, Any]:
        """How the method runs and the prompts it uses, for the run record."""

    def read(self, prepared: PreparedFigure, figure_dir: Path) -> FigureDataResult:
        """Read one prepared figure; never raises for a figure it cannot read."""

    def close(self) -> None: ...


def build_reader(options: FigureDataOptions) -> FigureReader:
    if options.method == "cloud":
        from docling.engines.figure_data.methods.cloud import CloudReader

        return CloudReader(options)
    if options.method == "agent":
        from docling.engines.figure_data.methods.agent import AgentReader

        return AgentReader(options)
    from docling.engines.figure_data.methods.ollama import OllamaReader

    return OllamaReader(options)
