"""Build the panel-splitter check: how well ``split_panels`` cuts figures into
their charts.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-3/splitter-page/build.py \\
        --truth <copy of truth/> --prepared <prepared bench folders> \\
        --wide <prepared folders of other papers> --out <page.html> \\
        [--flags flags.json]

This is the check of round 3 and runs with the engine of that time
(release ``extrct_docling-v2.131.0-r4`` or earlier): it calls
``split_panels`` with ``expect``, which the chart list of release r5
replaced (``panels.cut_from_list``; ``round-4-plus-splitter/`` measures it).

Scored part: the 15 bench figures. Each prepared figure (``evidence.json``
and ``figure.png``, as ``amir-figdata prepare`` writes them) is split in the
three modes of the splitter, ``auto`` (tick-label axes, then gutters),
``gutters`` (the round-1 splitter) and ``off``, and once more in ``auto``
with the number of charts given (``count``: the measured engine takes that
number from the model's first call; here the truth's stands in for it). The
boxes are matched to the truth's panel boxes the way the scorer does (IoU
of at least 0.5; a single chart on both sides always pairs).

Unscored part: every other prepared figure under ``--wide`` (made with
``amir-figdata prepare <bundles> --out <wide>``): how many charts the
splitter finds and by which method, with the boxes drawn for a look by eye.
``--flags`` (default: ``flags.json`` beside this script) records that look:
``{"<bundle>/<pictures_N>": [grade, note]}`` with grade ``clean``, ``minor``,
``wrong`` or ``not_chart``.

Writes ``results.json`` beside this script (numbers only) and the page,
which embeds the papers' figures: the page stays out of the repository and
is shared only privately.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from docling.engines.figure_data.panels import PanelSplitResult, split_panels
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.schema import Panel
from docling.engines.figure_data.scoring import match_panels

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
MODES = ("auto", "gutters", "off")
SCORED = ("auto", "count", "gutters", "off")
THUMB_SIDE = 900


def iou(a: list[float], b: list[float]) -> float:
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, right - left) * max(0.0, bottom - top)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def pairs(truth: list[list[float]], found: list[list[float]]) -> list[float]:
    """The IoU of each truth box and the found box the scorer pairs it
    with (crop pixels)."""
    matched = match_panels(
        [Panel(id=f"t{i}", bbox_px=box) for i, box in enumerate(truth)],
        [Panel(id=f"p{i}", bbox_px=box) for i, box in enumerate(found)],
    )
    return [round(iou(t.bbox_px, p.bbox_px), 3) for t, p in matched]


def jpeg(image: Image.Image) -> str:
    image = image.convert("RGB")
    if max(image.size) > THUMB_SIDE:
        ratio = THUMB_SIDE / max(image.size)
        image = image.resize(
            (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=74, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def split_all(
    figure_dir: Path, expect: int | None = None
) -> tuple[PreparedFigure, Image.Image, dict[str, dict]]:
    """The figure split in every mode; with *expect*, also in ``auto`` with
    that number of charts given (``count``)."""
    prepared = PreparedFigure.load(figure_dir)
    with Image.open(figure_dir / prepared.image) as opened:
        image = opened.convert("RGB")
    pixels = np.asarray(image)
    modes: dict[str, dict] = {}
    for mode in MODES:
        split = split_panels(pixels, prepared.words, mode=mode)
        modes[mode] = _mode(split)
    if expect is not None:
        modes["count"] = _mode(
            split_panels(pixels, prepared.words, mode="auto", expect=expect)
            if expect > 1
            else split_panels(pixels, prepared.words, mode="auto")
        )
    return prepared, image, modes


def _mode(split: PanelSplitResult) -> dict:
    return {
        "method": split.method,
        "notes": split.notes,
        "boxes": [[round(v, 1) for v in panel.bbox] for panel in split.panels],
        "ids": [panel.id for panel in split.panels],
    }


def figure_table() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in (BENCH / "FIGURES.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split(" | ")]
        if len(cells) >= 7 and cells[0].startswith("| ") and cells[0][2:3] in "ABC":
            rows[cells[0][2:].strip()] = cells
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--wide", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--flags", type=Path)
    args = parser.parse_args()

    testset = json.loads((BENCH / "testset.json").read_text(encoding="utf-8"))
    described = figure_table()
    flag_file = args.flags or HERE / "flags.json"
    flags = (
        json.loads(flag_file.read_text(encoding="utf-8")) if flag_file.is_file() else {}
    )

    bench: list[dict] = []
    bench_keys: set[tuple[str, str]] = set()
    for spec in testset["figures"]:
        bundle = Path(spec["bundle"]).name
        stem = spec["self_ref"].lstrip("#/").replace("/", "_")
        bench_keys.add((bundle, stem))
        truth = json.loads((args.truth / f"{bundle}__{stem}.json").read_text())
        truth_boxes = [panel["bbox_px"] for panel in truth.get("panels", [])]
        prepared, image, modes = split_all(
            args.prepared / bundle / "figure-to-data" / stem, expect=len(truth_boxes)
        )
        scale = prepared.px_per_crop
        stored = [[round(v, 1) for v in panel.bbox] for panel in prepared.panels]
        assert stored == modes["auto"]["boxes"], (spec["id"], "prepare differs")
        for mode in SCORED:
            found = [[v / scale for v in box] for box in modes[mode]["boxes"]]
            ious = pairs(truth_boxes, found) if truth_boxes else []
            modes[mode].update(
                found=len(found),
                matched=len(ious),
                ious=ious,
                extra=max(0, len(found) - len(ious)) if truth_boxes else None,
            )
        cells = described[spec["id"]]
        bench.append(
            {
                "id": spec["id"],
                "bundle": bundle,
                "stem": stem,
                "paper": cells[1],
                "figure": cells[3],
                "page": cells[4],
                "shows": spec["expected_kind"],
                "hasData": bool(truth_boxes),
                "truth": len(truth_boxes),
                "truthBoxes": [
                    [round(v * scale, 1) for v in box] for box in truth_boxes
                ],
                "size": [image.width, image.height],
                "kind": prepared.source_kind,
                "words": len(prepared.words),
                "modes": modes,
                "img": jpeg(image),
            }
        )

    wide: list[dict] = []
    skipped: list[str] = []
    for manifest_path in sorted(args.wide.glob("*/figure-to-data/prepare.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bundle = manifest["bundle"]
        for row in manifest["figures"]:
            if row["status"] != "prepared":
                if "not typed" not in (row.get("reason") or "") and "noise" not in (
                    row.get("reason") or ""
                ):
                    skipped.append(f"{bundle} {row['self_ref']}: {row.get('reason')}")
                continue
            if (bundle, row["folder"]) in bench_keys:
                continue
            prepared, image, modes = split_all(manifest_path.parent / row["folder"])
            wide.append(
                {
                    "key": f"{bundle}/{row['folder']}",
                    "bundle": bundle,
                    "stem": row["folder"],
                    "page": prepared.figure.page,
                    "type": prepared.figure_type,
                    "caption": (prepared.caption or "")[:160],
                    "size": [image.width, image.height],
                    "kind": prepared.source_kind,
                    "words": len(prepared.words),
                    "charts": len(modes["auto"]["boxes"]),
                    "method": modes["auto"]["method"],
                    "gutters": len(modes["gutters"]["boxes"]),
                    "guttersMethod": modes["gutters"]["method"],
                    "boxes": modes["auto"]["boxes"],
                    "guttersBoxes": modes["gutters"]["boxes"],
                    "grade": (flags.get(f"{bundle}/{row['folder']}") or [None])[0],
                    "flag": (flags.get(f"{bundle}/{row['folder']}") or [None, None])[1],
                    "image": image,
                }
            )

    data = [f for f in bench if f["hasData"]]
    totals = {}
    for mode in SCORED:
        totals[mode] = {
            "truth": sum(f["truth"] for f in data),
            "found": sum(f["modes"][mode]["found"] for f in data),
            "matched": sum(f["modes"][mode]["matched"] for f in data),
            "extra": sum(f["modes"][mode]["extra"] for f in data),
            "figuresComplete": sum(
                f["modes"][mode]["matched"] == f["truth"]
                and f["modes"][mode]["found"] == f["truth"]
                for f in data
            ),
            "meanIou": round(
                float(
                    np.mean([v for f in data for v in f["modes"][mode]["ious"]] or [0])
                ),
                3,
            ),
            "minIou": min(
                (v for f in data for v in f["modes"][mode]["ious"]), default=None
            ),
        }
    # Every figure of the wide set is shown: the page stays well under the
    # size limit at this resolution.
    gallery = wide
    grades = Counter(w["grade"] or "ungraded" for w in wide)
    wide_summary = {
        "figures": len(wide),
        "papers": len({w["bundle"] for w in wide}),
        "byCharts": dict(sorted(Counter(w["charts"] for w in wide).items())),
        "byMethod": dict(Counter(w["method"] for w in wide).most_common()),
        "byGuttersCharts": dict(sorted(Counter(w["gutters"] for w in wide).items())),
        "modesDisagree": sum(w["charts"] != w["gutters"] for w in wide),
        "moreWithAxes": sum(w["charts"] > w["gutters"] for w in wide),
        "fewerWithAxes": sum(w["charts"] < w["gutters"] for w in wide),
        "shown": len(gallery),
        "byGrade": {
            grade: grades.get(grade, 0)
            for grade in ("clean", "minor", "wrong", "not_chart", "ungraded")
            if grades.get(grade, 0)
        },
        "dataFigures": len(wide) - grades.get("not_chart", 0),
        "notPrepared": skipped,
    }
    results = {
        "bench": [
            {
                key: (
                    {
                        mode: {
                            k: v[k]
                            for k in ("method", "found", "matched", "extra", "ious")
                        }
                        for mode, v in figure["modes"].items()
                    }
                    if key == "modes"
                    else figure[key]
                )
                for key in ("id", "bundle", "stem", "hasData", "truth", "kind", "modes")
            }
            for figure in bench
        ],
        "totals": totals,
        "wide": wide_summary,
        "wideFigures": [
            {
                k: w[k]
                for k in (
                    "key",
                    "page",
                    "type",
                    "kind",
                    "charts",
                    "method",
                    "gutters",
                    "guttersMethod",
                    "grade",
                    "flag",
                )
            }
            for w in wide
        ],
    }
    (HERE / "results.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for entry in gallery:
        entry["img"] = jpeg(entry["image"])
    blob = {
        "bench": bench,
        "totals": totals,
        "wide": wide_summary,
        "gallery": [
            {k: v for k, v in entry.items() if k != "image"} for entry in gallery
        ],
        "wideRows": results["wideFigures"],
        "text": json.loads((HERE / "text.json").read_text(encoding="utf-8")),
    }
    template = (HERE / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(blob, ensure_ascii=False).replace("</", "<\\/")
    args.out.write_text(template.replace("/*__DATA__*/", payload), encoding="utf-8")
    print(json.dumps({"totals": totals, "wide": wide_summary}, indent=1))
    for figure in bench:
        line = " | ".join(
            f"{mode}: {figure['modes'][mode]['found']} found, "
            f"{figure['modes'][mode]['matched']} matched ({figure['modes'][mode]['method']})"
            for mode in SCORED
        )
        print(f"{figure['id']} truth {figure['truth']} | {line}")
    print(args.out, f"{args.out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
