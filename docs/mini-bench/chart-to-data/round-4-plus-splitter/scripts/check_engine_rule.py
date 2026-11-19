"""Does the rule as built into the engine give the cuts the check measured?

    uv run --no-sync python .../scripts/check_engine_rule.py --prepared <prepared folders> [--list <candidate> ...]

The check scored the one rule from files (``score_one_rule.py``): the rule
splitter's stored cut, and the cutter of ``cutter.py`` run on each model's
stored chart list. The step now has the rule as one function,
``panels.cut_from_list``. This runs that function on the 51 figures with
the same stored lists and scores what it returns, beside the number the
check had. No model runs.

Writes ``final-test/engine-rule.json`` and prints a table.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from common import ROUND, figures, image_path, read_candidate, to_grid, to_px
from PIL import Image
from score import judge_figure, total

from docling.engines.figure_data.panels import cut_from_list
from docling.engines.figure_data.prepare import PreparedFigure

LISTS = ["gemma4-26b-qat", "sonnet-5-5", "gemini-3-8-flash"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--list", nargs="*", dest="lists", default=LISTS)
    args = parser.parse_args()
    measured = json.loads((ROUND / "extra" / "one-rule.json").read_text(encoding="utf-8"))
    out = {}
    print("| Chart list | Figures cut right, engine | as the check scored it | Charts whole | Rules' cut taken | Cut between the listed | Listed boxes as they are |")
    print("|---|---|---|---|---|---|---|")
    for name in args.lists:
        listed = read_candidate(name)
        judged, taken = [], {}
        for figure in figures():
            row = listed.get(figure["id"])
            if row is None or "error" in row:
                continue
            record = json.loads(
                (ROUND / "truth" / f"{figure['id']}.json").read_text(encoding="utf-8")
            )
            truth = [chart["box"] for chart in record["charts"]]
            image = Image.open(image_path(figure)).convert("RGB")
            prepared = PreparedFigure.load(args.prepared / figure["prepared"])
            boxes = [
                (label, tuple(to_px(box, image.width, image.height)))
                for label, box in zip(row.get("labels") or [], row["boxes"])
            ]
            split = cut_from_list(np.asarray(image), prepared.words, boxes)
            cells = [to_grid(list(p.bbox), image.width, image.height) for p in split.panels]
            result = judge_figure(truth, cells)
            judged.append(result)
            source = split.method if split.method.startswith("listed") else "rules"
            cell = taken.setdefault(source, {"figures": 0, "right": 0})
            cell["figures"] += 1
            cell["right"] += result["right"]
        score = total(judged)
        before = measured.get(name, {}).get("one_rule", {}).get("all", {}).get("right")
        out[name] = {"all": score, "taken": taken, "check": before}

        def cell_of(source: str) -> str:
            c = taken.get(source, {"figures": 0, "right": 0})
            return f"{c['figures']} ({c['right']} right)"

        print(
            f"| {name} | {score['right']} of {score['figures']} | {before} | "
            f"{score['held']} of {score['charts']} | {cell_of('rules')} | "
            f"{cell_of('listed')} | {cell_of('listed-boxes')} |"
        )
    (ROUND / "final-test" / "engine-rule.json").write_text(
        json.dumps(out, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
