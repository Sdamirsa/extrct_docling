"""Hand the figures to the truth agents blind, and take their boxes back.

    uv run --no-sync python .../scripts/truth_parts.py make <work dir> [parts]
    uv run --no-sync python .../scripts/truth_parts.py collect <work dir>

``make`` gives every figure a neutral id (T01, ...) in a shuffled order,
deals them into ``parts`` folders (default 4) under the work folder, each
with ``images/``, ``draw_boxes.py`` and the brief (``truth/PROMPT.md`` with
the folder filled in), and writes ``<work dir>/mapping.json``. The work
folder lies outside the repository; a part folder holds nothing that says
which figure of which paper an image is, and no result of any splitter.

``collect`` writes ``truth/<figure id>.json`` from the agents' files.
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

from common import ROUND, figures, image_path

SEED = 20261119


def make(work: Path, parts: int) -> None:
    rows = figures()
    order = list(range(len(rows)))
    random.Random(SEED).shuffle(order)
    brief = (ROUND / "truth" / "PROMPT.md").read_text(encoding="utf-8")
    mapping: dict[str, dict[str, str]] = {}
    for position, index in enumerate(order):
        figure = rows[index]
        blind = f"T{position + 1:02d}"
        part = work / f"part-{chr(ord('A') + position % parts)}"
        (part / "images").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image_path(figure), part / "images" / f"{blind}.png")
        mapping[blind] = {"figure": figure["id"], "part": part.name}
    for part in sorted(work.glob("part-*")):
        shutil.copyfile(ROUND / "scripts" / "draw_boxes.py", part / "draw_boxes.py")
        (part / "PROMPT.md").write_text(
            brief.replace("{folder}", str(part)), encoding="utf-8"
        )
    (work / "mapping.json").write_text(json.dumps(mapping, indent=1) + "\n")
    for part in sorted(work.glob("part-*")):
        names = sorted(p.stem for p in (part / "images").glob("*.png"))
        print(part, len(names), " ".join(names))


def collect(work: Path) -> None:
    mapping = json.loads((work / "mapping.json").read_text())
    missing = []
    for blind, entry in sorted(mapping.items()):
        source = work / entry["part"] / f"{blind}.json"
        if not source.is_file():
            missing.append(blind)
            continue
        record = json.loads(source.read_text(encoding="utf-8"))
        charts = [
            {
                "label": str(chart.get("label", n)),
                "box": [float(v) for v in chart["box"]],
            }
            for n, chart in enumerate(record.get("charts", []), start=1)
        ]
        (ROUND / "truth" / f"{entry['figure']}.json").write_text(
            json.dumps(
                {
                    "id": entry["figure"],
                    "charts": charts,
                    "not_chart": bool(record.get("not_chart", False)),
                    "note": record.get("note", ""),
                    "drawn_as": blind,
                },
                indent=1,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        f"{len(mapping) - len(missing)} of {len(mapping)} collected; missing: {missing}"
    )


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    else:
        collect(Path(sys.argv[2]))
