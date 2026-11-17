# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Granite-Vision 4.1-4B ``<chart2csv>`` (upstream Docling's chart-extraction
stage, preset ``granite_vision_v4``) on the bench's figures.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/run_granite_vision.py

One figure per call, so each has its own time. The CSV the model returns is
kept as ``grid`` and also written as figure-data JSON (one panel; first
column = category, header = series) so the same scorer applies. Reads the
bundles, writes only under ``runs/granite-vision-4.1-4b/``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import torch
from docling_core.types.doc import DoclingDocument
from PIL import Image

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import ItemAndImageEnrichmentElement
from docling.datamodel.chart_extraction_options import ChartExtractionVlmEngineOptions
from docling.engines.figure_data.schema import ChartData, Figure, Panel, Value
from docling.models.stages.chart_extraction.granite_vision import (
    ChartExtractionVlmEngineModel,
)

BENCH = Path(__file__).resolve().parents[1]
OUT = BENCH / "runs" / "granite-vision-4.1-4b" / "all"


def number(text: str) -> float | None:
    cleaned = text.strip().rstrip("%").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def to_chart(grid: list[list[str]], figure: Figure, size: tuple[int, int]) -> ChartData:
    panel = Panel(id="1", bbox_px=[0, 0, size[0], size[1]])
    if grid:
        header = grid[0]
        for row in grid[1:]:
            for column, cell in enumerate(row[1:], start=1):
                value = number(cell)
                if value is not None:
                    panel.data.append(
                        Value(
                            category=row[0],
                            series=header[column] if column < len(header) else None,
                            value=value,
                            source="vlm",
                        )
                    )
    return ChartData(figure=figure, source_kind="raster", panels=[panel])


def main() -> None:
    testset = json.loads((BENCH / "testset.json").read_text(encoding="utf-8"))
    started = time.perf_counter()
    model = ChartExtractionVlmEngineModel(
        enabled=True,
        artifacts_path=None,
        options=ChartExtractionVlmEngineOptions.from_preset("granite_vision_v4"),
        accelerator_options=AcceleratorOptions(),
        enable_remote_services=False,
    )
    load_seconds = time.perf_counter() - started
    timing: list[dict] = []
    docs: dict[str, DoclingDocument] = {}
    for spec in testset["figures"]:
        bundle = Path(spec["bundle"])
        doc = docs.setdefault(
            spec["bundle"], DoclingDocument.load_from_json(bundle / "document.json")
        )
        item = next(p for p in doc.pictures if p.self_ref == spec["self_ref"])
        image = Image.open(bundle / spec["image_path"]).convert("RGB")
        start = time.perf_counter()
        list(model(doc, [ItemAndImageEnrichmentElement(item=item, image=image)]))
        seconds = time.perf_counter() - start
        chart = item.meta.tabular_chart if item.meta is not None else None
        grid = (
            [[cell.text for cell in row] for row in chart.chart_data.grid]
            if chart is not None
            else []
        )
        prov = item.prov[0]
        data = to_chart(
            grid,
            Figure(
                bundle=bundle.name,
                self_ref=spec["self_ref"],
                image_path=spec["image_path"],
                page=prov.page_no,
                bbox=list(prov.bbox.as_tuple()),
            ),
            image.size,
        )
        target = OUT / bundle.name
        target.mkdir(parents=True, exist_ok=True)
        stem = spec["self_ref"].lstrip("#/").replace("/", "_")
        (target / f"{stem}.json").write_text(json.dumps(data.dump(), indent=1))
        (target / f"{stem}.grid.json").write_text(json.dumps(grid, indent=1))
        timing.append(
            {
                "bundle": spec["bundle"],
                "self_ref": spec["self_ref"],
                "mode": "chart2csv",
                "model": "ibm-granite/granite-vision-4.1-4b",
                "rows": sum(len(panel.data) for panel in data.panels),
                "seconds": round(seconds, 2),
                "load_s": round(load_seconds, 2) if not timing else 0.0,
                "gpu_bytes": torch.cuda.max_memory_allocated()
                if torch.cuda.is_available()
                else None,
            }
        )
        print(spec["id"], f"{seconds:.1f}s", len(grid), "csv rows")
    (OUT / "timing.json").write_text(json.dumps(timing, indent=1))


if __name__ == "__main__":
    main()
