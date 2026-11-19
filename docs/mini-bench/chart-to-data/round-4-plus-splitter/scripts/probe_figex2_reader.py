"""Can FigEx2's captioning model read values out of a chart?

    <figex2 python> .../scripts/probe_figex2_reader.py --code <FigEx2 checkout> \\
        --weights <FigEx2-8B folder> --base <Qwen3-VL-8B-Instruct folder> <figure id> ...

The readers of round 4 return the values of a chart. FigEx2's captioning
model was trained to write one caption per panel letter. This asks it for
the values as a table, one call per figure, and keeps what it answers
(``extra/figex2-captioner-as-reader.json``), beside its answer to its own
prompt on the same figures. ``score_figex2_reader.py`` counts the values.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import torch
from common import ROUND, figures, image_path
from PIL import Image

READ_PROMPT = (
    "This is a figure from a scientific paper with one or more charts. Read "
    "the data it plots and return every value as one table with the columns "
    "chart | category | series | value. chart is the chart's panel letter (a, "
    "b, ...) or 1 when there is one chart; category is the bar's or point's "
    "label on the axis (or its x value); series is the legend entry; value is "
    "the number in axis units, without a unit. One row per bar, bar segment or "
    "point. Return only the table."
)
# FigEx2's own image size and twice its own answer limit. The authors'
# code generates without a cache, so the time grows with the square of the
# answer's length: at 1,600 px and 8,192 tokens one dense figure did not
# finish in ten minutes. A table of more than about 90 rows is cut here.
MAX_SIDE = 1024
MAX_NEW_TOKENS = 2048


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("ids", nargs="+")
    args = parser.parse_args()

    for folder in (args.code, args.weights, args.base):
        if not folder.is_dir():
            raise SystemExit(f"not a folder: {folder}")
    # As in run_figex2.py: local folders only, no lookup on the hub.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    sys.path.insert(0, str(args.code))
    from inference import build_lm
    from model.FigEx2_dab_detr import PROMPT_COMPOUND

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    tokenizer, processor, lm = build_lm(
        str(args.base), args.weights / "vlm", device=device, dtype=dtype
    )
    by_id = {figure["id"]: figure for figure in figures()}
    answers: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory() as work:
        for figure_id in args.ids:
            image = Image.open(image_path(by_id[figure_id])).convert("RGB")
            image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
            scaled = Path(work) / f"{figure_id}.png"
            image.save(scaled)
            row = {}
            for name, prompt in (
                ("asked_for_values", READ_PROMPT),
                ("own_prompt", PROMPT_COMPOUND),
            ):
                text, _, _ = lm.evaluate(
                    qwen_processor=processor,
                    tokenizer=tokenizer,
                    image_path=str(scaled),
                    device=device,
                    max_new_tokens=MAX_NEW_TOKENS
                    if name == "asked_for_values"
                    else 1024,
                    prompt=prompt,
                )
                row[name] = text
                print(f"--- {figure_id} {name}\n{text[:300]}\n", flush=True)
            answers[figure_id] = row
    target = ROUND / "extra" / "figex2-captioner-as-reader.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        json.dumps(
            {"prompt": READ_PROMPT, "image_side_px": MAX_SIDE, "figures": answers},
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
