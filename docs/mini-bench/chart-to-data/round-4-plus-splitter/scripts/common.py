"""Shared pieces of the split check: where its files are and how boxes are
written. Every box in this folder is ``[x0, y0, x1, y1]`` on a 0-1000 grid
of the figure image (x from the left, y from the top)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROUND = Path(__file__).resolve().parents[1]
BENCH = ROUND.parent
GRID = 1000.0

Box = list[float]


def figures() -> list[dict[str, Any]]:
    return json.loads((ROUND / "figures.json").read_text(encoding="utf-8"))["figures"]


def image_path(figure: dict[str, Any]) -> Path:
    return ROUND / "figures" / f"{figure['id']}.png"


def to_grid(box: Box, width: float, height: float) -> Box:
    x0, y0, x1, y1 = box
    return [
        round(min(max(x0 / width, 0.0), 1.0) * GRID, 1),
        round(min(max(y0 / height, 0.0), 1.0) * GRID, 1),
        round(min(max(x1 / width, 0.0), 1.0) * GRID, 1),
        round(min(max(y1 / height, 0.0), 1.0) * GRID, 1),
    ]


def to_px(box: Box, width: float, height: float) -> Box:
    x0, y0, x1, y1 = box
    return [
        x0 / GRID * width,
        y0 / GRID * height,
        x1 / GRID * width,
        y1 / GRID * height,
    ]


def area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def overlap(a: Box, b: Box) -> float:
    return area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])


def iou(a: Box, b: Box) -> float:
    inter = overlap(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


def write_candidate(name: str, about: str, rows: dict[str, dict[str, Any]]) -> Path:
    """``candidates/<name>.json``: what one splitter found, per figure
    (``boxes`` on the 0-1000 grid, anything else it reported beside)."""
    path = ROUND / "candidates" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"candidate": name, "about": about, "figures": rows},
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def read_candidate(name: str) -> dict[str, dict[str, Any]]:
    path = ROUND / "candidates" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))["figures"]
