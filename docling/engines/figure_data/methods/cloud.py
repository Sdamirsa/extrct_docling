# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Method ``cloud``: one call to a cloud model's API per figure.

The model gets the figure, one enlarged crop per chart when the layout
analysis found several (a model sees every image at a fixed level of
detail, so a crop of its own is how a chart gets more of it), and
``figure.txt``. It answers once, as JSON to a schema, with the whole
figure.

The model is reached through a chat-completions endpoint with a key
(:mod:`.endpoint`): OpenRouter unless ``cloud_base_url`` names another.
The key comes from the environment variable ``cloud_api_key_env`` or from
``.env``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import ValidationError

from docling.engines.figure_data.methods.endpoint import (
    EndpointClient,
    EndpointError,
    api_key,
    image_part,
    is_local,
    text_part,
)
from docling.engines.figure_data.prepare import CONTEXT_FILENAME, PreparedFigure
from docling.engines.figure_data.reading import (
    CONVENTIONS,
    FigureReading,
    chart_from_reading,
)
from docling.engines.figure_data.schema import (
    CallTiming,
    ChartData,
    FigureDataOptions,
    FigureDataResult,
    inline_refs,
)

TRACE_FILENAME = "trace.json"

SYSTEM_PROMPT = f"""You read the data out of one figure from a scientific paper and return it as tables.

You are given the figure image; when the figure holds several charts, one enlarged crop per chart after it; the paper's caption; the charts a layout analysis found; and the text printed in the figure (taken from the PDF or read by OCR; OCR can misread, the image decides). Read each chart from its own crop when it has one.

Answer once, for the whole figure: description (what it shows, one sentence), has_data, one entry in panels per chart, and not_read.

{CONVENTIONS}"""


class CloudError(RuntimeError):
    """The cloud model could not be asked."""


class CloudReader:
    method = "cloud"

    def __init__(
        self, options: FigureDataOptions, *, endpoint: EndpointClient | None = None
    ) -> None:
        if options.backend != "openai-compatible":
            raise ValueError(
                f"the cloud method calls a model's API endpoint: backend "
                f"'openai-compatible', not {options.backend!r}"
            )
        self.options = options
        self._endpoint = endpoint

    def describe(self) -> dict[str, Any]:
        options = self.options
        return {
            "runtime": f"POST {options.cloud_base_url.rstrip('/')}/chat/completions, "
            f"key from {options.cloud_api_key_env}",
            "calls_per_figure": 1,
            "system_prompt": SYSTEM_PROMPT,
        }

    def close(self) -> None:
        if self._endpoint is not None:
            self._endpoint.close()

    def read(self, prepared: PreparedFigure, figure_dir: Path) -> FigureDataResult:
        options = self.options
        started = time.perf_counter()
        issues: list[str] = []
        reading: FigureReading | None = None
        call = CallTiming(prompt="cloud read", wall_s=0.0)
        try:
            reading, call = self._ask(prepared, figure_dir)
        except (CloudError, EndpointError, ValidationError) as exc:
            issues.append(f"cloud read failed: {str(exc)[:400]}")
        if reading is None:
            chart = ChartData(
                figure=prepared.figure,
                source_kind=prepared.source_kind,
                uncertain=["not read: the model returned no reading"],
            )
        else:
            if call.cut:
                issues.append(
                    "the reply ran into the token limit: its complete points are kept"
                )
            chart, checks = chart_from_reading(
                reading,
                prepared,
                reader="cloud",
                labeler=f"extrct figure-to-data cloud ({options.model})",
                frontier=not is_local(options.cloud_base_url),
            )
            issues.extend(checks)
        call.wall_s = call.wall_s or round(time.perf_counter() - started, 2)
        return FigureDataResult(
            chart_data=chart,
            method="cloud",
            backend=options.backend,
            model=options.model,
            panel_split=prepared.split_method,
            seconds=round(time.perf_counter() - started, 2),
            calls=[call],
            issues=issues,
        )

    def _ask(
        self, prepared: PreparedFigure, figure_dir: Path
    ) -> tuple[FigureReading, CallTiming]:
        options = self.options
        if self._endpoint is None:
            key = api_key(options.cloud_api_key_env)
            if key is None and not is_local(options.cloud_base_url):
                raise CloudError(
                    f"no API key: set {options.cloud_api_key_env} in the "
                    f"environment or in a .env file ({options.cloud_base_url})"
                )
            self._endpoint = EndpointClient(
                options.cloud_base_url, key, timeout_s=options.request_timeout_s
            )
        reply = self._endpoint.ask(
            model=options.model,
            system=SYSTEM_PROMPT,
            content=_content(prepared, figure_dir, options),
            schema=inline_refs(FigureReading.model_json_schema()),
            max_tokens=options.cloud_max_output_tokens,
            reasoning_effort=options.cloud_reasoning_effort,
        )
        (figure_dir / TRACE_FILENAME).write_text(
            json.dumps(
                {
                    "method": "cloud",
                    "model": reply.model or options.model,
                    "endpoint": options.cloud_base_url,
                    "asked_with": reply.asked_with,
                    "reasoning_effort": options.cloud_reasoning_effort,
                    "usage": reply.usage,
                    "reply": reply.data,
                },
                indent=1,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        call = CallTiming(
            prompt="cloud read",
            wall_s=reply.seconds,
            prompt_tokens=reply.prompt_tokens,
            eval_tokens=reply.completion_tokens,
            cost_usd=reply.cost_usd,
            turns=1,
            cut=reply.cut,
        )
        return FigureReading.model_validate(reply.data), call


def _content(
    prepared: PreparedFigure, figure_dir: Path, options: FigureDataOptions
) -> list[dict[str, Any]]:
    """The one user message: the figure, a crop per chart, the context."""
    max_side = options.cloud_max_side_px
    with Image.open(figure_dir / prepared.image) as opened:
        content = [image_part(opened, max_side)]
    for panel in prepared.panels:
        if panel.image is None:
            continue
        content.append(text_part(f"Chart {panel.id}, enlarged:"))
        with Image.open(figure_dir / panel.image) as crop:
            content.append(image_part(crop, max_side))
    content.append(
        text_part(
            (figure_dir / CONTEXT_FILENAME).read_text(encoding="utf-8")
            + "\nRead this figure."
        )
    )
    return content
