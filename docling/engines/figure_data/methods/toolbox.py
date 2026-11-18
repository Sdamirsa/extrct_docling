# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The tools an agent has on ONE prepared figure, and the MCP server that
offers them (``python -m docling.engines.figure_data.methods.toolbox <figure folder>``).

- ``look``: an enlarged view of the figure, of one chart or of a region,
  with the text printed there. A model sees an image at a fixed level of
  detail whatever its size, so the way to more detail is a smaller piece.
- ``record_chart``: write down one chart. The reply is what the engine's
  checks say about it (values outside the axis, intervals that miss their
  centre, stacks that do not add up, labels the figure does not print,
  repeated or unnamed points), so the agent can look again and correct.
- ``finish``: what the figure is, and what was left unread.

The server holds one figure folder and has no other tool: an agent that is
given only this server cannot read anything else, and cannot write
anything but its reading (``agent-reading.json`` in the figure folder).
"""

from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from docling.engines.figure_data.evidence import words_in
from docling.engines.figure_data.prepare import STEP_VERSION, PreparedFigure
from docling.engines.figure_data.readers.vlm import words_block
from docling.engines.figure_data.reading import (
    GRID,
    FigureReading,
    ReadPanel,
    panel_checks,
)
from docling.engines.figure_data.schema import Box, inline_refs

AGENT_STATE_FILENAME = "agent-reading.json"
SERVER_NAME = "figure"
_VIEW_SIDE_PX = 1568
_MAX_ENLARGE = 4.0
_MIN_REGION = 0.02
_VIEW_WORDS = 120
_PROTOCOL = "2025-06-18"


class AgentState(BaseModel):
    """What the agent has written so far, kept on disk after every call."""

    panels: list[ReadPanel] = Field(default_factory=list)
    description: str = ""
    has_data: bool | None = None
    not_read: list[str] = Field(default_factory=list)
    finished: bool = False
    warned: bool = False
    looks: int = 0
    records: int = 0

    def reading(self) -> FigureReading | None:
        """The figure as the agent left it; None when it wrote nothing."""
        if self.has_data is None and not self.panels:
            return None
        return FigureReading(
            description=self.description,
            has_data=self.has_data if self.has_data is not None else True,
            panels=self.panels,
            not_read=self.not_read,
        )


class ToolResult(BaseModel):
    text: str
    image_png: bytes | None = None
    is_error: bool = False


class FigureToolbox:
    def __init__(self, figure_dir: Path) -> None:
        self.dir = figure_dir
        self.prepared = PreparedFigure.load(figure_dir)
        with Image.open(figure_dir / self.prepared.image) as image:
            self.image = image.convert("RGB")
        self.state = AgentState()
        self._save()

    @staticmethod
    def load_state(figure_dir: Path) -> AgentState | None:
        path = figure_dir / AGENT_STATE_FILENAME
        if not path.is_file():
            return None
        return AgentState.model_validate_json(path.read_text(encoding="utf-8"))

    def specs(self) -> list[dict[str, Any]]:
        box = {
            "type": "array",
            "items": {"type": "integer"},
            "description": "[x0, y0, x1, y1] on a 0-1000 grid, x from the left, y from the top",
        }
        return [
            {
                "name": "look",
                "description": (
                    "Get an enlarged view of the figure with the text printed "
                    "there. No arguments: the whole figure. chart: one of the "
                    "listed charts. box: a region, on the grid of the chart "
                    "when chart is given, else on the grid of the figure. "
                    "Look at a smaller region whenever marks are small, dense "
                    "or close together."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "chart": {"type": "string", "description": "a chart id"},
                        "box": box,
                    },
                },
            },
            {
                "name": "record_chart",
                "description": (
                    "Write down one chart: its structure and every data point. "
                    "Recording a chart id again replaces what was recorded "
                    "for it. The reply lists what the checks found."
                ),
                "inputSchema": inline_refs(ReadPanel.model_json_schema()),
            },
            {
                "name": "finish",
                "description": (
                    "End the reading. description: what the figure shows, one "
                    "sentence. has_data: false for a figure without data "
                    "values (then no chart is recorded). not_read: everything "
                    "the figure shows that you did not record, each with the "
                    "reason and how much it is."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "has_data": {"type": "boolean"},
                        "not_read": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["description", "has_data", "not_read"],
                },
            },
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name == "look":
            result = self.look(arguments.get("chart"), arguments.get("box"))
        elif name == "record_chart":
            result = self.record_chart(arguments)
        elif name == "finish":
            result = self.finish(arguments)
        else:
            result = ToolResult(text=f"no tool named {name}", is_error=True)
        self._save()
        return result

    # -- look ------------------------------------------------------------------

    def look(self, chart: object, box: object) -> ToolResult:
        region: Box = self.prepared.full
        where = "the whole figure"
        if chart is not None:
            panel = self.prepared.panel(str(chart))
            if panel is None:
                listed = ", ".join(p.id for p in self.prepared.panels) or "none"
                return ToolResult(
                    text=f"no chart {chart!r}; the listed charts are: {listed}. "
                    "Use box on the figure's grid for anything else.",
                    is_error=True,
                )
            region, where = panel.bbox, f"chart {panel.id}"
        if box is not None:
            inner = _sub_region(box, region)
            if inner is None:
                return ToolResult(
                    text="box must be [x0, y0, x1, y1] with x0 < x1 and y0 < y1 "
                    "on the 0-1000 grid, at least 20 wide and high",
                    is_error=True,
                )
            region = inner
            where = f"part of {where}"
        self.state.looks += 1
        x0, y0, x1, y1 = (round(v) for v in region)
        crop = self.image.crop((x0, y0, x1, y1))
        scale = min(_VIEW_SIDE_PX / max(crop.size), _MAX_ENLARGE)
        if abs(scale - 1.0) > 0.02:
            crop = crop.resize(
                (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = io.BytesIO()
        crop.save(buffer, format="PNG")
        grid = [
            round(region[0] / self.prepared.width * GRID),
            round(region[1] / self.prepared.height * GRID),
            round(region[2] / self.prepared.width * GRID),
            round(region[3] / self.prepared.height * GRID),
        ]
        words = words_block(
            words_in(self.prepared.words, region), region, limit=_VIEW_WORDS
        )
        return ToolResult(
            text=(
                f"View of {where}: region {grid} of the figure's 0-1000 grid, "
                f"shown at {scale:.1f}x.\nText printed here (text @ x,y on a "
                f"0-1000 grid of this view):\n{words}"
            ),
            image_png=buffer.getvalue(),
        )

    # -- record ----------------------------------------------------------------

    def record_chart(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            read = ReadPanel.model_validate(arguments)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors()[:8]
            )
            return ToolResult(
                text=f"not recorded, the chart does not validate: {problems}",
                is_error=True,
            )
        self.state.records += 1
        self.state.finished = False
        kept = [p for p in self.state.panels if p.id != read.id]
        replaced = len(kept) != len(self.state.panels)
        self.state.panels = [*kept, read]
        checks = panel_checks(read, self.prepared)
        without = sum(p.value is None for p in read.points)
        lines = [
            f"{'Replaced' if replaced else 'Recorded'} chart {read.id}: "
            f"{len(read.points)} point(s)"
            + (f", {without} without a value" if without else "")
            + "."
        ]
        if checks.naming:
            lines.append(
                "Naming problems. Record the chart again with these fixed "
                "(the values can stay as they are):"
            )
            lines.extend(f"- {check}" for check in checks.naming)
        if checks.values:
            lines.append(
                "Value checks. Look at the chart again where they point; "
                "record it again if you were wrong, keep what the image "
                "confirms:"
            )
            lines.extend(f"- {check}" for check in checks.values[:12])
        if not checks.naming and not checks.values:
            lines.append("No check failed.")
        lines.append(self._progress())
        return ToolResult(text="\n".join(lines))

    def _progress(self) -> str:
        recorded = [p.id for p in self.state.panels]
        open_ids = self._unrecorded()
        text = f"Recorded so far: {', '.join(recorded)}."
        if open_ids:
            text += f" Listed charts not recorded yet: {', '.join(open_ids)}."
        return text

    def _unrecorded(self) -> list[str]:
        listed = self.prepared.panels
        if len(listed) < 2 or len(self.state.panels) >= len(listed):
            return []
        recorded = {p.id.casefold() for p in self.state.panels}
        return [p.id for p in listed if p.id.casefold() not in recorded]

    # -- finish ----------------------------------------------------------------

    def finish(self, arguments: dict[str, Any]) -> ToolResult:
        description = str(arguments.get("description") or "").strip()
        has_data = arguments.get("has_data")
        not_read = arguments.get("not_read") or []
        if not description or not isinstance(has_data, bool):
            return ToolResult(
                text="finish needs description (text) and has_data (true or false)",
                is_error=True,
            )
        if not isinstance(not_read, list):
            not_read = [str(not_read)]
        if has_data and not self.state.panels:
            return ToolResult(
                text="has_data is true but no chart is recorded: record the "
                "charts first, or finish with has_data false",
                is_error=True,
            )
        if not has_data and self.state.panels:
            return ToolResult(
                text="has_data is false but charts are recorded: finish with "
                "has_data true, since you recorded data",
                is_error=True,
            )
        self.state.description = description
        self.state.has_data = has_data
        self.state.not_read = [str(item) for item in not_read]
        open_ids = self._unrecorded() if has_data else []
        misnamed = [
            p.id for p in self.state.panels if panel_checks(p, self.prepared).naming
        ]
        if (open_ids or misnamed) and not self.state.warned:
            self.state.warned = True
            parts = []
            if open_ids:
                parts.append(
                    f"the listed charts {', '.join(open_ids)} are not recorded "
                    "(if they hold data, record them; if not, or if you cannot "
                    "read them, name them in not_read)"
                )
            if misnamed:
                parts.append(
                    f"the charts {', '.join(misnamed)} still have the naming "
                    "problems their record_chart reply listed (record them "
                    "again with the names fixed)"
                )
            return ToolResult(
                text=f"Not finished yet: {'; '.join(parts)}. Then call finish again."
            )
        self.state.finished = True
        return ToolResult(text="Finished and saved. End your turn now.")

    def _save(self) -> None:
        (self.dir / AGENT_STATE_FILENAME).write_text(
            self.state.model_dump_json(indent=1) + "\n", encoding="utf-8"
        )


def _sub_region(box: object, outer: Box) -> Box | None:
    if not isinstance(box, list) or len(box) != 4:
        return None
    try:
        x0, y0, x1, y1 = (min(max(float(v), 0.0), GRID) / GRID for v in box)
    except (TypeError, ValueError):
        return None
    if x1 - x0 < _MIN_REGION or y1 - y0 < _MIN_REGION:
        return None
    width, height = outer[2] - outer[0], outer[3] - outer[1]
    return (
        outer[0] + x0 * width,
        outer[1] + y0 * height,
        outer[0] + x1 * width,
        outer[1] + y1 * height,
    )


# --- MCP over stdio -----------------------------------------------------------


def serve(figure_dir: Path, stdin: TextIO, stdout: TextIO) -> None:
    """Answer MCP requests (JSON-RPC 2.0, one message per line) until *stdin*
    closes: ``initialize``, ``tools/list``, ``tools/call``, ``ping``."""
    toolbox = FigureToolbox(figure_dir)
    for line in stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(toolbox, request)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()


def handle(toolbox: FigureToolbox, request: dict[str, Any]) -> dict[str, Any] | None:
    """The reply to one MCP *request*; None for a notification."""
    request_id = request.get("id")
    if request_id is None:
        return None
    method = request.get("method")
    params = request.get("params") or {}
    result: dict[str, Any]
    if method == "initialize":
        result = {
            "protocolVersion": params.get("protocolVersion") or _PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": STEP_VERSION},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": toolbox.specs()}
    elif method == "tools/call":
        outcome = toolbox.call(str(params.get("name")), params.get("arguments") or {})
        content: list[dict[str, Any]] = [{"type": "text", "text": outcome.text}]
        if outcome.image_png is not None:
            content.append(
                {
                    "type": "image",
                    "data": base64.b64encode(outcome.image_png).decode("ascii"),
                    "mimeType": "image/png",
                }
            )
        result = {"content": content, "isError": outcome.is_error}
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"unknown method {method}"},
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


if __name__ == "__main__":
    serve(Path(sys.argv[1]), sys.stdin, sys.stdout)
