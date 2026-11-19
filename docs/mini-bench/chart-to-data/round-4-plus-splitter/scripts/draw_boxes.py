"""Draw the boxes of one figure's JSON file on the figure, to check them by
eye. Stands alone (Pillow only), so it can be copied beside a set of images.

    python draw_boxes.py <id> [<id> ...]

Run with a folder that holds ``images/<id>.png`` and ``<id>.json`` as the
script's own folder. The JSON holds ``{"charts": [{"label": "a", "box":
[x0, y0, x1, y1]}]}`` with boxes on a 0-1000 grid of the image (x from the
left, y from the top). Writes ``check/<id>.png``, the whole figure with
every box drawn and numbered, and ``check/<id>-<n>.png``, one enlarged
view per box with some of the figure around it, so that a clipped label or
a piece of the neighbour shows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
COLOURS = ["#eb6834", "#2a78d6", "#1f9d55", "#b23ac7", "#c79a00", "#d63a5e"]
MARGIN = 0.05  # of the figure's side, shown around a box in its own view
VIEW_SIDE = 1100


def draw(figure_id: str) -> None:
    record = json.loads((HERE / f"{figure_id}.json").read_text(encoding="utf-8"))
    image = Image.open(HERE / "images" / f"{figure_id}.png").convert("RGB")
    width, height = image.size
    boxes = [
        [
            chart["box"][0] / 1000 * width,
            chart["box"][1] / 1000 * height,
            chart["box"][2] / 1000 * width,
            chart["box"][3] / 1000 * height,
        ]
        for chart in record.get("charts", [])
    ]
    out = HERE / "check"
    out.mkdir(exist_ok=True)
    for old in out.glob(f"{figure_id}-*.png"):
        old.unlink()
    line = max(3, max(width, height) // 300)
    font = ImageFont.load_default(size=max(16, max(width, height) // 45))
    whole = image.copy()
    pen = ImageDraw.Draw(whole)
    for number, box in enumerate(boxes, start=1):
        colour = COLOURS[(number - 1) % len(COLOURS)]
        pen.rectangle(box, outline=colour, width=line)
        tag = str(number)
        size = pen.textbbox((0, 0), tag, font=font)
        pen.rectangle(
            [box[0], box[1], box[0] + size[2] + 2 * line, box[1] + size[3] + 2 * line],
            fill=colour,
        )
        pen.text((box[0] + line, box[1] + line // 2), tag, fill="#ffffff", font=font)
    whole.thumbnail((1600, 1600))
    whole.save(out / f"{figure_id}.png")
    for number, box in enumerate(boxes, start=1):
        pad_x, pad_y = MARGIN * width, MARGIN * height
        view_box = (
            max(0, round(box[0] - pad_x)),
            max(0, round(box[1] - pad_y)),
            min(width, round(box[2] + pad_x)),
            min(height, round(box[3] + pad_y)),
        )
        view = image.crop(view_box)
        pen = ImageDraw.Draw(view)
        pen.rectangle(
            [
                box[0] - view_box[0],
                box[1] - view_box[1],
                box[2] - view_box[0],
                box[3] - view_box[1],
            ],
            outline=COLOURS[(number - 1) % len(COLOURS)],
            width=max(2, line // 2),
        )
        scale = VIEW_SIDE / max(view.size)
        if scale > 1:
            view = view.resize(
                (round(view.width * scale), round(view.height * scale)),
                Image.Resampling.LANCZOS,
            )
        else:
            view.thumbnail((VIEW_SIDE, VIEW_SIDE))
        view.save(out / f"{figure_id}-{number}.png")
    print(f"{figure_id}: {len(boxes)} box(es) drawn, image {width} x {height} px")


if __name__ == "__main__":
    for name in sys.argv[1:]:
        draw(name)
