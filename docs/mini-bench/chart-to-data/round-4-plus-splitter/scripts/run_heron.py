"""Split the figures with Docling's own page-layout detector.

    uv run --no-sync python .../scripts/run_heron.py --prepared <prepared folders>

Heron (``docling-project/docling-layout-heron``, an RT-DETR detector, the
conversion's default layout model) is trained to find the blocks of a
page. Here it is run on one figure image at a time, and its ``picture``
boxes are read as the charts of the figure. Two rules turn the boxes into
charts, both fixed before this check on the 11 figures of the showcase
paper: a box under 2 % of the figure is dropped (the rule splitter's own
minimum), and a box that holds other boxes is a group, not a chart.

Writes two candidates:

- ``heron``: the detector's boxes as they are;
- ``heron-cut``: the boxes as seeds for the rule splitter's own cutter,
  which cuts the figure along the widest ink-free band between two seeds
  and trims each cell to its ink. This is how the detector would be wired
  into the prepare phase: the model says where the charts are, the rules
  make the crops.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import torch
from common import figures, image_path, overlap, to_grid, write_candidate
from cutter import cut, text_height
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForObjectDetection

from docling.engines.figure_data.prepare import PreparedFigure

REPO = "docling-project/docling-layout-heron"
THRESHOLD = 0.3
MIN_AREA = 0.02


def _area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def leaves(boxes: list[list[float]], width: int, height: int) -> list[list[float]]:
    """The picture boxes that are charts: large enough, holding no other."""
    kept = [b for b in boxes if _area(b) >= MIN_AREA * width * height]
    alone = [
        b
        for b in kept
        if not any(o is not b and overlap(o, b) >= 0.8 * _area(o) for o in kept)
    ]
    return sorted(alone, key=lambda b: (round(b[1] / (0.1 * height)), b[0]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoImageProcessor.from_pretrained(REPO)
    model = AutoModelForObjectDetection.from_pretrained(REPO).to(device).eval()
    names = model.config.id2label

    plain: dict[str, dict] = {}
    with_cut: dict[str, dict] = {}
    for figure in figures():
        image = Image.open(image_path(figure)).convert("RGB")
        started = time.perf_counter()
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        found = processor.post_process_object_detection(
            outputs, target_sizes=[(image.height, image.width)], threshold=THRESHOLD
        )[0]
        seconds = round(time.perf_counter() - started, 3)
        pictures = [
            (float(score), [float(v) for v in box])
            for label, score, box in zip(
                found["labels"].tolist(),
                found["scores"].tolist(),
                found["boxes"].tolist(),
            )
            if names[int(label)] == "picture"
        ]
        charts = leaves([box for _, box in pictures], image.width, image.height)
        # No chart-sized box at all: the figure is taken as one chart.
        whole = [0.0, 0.0, float(image.width), float(image.height)]
        charts = charts or [whole]
        plain[figure["id"]] = {
            "boxes": [to_grid(b, image.width, image.height) for b in charts],
            "seconds": seconds,
            "picture_boxes": [
                {
                    "score": round(score, 3),
                    "box": to_grid(box, image.width, image.height),
                }
                for score, box in pictures
            ],
        }
        prepared = PreparedFigure.load(args.prepared / figure["prepared"])
        cells = cut(charts, np.asarray(image), text_height(prepared))
        with_cut[figure["id"]] = {
            "boxes": [to_grid(b, image.width, image.height) for b in cells],
            "seconds": seconds,
        }
        print(figure["id"], len(charts), len(cells), flush=True)
    write_candidate(
        "heron",
        f"{REPO} run on the figure image; its picture boxes over 2 % of the "
        f"figure that hold no other box (score threshold {THRESHOLD}).",
        plain,
    )
    write_candidate(
        "heron-cut",
        "The heron boxes as seeds of the rule splitter's cutter: the figure is "
        "cut along the widest ink-free band between two seeds and every cell "
        "trimmed to its ink.",
        with_cut,
    )


if __name__ == "__main__":
    main()
