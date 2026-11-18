# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""What the engine knows about each bench figure before it asks a model.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/probe_evidence.py <work dir>

Per figure: the work image's size, where its words come from (PDF text
layer or OCR), how the splitter cuts it, and per panel the words inside it
and the axes calibrated from them. No model is called. A panel without a
numeric axis is one whose values will be the model's own estimates.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from docling.engines.figure_data.evidence import (
    AxisMap,
    build_job,
    find_axes,
    load_bundle,
    words_in,
)
from docling.engines.figure_data.panels import split_panels

BENCH = Path(__file__).resolve().parents[1]


def describe(axis: AxisMap | None) -> str:
    return "none" if axis is None else f"{axis.scale}, {len(axis.ticks)} ticks"


def main() -> None:
    work = Path(sys.argv[1])
    testset = json.loads((BENCH / "testset.json").read_text(encoding="utf-8"))
    for figure in testset["figures"]:
        bundle = load_bundle(Path(figure["bundle"]), Path(figure["pdf"]))
        job = build_job(bundle, figure["self_ref"], work_dir=work, crop_dpi=220)
        image = Image.open(job.image_path).convert("RGB")
        sources = dict(collections.Counter(w.source for w in job.words))
        split = split_panels(np.asarray(image), job.words)
        print(f"\n== {figure['id']} {figure['expected_kind']}")
        print(
            f"   image {image.size}, {job.source_kind}, words {sources}, "
            f"{len(job.marks)} vector marks"
        )
        print(f"   split: {split.method}, {len(split.panels)} panel(s) {split.notes}")
        for panel in split.panels:
            words = words_in(job.words, panel.bbox)
            axes = find_axes(words, panel.bbox)
            x0, y0, x1, y1 = panel.bbox
            print(
                f"     panel {panel.id}: {round(x1 - x0)} x {round(y1 - y0)} px, "
                f"{len(words)} words, x axis {describe(axes.x)}, "
                f"y axis {describe(axes.y)}"
            )


if __name__ == "__main__":
    main()
