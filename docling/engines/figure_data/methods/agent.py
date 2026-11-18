# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Method ``agent``: one agent session per figure.

The agent is a Claude Code session without a terminal whose whole world is
one prepared figure: :data:`POLICY` as its system prompt, the figure image
and ``figure.txt`` as its only message, and the three tools of
:mod:`.toolbox` (look closer, record a chart, finish). It has no file,
shell or web tool, so one session cannot see another figure, the paper or
the machine. The runner starts a fresh session for every figure: what was
read in one figure never sits in the context of the next.

Built and measured with Claude Sonnet. With ``backend="ollama"`` the same
session runs on a local model through Ollama's Anthropic-compatible
endpoint.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

from docling.engines.figure_data.methods.claude_cli import (
    ClaudeCliError,
    CliRun,
    Runner,
    image_block,
    run_claude,
    text_block,
)
from docling.engines.figure_data.methods.toolbox import (
    AGENT_STATE_FILENAME,
    SERVER_NAME,
    FigureToolbox,
)
from docling.engines.figure_data.prepare import CONTEXT_FILENAME, PreparedFigure
from docling.engines.figure_data.reading import CONVENTIONS, chart_from_reading
from docling.engines.figure_data.schema import (
    CallTiming,
    ChartData,
    FigureDataOptions,
    FigureDataResult,
)

TRACE_FILENAME = "trace.json"
TOOLS = ("look", "record_chart", "finish")

POLICY = f"""You read the data out of ONE figure from a scientific paper and write it down as tables. This session holds that one figure and nothing else: no other figure, no file, no paper text. Work from what you see; do not ask for more.

You are given the figure image, the paper's caption for it, the charts a layout analysis found in it, and the text printed in it (taken from the PDF or read by OCR; OCR can misread, the image decides). Your tools: look (an enlarged view of the figure, of one chart or of a region, with the text printed there), record_chart (write down one chart), finish (end the reading).

Work in this order
1. Decide what the figure is. If it holds no data values, call finish with has_data false and stop.
2. Otherwise take its charts one at a time, in reading order. For each chart:
   - call look on it, so that you read it enlarged and not from the overview. Look again at a part of it wherever marks are small, dense or close together, or text is hard to read. A chart with more than about 20 marks is read in parts: look at a few rows or groups at a time. Never estimate what you could have enlarged;
   - read its structure (kind, orientation, axes, legend), then every mark;
   - count the marks you see and the points you wrote. The two numbers must agree; if they cannot, say in the chart's notes what is missing;
   - call record_chart and read the reply. A naming problem (a point without a name, several bars under one category, a legend entry missing) is always yours to fix: record the chart again with the names corrected. A value check (a value outside the axis, an interval that misses its centre, a stack that does not add up, a label the figure does not print) says where to look again: record the chart again if you were wrong, and keep a reading you have confirmed in the image, since a check can be wrong too.
3. When every chart is recorded, call finish with one sentence on what the figure shows and, in not_read, everything it shows that you did not record. Then stop; write no summary.

{CONVENTIONS}"""


class AgentReader:
    method = "agent"

    def __init__(
        self, options: FigureDataOptions, *, runner: Runner = subprocess.run
    ) -> None:
        if options.backend not in ("claude-cli", "ollama"):
            raise ValueError(
                "the agent method runs a Claude Code session: backend "
                f"'claude-cli' or 'ollama', not {options.backend!r}"
            )
        self.options = options
        self._runner = runner

    def describe(self) -> dict[str, Any]:
        return {
            "runtime": f"{self.options.claude_command} -p (Claude Code, headless)",
            "session": "one per figure; no built-in tools, no settings, "
            "memory files or other MCP servers",
            "tools": [f"mcp__{SERVER_NAME}__{name}" for name in TOOLS],
            "system_prompt": POLICY,
        }

    def close(self) -> None:
        return None

    def read(self, prepared: PreparedFigure, figure_dir: Path) -> FigureDataResult:
        options = self.options
        started = time.perf_counter()
        (figure_dir / AGENT_STATE_FILENAME).unlink(missing_ok=True)
        with Image.open(figure_dir / prepared.image) as image:
            content = [
                image_block(image, options.cloud_max_side_px),
                text_block(
                    (figure_dir / CONTEXT_FILENAME).read_text(encoding="utf-8")
                    + "\nRead this figure."
                ),
            ]
        issues: list[str] = []
        run = CliRun()
        try:
            run = run_claude(
                command=options.claude_command,
                model=options.model,
                system_prompt=POLICY,
                content=content,
                timeout_s=options.time_budget_s_per_figure,
                mcp_servers={
                    SERVER_NAME: {
                        "command": sys.executable,
                        "args": [
                            "-m",
                            "docling.engines.figure_data.methods.toolbox",
                            str(figure_dir.resolve()),
                        ],
                    }
                },
                allowed_tools=[f"mcp__{SERVER_NAME}__{name}" for name in TOOLS],
                effort=options.claude_effort,
                max_cost_usd=options.max_cost_usd_per_figure,
                ollama_url=options.ollama_url if options.backend == "ollama" else None,
                runner=self._runner,
            )
        except ClaudeCliError as exc:
            issues.append(f"agent session failed: {exc}")
        if run.error is not None:
            issues.append(f"agent session: {run.error}")
        (figure_dir / TRACE_FILENAME).write_text(
            json.dumps(
                {"method": "agent", "model": options.model, "events": run.events},
                indent=1,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        state = FigureToolbox.load_state(figure_dir)
        reading = state.reading() if state is not None else None
        labeler = f"extrct figure-to-data agent ({options.model})"
        if reading is None:
            issues.append("the agent recorded nothing")
            chart = ChartData(
                figure=prepared.figure,
                source_kind=prepared.source_kind,
                uncertain=["not read: the agent session ended without a reading"],
            )
        else:
            if state is not None and not state.finished:
                issues.append(
                    "the session ended before finish: what was recorded is kept"
                )
            chart, checks = chart_from_reading(
                reading,
                prepared,
                reader="agent",
                labeler=labeler,
                frontier=options.backend != "ollama",
            )
            issues.extend(checks)
        call = CallTiming(
            prompt="agent session",
            wall_s=run.seconds,
            prompt_tokens=run.input_tokens,
            eval_tokens=run.output_tokens,
            # The CLI prices every token as the provider's; a local model
            # costs nothing it could know.
            cost_usd=run.cost_usd if options.backend != "ollama" else None,
            turns=run.turns,
            tool_calls=len(run.tool_calls),
            cut=run.error is not None,
        )
        return FigureDataResult(
            chart_data=chart,
            method="agent",
            backend=options.backend,
            model=options.model,
            panel_split=prepared.split_method,
            seconds=round(time.perf_counter() - started, 2),
            calls=[call],
            issues=issues,
        )
