"""Ask a vision model which charts each figure holds and where.

    uv run --no-sync python .../scripts/run_vlm.py --prepared <prepared folders> \\
        --name <candidate name> --method ollama|cloud --model <model id> [--caption]

Every model gets the step's own overview call, word for word: the figure
image and ``overview_prompt`` (``docling/engines/figure_data/readers/vlm.py``),
which asks for a one-line description, whether the figure holds data, and
one entry per chart with its box on a 0-1000 grid, and lists the words
printed in the figure with their positions. It is the call the local
engine opens every figure with, and the one whose boxes ``panel_split =
"vlm"`` would cut by.

``--caption`` (the final test) adds the figure's caption in the paper to
that prompt. The prepare phase has it for every figure the conversion
found a caption for; the overview call has never been given it.

``ollama``: a local model through Ollama, with the engine's client and its
options (temperature 0, context 16,384, image side 1,600 px). ``cloud``: a
model behind the chat-completions endpoint of the cloud method (OpenRouter
by default, image side 2,000 px, reasoning effort high); the key is read
the way the cloud method reads it and never printed or stored.

One call per figure, written to ``candidates/<name>.json`` after each, so a
stopped run picks up where it was.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, TypeVar

from common import ROUND, figures, image_path, write_candidate
from PIL import Image
from pydantic import BaseModel

from docling.engines.figure_data.methods.endpoint import (
    EndpointClient,
    EndpointError,
    api_key,
    image_part,
    text_part,
)
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.readers.vlm import (
    OllamaClient,
    OllamaError,
    OverviewResponse,
    fit_image,
    overview_prompt,
)
from docling.engines.figure_data.schema import FigureDataOptions, inline_refs

SYSTEM = "You look at one figure from a scientific paper and answer as JSON."
CLOUD_MAX_TOKENS = 32000
CAPTION_NOTE = (
    "\nThe figure's caption in the paper (it can name the panels; one panel "
    "can hold several charts, and the image decides):\n{caption}"
)

Reply = TypeVar("Reply", bound=BaseModel)


class Asker:
    """One model behind one method, asked the way the step asks it."""

    def __init__(self, method: str, model: str, effort: str | None = None) -> None:
        options = FigureDataOptions(method=method, model=model)
        if effort:
            options = options.model_copy(update={"cloud_reasoning_effort": effort})
        self.options = options
        self.model = model
        self._local: OllamaClient | None = None
        self._remote: EndpointClient | None = None
        if method == "ollama":
            self._local = OllamaClient(
                options.ollama_url, timeout_s=options.request_timeout_s
            )
            self.about = (
                f"{model} through Ollama (image side {options.vlm_max_side_px} "
                "px, temperature 0)"
            )
        else:
            key = api_key(options.cloud_api_key_env)
            if key is None:
                raise SystemExit(f"no API key: set {options.cloud_api_key_env}")
            self._remote = EndpointClient(
                options.cloud_base_url, key, timeout_s=options.request_timeout_s
            )
            self.about = (
                f"{model} through {options.cloud_base_url} (image side "
                f"{options.cloud_max_side_px} px, reasoning effort "
                f"{options.cloud_reasoning_effort})"
            )

    def ask(
        self, response: type[Reply], prompt: str, images: list[Image.Image], label: str
    ) -> tuple[Reply, dict[str, Any]]:
        """The model's answer to *prompt* about *images*, and what the call
        took."""
        options = self.options
        if self._local is not None:
            reply, timing = self._local.chat_json(
                response,
                model=self.model,
                prompt=prompt,
                images=[fit_image(image, options.vlm_max_side_px) for image in images],
                options={
                    "num_ctx": options.num_ctx,
                    "num_predict": options.max_output_tokens,
                    "temperature": 0,
                },
                keep_alive=options.keep_alive,
                label=label,
                deadline_s=options.time_budget_s_per_call,
            )
            return reply, {
                "seconds": timing.wall_s,
                "prompt_tokens": timing.prompt_tokens,
                "output_tokens": timing.eval_tokens,
                "cut": timing.cut,
            }
        assert self._remote is not None
        answer = self._remote.ask(
            model=self.model,
            system=SYSTEM,
            content=[
                *(image_part(image, options.cloud_max_side_px) for image in images),
                text_part(prompt),
            ],
            schema=inline_refs(response.model_json_schema()),
            max_tokens=CLOUD_MAX_TOKENS,
            reasoning_effort=options.cloud_reasoning_effort,
        )
        return response.model_validate(answer.data), {
            "seconds": answer.seconds,
            "prompt_tokens": answer.prompt_tokens,
            "output_tokens": answer.completion_tokens,
            "cost_usd": answer.cost_usd,
            "cut": answer.cut,
        }

    def close(self) -> None:
        if self._local is not None:
            self._local.unload(self.model)
            self._local.close()
        if self._remote is not None:
            self._remote.close()


def boxes_of(reply: OverviewResponse) -> tuple[list[list[float]], list[str]]:
    boxes: list[list[float]] = []
    labels: list[str] = []
    for chart in reply.charts if reply.has_data else []:
        x0, y0, x1, y1 = (float(min(max(v, 0), 1000)) for v in chart.box)
        boxes.append([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)])
        labels.append(chart.id)
    return boxes, labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--method", choices=("ollama", "cloud"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--effort", help="cloud: reasoning effort (default: the step's)"
    )
    parser.add_argument(
        "--caption", action="store_true", help="add the figure's caption to the prompt"
    )
    parser.add_argument("--only", nargs="*", help="figure ids (default: all)")
    args = parser.parse_args()

    target = ROUND / "candidates" / f"{args.name}.json"
    rows: dict[str, dict[str, Any]] = (
        json.loads(target.read_text(encoding="utf-8"))["figures"]
        if target.is_file()
        else {}
    )
    asker = Asker(args.method, args.model, args.effort)
    about = f"{asker.about}, the step's overview call" + (
        ", with the figure's caption in the paper added." if args.caption else "."
    )
    for figure in figures():
        if args.only and figure["id"] not in args.only:
            continue
        if figure["id"] in rows and "error" not in rows[figure["id"]]:
            continue
        prepared = PreparedFigure.load(args.prepared / figure["prepared"])
        image = Image.open(image_path(figure)).convert("RGB")
        prompt = overview_prompt(prepared.words, prepared.full)
        caption = (prepared.caption or "").strip()
        if args.caption and caption:
            prompt += CAPTION_NOTE.format(caption=caption)
        row: dict[str, Any]
        try:
            reply, row = asker.ask(OverviewResponse, prompt, [image], "overview")
            boxes, labels = boxes_of(reply)
            row.update(
                boxes=boxes,
                labels=labels,
                has_data=reply.has_data,
                description=reply.description,
                kinds=[chart.kind for chart in reply.charts],
            )
            if args.caption:
                row["caption_given"] = bool(caption)
        except (OllamaError, EndpointError, ValueError) as exc:
            row = {"boxes": [], "labels": [], "error": str(exc)[:300]}
        rows[figure["id"]] = row
        write_candidate(args.name, about, rows)
        print(
            figure["id"],
            len(row["boxes"]),
            row.get("seconds"),
            row.get("cost_usd", ""),
            row.get("error", ""),
            flush=True,
        )
    asker.close()


if __name__ == "__main__":
    main()
