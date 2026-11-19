"""Let a model rule between two cuts of a figure.

    uv run --no-sync python .../scripts/run_ruling.py --prepared <prepared folders> \\
        --name <ruling name> --list <candidate> --method ollama|cloud --model <model id> \\
        [--caption] [--only <figure id> ...]

The two cuts of a figure: the rule splitter's own (``candidates/rules.json``)
and the rules' cutter started from a model's chart list
(``candidates/<list>-cut.json``). Where the two are the same cut (as many
boxes, each overlapping its partner by half or more), nothing is asked.
Where they differ, the model gets both drawn on the figure, as two images,
and answers with a number and a boolean: how many charts the figure has,
and whether the first drawing is the right cut. Which cut is drawn first
is fixed by the figure's id, half and half.

Writes ``final-test/rulings/<ruling name>.json`` after each figure.
"""

from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path
from typing import Any

from common import ROUND, figures, image_path, read_candidate, to_px
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from run_vlm import Asker
from score import FOUND, WHOLE, pair

from docling.engines.figure_data.methods.endpoint import EndpointError
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.readers.vlm import OllamaError

SIDE = 2000
INK = (230, 0, 122)
PROMPT = """These two images show the same figure from a scientific paper. On each, one way of cutting the figure into its charts is drawn: every numbered box is meant to hold exactly one chart, whole (its plot, tick labels, axis titles, its own title and legend). Every plot with its own axes, and every pie, is its own chart, also when they sit in a grid, share a legend, or stand under one panel letter.
The first image has {first} box(es), the second image has {second}.
- charts: how many charts the figure has.
- first_is_right: true when the boxes of the first image are the right cut, false when those of the second image are. When neither is right, choose the one closer to it."""
CAPTION = "\nThe figure's caption in the paper (it can name the panels; one panel can hold several charts, and the image decides):\n{caption}"


class Ruling(BaseModel):
    charts: int
    first_is_right: bool


def same_cut(a: list[list[float]], b: list[list[float]]) -> bool:
    if len(a) != len(b):
        return False
    return len(a) == 1 or all(score >= FOUND for _, _, score in pair(a, b))


def drawn(image: Image.Image, boxes: list[list[float]]) -> Image.Image:
    """*image* with the numbered *boxes* drawn on it."""
    canvas = image.copy()
    canvas.thumbnail((SIDE, SIDE))
    draw = ImageDraw.Draw(canvas)
    line = max(3, round(max(canvas.size) / 400))
    font = ImageFont.load_default(size=max(14, round(max(canvas.size) / 70)))
    for index, box in enumerate(boxes, 1):
        x0, y0, x1, y1 = to_px(box, canvas.width, canvas.height)
        # A cut can hold a cell without height or width; it is drawn as a line.
        draw.rectangle(
            (x0, y0, max(x0, x1 - 1), max(y0, y1 - 1)), outline=INK, width=line
        )
        tag = draw.textbbox((x0 + line, y0 + line), str(index), font=font)
        draw.rectangle((tag[0] - 3, tag[1] - 3, tag[2] + 3, tag[3] + 3), fill=INK)
        draw.text((x0 + line, y0 + line), str(index), fill="white", font=font)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--list", required=True, dest="listed")
    parser.add_argument("--method", choices=("ollama", "cloud"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort")
    parser.add_argument("--caption", action="store_true")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--keep-drawings", type=Path, help="save what was sent")
    args = parser.parse_args()

    target = ROUND / "final-test" / "rulings" / f"{args.name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict[str, Any]] = (
        json.loads(target.read_text(encoding="utf-8"))["figures"]
        if target.is_file()
        else {}
    )
    rules = read_candidate("rules")
    listed = read_candidate(args.listed)
    seeded = read_candidate(f"{args.listed}-cut")
    asker = Asker(args.method, args.model, args.effort)
    about = (
        f"{asker.about}: where the rule splitter's cut and the rules' cutter "
        f"started from {args.listed} differ, the model sees both drawn on the "
        "figure and says how many charts there are and whether the first "
        "drawing is right" + (", with the figure's caption." if args.caption else ".")
    )
    for figure in figures():
        figure_id = figure["id"]
        if args.only and figure_id not in args.only:
            continue
        if figure_id not in listed or "error" in listed[figure_id]:
            continue
        if figure_id in rows and "error" not in rows[figure_id]:
            continue
        cuts = {
            "rules": rules[figure_id].get("boxes") or [WHOLE],
            "list": seeded[figure_id].get("boxes") or [WHOLE],
        }
        row: dict[str, Any] = {"boxes": {k: len(v) for k, v in cuts.items()}}
        if same_cut(cuts["rules"], cuts["list"]):
            row["same"] = True
        else:
            order = ["rules", "list"] if zlib.crc32(figure_id.encode()) % 2 else ["list", "rules"]
            image = Image.open(image_path(figure)).convert("RGB")
            drawings = [drawn(image, cuts[name]) for name in order]
            if args.keep_drawings:
                args.keep_drawings.mkdir(parents=True, exist_ok=True)
                for name, drawing in zip(order, drawings):
                    drawing.save(args.keep_drawings / f"{figure_id}-{name}.png")
            prompt = PROMPT.format(first=len(cuts[order[0]]), second=len(cuts[order[1]]))
            caption = (
                PreparedFigure.load(args.prepared / figure["prepared"]).caption or ""
            ).strip()
            if args.caption and caption:
                prompt += CAPTION.format(caption=caption)
            try:
                reply, meta = asker.ask(Ruling, prompt, drawings, "ruling")
                row.update(
                    same=False,
                    first=order[0],
                    charts=reply.charts,
                    first_is_right=reply.first_is_right,
                    picked=order[0] if reply.first_is_right else order[1],
                    **meta,
                )
            except (OllamaError, EndpointError, ValueError) as exc:
                row.update(same=False, error=str(exc)[:300])
        rows[figure_id] = row
        target.write_text(
            json.dumps({"ruling": args.name, "about": about, "figures": rows}, indent=1)
            + "\n",
            encoding="utf-8",
        )
        print(
            figure_id,
            "same" if row.get("same") else f"{row['boxes']} first={row.get('first')}",
            row.get("charts", ""),
            row.get("picked", ""),
            row.get("seconds", ""),
            row.get("cost_usd", ""),
            row.get("error", ""),
            flush=True,
        )
    asker.close()


if __name__ == "__main__":
    main()
