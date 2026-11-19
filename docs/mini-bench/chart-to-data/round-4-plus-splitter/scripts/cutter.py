"""Model boxes as seeds for the rule splitter's own cutter.

A detector or a vision model says where the charts of a figure are; its
boxes are rarely exact enough to crop by (a clipped tick label, a strip of
the neighbour). The splitter of the prepare phase already knows how to cut
a figure between seeds: along the widest ink-free band, each cell then
trimmed to its ink. This applies that cutter to any set of boxes.

    uv run --no-sync python .../scripts/cutter.py --prepared <prepared folders> <candidate> ...

writes ``candidates/<candidate>-cut.json`` for each candidate named.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from common import figures, image_path, read_candidate, to_grid, to_px, write_candidate
from PIL import Image

# The cutter is private to the splitter; the check borrows it as it is.
from docling.engines.figure_data.panels import _cut_between, _ink_box, _Seed, ink_mask
from docling.engines.figure_data.prepare import PreparedFigure

FALLBACK_TEXT_HEIGHT = 0.015  # of the figure's height, when it has no words


def text_height(prepared: PreparedFigure) -> float:
    heights = [w.bbox[3] - w.bbox[1] for w in prepared.words]
    return (
        float(np.median(heights)) if heights else FALLBACK_TEXT_HEIGHT * prepared.height
    )


def cut(boxes: list[list[float]], pixels: np.ndarray, size: float) -> list[list[float]]:
    """One ink-trimmed cell per box, cut along the free bands between
    them; the boxes themselves when no straight cut separates them."""
    height, width = pixels.shape[:2]
    full = (0.0, 0.0, float(width), float(height))
    if len(boxes) < 2:
        return [list(full)]
    mask = ink_mask(pixels)
    for shrink in (0.0, 0.03, 0.08):
        seeds = [
            _Seed(
                (
                    b[0] + shrink * (b[2] - b[0]),
                    b[1] + shrink * (b[3] - b[1]),
                    b[2] - shrink * (b[2] - b[0]),
                    b[3] - shrink * (b[3] - b[1]),
                ),
                (True, True),
            )
            for b in boxes
        ]
        cells = _cut_between(seeds, full, mask, size)
        if cells is not None:
            trimmed = [list(_ink_box(mask, cell)) for cell in cells]
            return sorted(trimmed, key=lambda b: (round(b[1] / (0.1 * height)), b[0]))
    return boxes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("candidates", nargs="+")
    args = parser.parse_args()
    for name in args.candidates:
        rows = read_candidate(name)
        out: dict[str, dict] = {}
        for figure in figures():
            row = rows.get(figure["id"], {})
            image = Image.open(image_path(figure)).convert("RGB")
            boxes = [to_px(b, image.width, image.height) for b in row.get("boxes", [])]
            prepared = PreparedFigure.load(args.prepared / figure["prepared"])
            cells = (
                cut(boxes, np.asarray(image), text_height(prepared)) if boxes else []
            )
            out[figure["id"]] = {
                "boxes": [to_grid(b, image.width, image.height) for b in cells],
                "seconds": row.get("seconds"),
                "cost_usd": row.get("cost_usd"),
            }
        write_candidate(
            f"{name}-cut",
            f"The boxes of {name} as seeds of the rule splitter's cutter: the figure "
            "is cut along the widest ink-free band between two seeds and every cell "
            "trimmed to its ink.",
            out,
        )
        print(name, "cut")


if __name__ == "__main__":
    main()
