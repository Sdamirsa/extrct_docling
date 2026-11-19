# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Method ``cloud``: a cloud model's API reads each figure in two calls.

First the model lists the charts of the figure (the overview prompt of the
local engine, a short answer at low reasoning effort), and the prepared
figure is cut again by that list (:func:`..prepare.relist`): a model has
the number of charts right far more often than the rule splitter, and the
rules draw the edges. ``panel_split = "rules"`` leaves that call out.

Then the model gets the figure, one enlarged crop per chart when there are
several (a model sees every image at a fixed level of detail, so a crop of
its own is how a chart gets more of it), and ``figure.txt``. It answers
once, as JSON to a schema, with the whole figure.

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
    EndpointReply,
    ReplyError,
    api_key,
    image_part,
    is_local,
    text_part,
)
from docling.engines.figure_data.prepare import (
    CONTEXT_FILENAME,
    PreparedFigure,
    relist,
    unlist,
)
from docling.engines.figure_data.readers.vlm import (
    GRID,
    OverviewResponse,
    overview_prompt,
)
from docling.engines.figure_data.reading import (
    CONVENTIONS,
    FigureReading,
    chart_from_reading,
)
from docling.engines.figure_data.schema import (
    Box,
    CallTiming,
    ChartData,
    FigureDataOptions,
    FigureDataResult,
    inline_refs,
)

TRACE_FILENAME = "trace.json"

LIST_SYSTEM_PROMPT = (
    "You look at one figure from a scientific paper and answer as JSON."
)
# The end of an issue that says the model's chart list was not used. (No
# word of failure in it: the step classes a figure by its issues, and a
# figure read without a list is not a failed one.)
_RULES_KEPT = "the rule splitter's cut is kept"

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
            "calls_per_figure": 2 if options.panel_split == "auto" else 1,
            "system_prompt": SYSTEM_PROMPT,
        }

    def close(self) -> None:
        if self._endpoint is not None:
            self._endpoint.close()

    def read(self, prepared: PreparedFigure, figure_dir: Path) -> FigureDataResult:
        options = self.options
        started = time.perf_counter()
        issues: list[str] = []
        calls: list[CallTiming] = []
        listing: dict[str, Any] | None = None
        # A figure folder is reused: whatever an earlier run listed, this
        # one starts from the rule splitter's cut.
        prepared = unlist(prepared, figure_dir)
        if options.panel_split == "auto":
            try:
                prepared, listed, listing, unused = self._list(prepared, figure_dir)
                calls.append(listed)
                issues.extend([unused] if unused else prepared.split_notes)
            except (CloudError, EndpointError) as exc:
                issues.append(f"no chart list ({str(exc)[:300]}): {_RULES_KEPT}")
        reading: FigureReading | None = None
        call = CallTiming(prompt="cloud read", wall_s=0.0)
        try:
            reading, call, unread = self._ask(prepared, figure_dir, listing)
            if unread is not None:
                issues.append(f"cloud read failed: {unread}")
        except (CloudError, EndpointError) as exc:
            issues.append(f"cloud read failed: {str(exc)[:400]}")
            if listing is not None:
                # The list was made and paid for: keep it beside the failure.
                _write_trace(figure_dir, options, reply=None, listing=listing)
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
            calls=[*calls, call],
            issues=issues,
        )

    def _client(self) -> EndpointClient:
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
        return self._endpoint

    def _list(
        self, prepared: PreparedFigure, figure_dir: Path
    ) -> tuple[PreparedFigure, CallTiming, dict[str, Any], str | None]:
        """Ask the model which charts the figure holds and cut the prepared
        figure by its list. Returns the figure, the call, what goes into
        the trace, and why the list was not used when it was not (a reply
        that is not a list, or one cut off). A list without charts leaves
        the rule splitter's cut: whether the figure holds data is the
        read's call."""
        options = self.options
        with Image.open(figure_dir / prepared.image) as opened:
            image = image_part(opened, options.cloud_max_side_px)
        effort = options.cloud_list_reasoning_effort
        try:
            reply = self._client().ask(
                model=options.model,
                system=LIST_SYSTEM_PROMPT,
                content=[
                    image,
                    text_part(overview_prompt(prepared.words, prepared.full)),
                ],
                schema=inline_refs(OverviewResponse.model_json_schema()),
                max_tokens=options.cloud_max_output_tokens,
                reasoning_effort=effort,
            )
        except ReplyError as exc:
            unread = {
                "reasoning_effort": effort,
                "usage": exc.reply.usage,
                "reply": None,
                "reply_text": exc.text,
            }
            problem = f"the reply holds no chart list: {_RULES_KEPT}"
            return prepared, _call("cloud list", exc.reply), unread, problem
        call = _call("cloud list", reply)
        trace = {"reasoning_effort": effort, "usage": reply.usage, "reply": reply.data}
        try:
            listed = OverviewResponse.model_validate(reply.data)
        except ValidationError as exc:
            problem = f"the reply is not a chart list ({exc.error_count()} errors)"
            return prepared, call, trace, f"{problem}: {_RULES_KEPT}"
        if reply.cut:
            return prepared, call, trace, f"the chart list was cut off: {_RULES_KEPT}"
        if listed.has_data and listed.charts:
            prepared = relist(
                prepared,
                figure_dir,
                [(chart.id, _pixels(chart.box, prepared)) for chart in listed.charts],
                by=reply.model or options.model,
            )
        return prepared, call, trace, None

    def _ask(
        self,
        prepared: PreparedFigure,
        figure_dir: Path,
        listing: dict[str, Any] | None = None,
    ) -> tuple[FigureReading | None, CallTiming, str | None]:
        """The reading, the call, and what is wrong with the reply when it
        is not a reading (the call was made and is counted either way)."""
        options = self.options
        try:
            reply = self._client().ask(
                model=options.model,
                system=SYSTEM_PROMPT,
                content=_content(prepared, figure_dir, options),
                schema=inline_refs(FigureReading.model_json_schema()),
                max_tokens=options.cloud_max_output_tokens,
                reasoning_effort=options.cloud_reasoning_effort,
            )
        except ReplyError as exc:
            _write_trace(
                figure_dir, options, reply=exc.reply, listing=listing, text=exc.text
            )
            return None, _call("cloud read", exc.reply), str(exc)[:400]
        _write_trace(figure_dir, options, reply=reply, listing=listing)
        call = _call("cloud read", reply)
        try:
            return FigureReading.model_validate(reply.data), call, None
        except ValidationError as exc:
            return None, call, str(exc)[:400]


