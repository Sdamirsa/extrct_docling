# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Answers of a blind agent run (one ``<figure id>.json`` per figure, the
format of ``round-2/sonnet/PROMPT.md``) as figure-data JSON in the bench's
run layout, so the same scorer and judge apply.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/import_agent_answers.py \
        <answers dir> <work images dir> <run folder> "<labeler name>"

The agent boxed its panels in pixels of the work image it was given; the
bench's panels are in pixels of the bundle crop, so boxes are scaled by the
ratio of the two widths. Nothing else is changed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from docling.engines.figure_data.schema import ChartData, Labeler, Panel

BENCH = Path(__file__).resolve().parents[1]


def main() -> None:
    answers, images, out = (Path(arg) for arg in sys.argv[1:4])
    testset = json.loads((BENCH / "testset.json").read_text(encoding="utf-8"))
    for figure in testset["figures"]:
        bundle = Path(figure["bundle"])
        stem = figure["self_ref"].lstrip("#/").replace("/", "_")
        truth = ChartData.model_validate_json(
            (BENCH / "truth" / f"{bundle.name}__{stem}.json").read_text(
                encoding="utf-8"
            )
        )
        answer = json.loads(
            (answers / f"{figure['id']}.json").read_text(encoding="utf-8")
        )
        with Image.open(images / f"{figure['id']}.png") as work:
            work_width = work.width
        with Image.open(bundle / figure["image_path"]) as crop:
            scale = crop.width / work_width
        panels = [
            Panel.model_validate(
                {**panel, "bbox_px": [round(v * scale, 1) for v in panel["bbox_px"]]}
            )
            for panel in answer.get("panels", [])
        ]
        chart = ChartData(
            figure=truth.figure,
            source_kind="raster",
            panels=panels,
            labeler=Labeler(kind="agent", name=sys.argv[4], date="2026-11-17"),
            uncertain=answer.get("uncertain", []),
        )
        target = out / "all" / bundle.name / f"{stem}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(chart.dump(), indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print("wrote", out)


if __name__ == "__main__":
    main()