def _call(prompt: str, reply: EndpointReply) -> CallTiming:
    return CallTiming(
        prompt=prompt,
        wall_s=reply.seconds,
        prompt_tokens=reply.prompt_tokens,
        eval_tokens=reply.completion_tokens,
        cost_usd=reply.cost_usd,
        turns=1,
        cut=reply.cut,
    )


def _write_trace(
    figure_dir: Path,
    options: FigureDataOptions,
    *,
    reply: EndpointReply | None,
    listing: dict[str, Any] | None,
    text: str | None = None,
) -> None:
    """``trace.json``: what the model answered to the read (None when the
    endpoint gave no answer; *text* when the answer held no JSON object)
    and, under ``chart_list``, to the list call before it."""
    (figure_dir / TRACE_FILENAME).write_text(
        json.dumps(
            {
                "method": "cloud",
                "model": (reply.model if reply is not None else None) or options.model,
                "endpoint": options.cloud_base_url,
                "asked_with": reply.asked_with if reply is not None else None,
                "reasoning_effort": options.cloud_reasoning_effort,
                "usage": reply.usage if reply is not None else None,
                "reply": reply.data if reply is not None and text is None else None,
                "reply_text": text,
                "chart_list": listing,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _pixels(box: list[int], prepared: PreparedFigure) -> Box:
    """A box on the 0-1000 grid of the figure, in pixels of ``figure.png``."""
    x0, y0, x1, y1 = (min(max(v, 0), GRID) / GRID for v in box)
    return (
        min(x0, x1) * prepared.width,
        min(y0, y1) * prepared.height,
        max(x0, x1) * prepared.width,
        max(y0, y1) * prepared.height,
    )


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
