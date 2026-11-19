"""Build the figure set of the split check and record the cut the rule
splitter makes on it.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/build_set.py \\
        --prepared <prepared folders>

``--prepared`` holds the figures as the prepare phase writes them today:

    uv run --no-sync amir-figdata prepare samples/aca-papers_out \\
        samples/round-4-showcase/cloud-sonnet-5-5 --out <prepared folders>

Three groups of data figures, 51 in all:

- ``bench``: the 10 data figures of the 15-figure bench (rounds 1 to 3);
- ``showcase``: the 11 chart figures of the showcase paper (round 4);
- ``other``: the 30 data figures of other papers that round 3 looked at by
  eye (``round-3/splitter-page/flags.json``, every grade but ``not_chart``).

Writes ``figures.json``, copies each figure image to ``figures/<id>.png``
(the papers' artwork, git-ignored) and writes ``candidates/rules.json``:
the charts the prepare phase cut each figure into. The chart counts known
from earlier truth are kept in ``figures.json`` as a cross-check; the
truth of this check is drawn anew (``truth/``).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from common import BENCH, ROUND, to_grid, write_candidate

from docling.engines.figure_data.prepare import PreparedFigure

SHOWCASE = "Public-test-manuscript"
# Charts per dense supplementary figure: round-4/truth-sample/STRUCTURE.md.
SAMPLED = {"S10": 3, "S11": 11, "S12": 5, "S13": 4, "S14": 3}
_PANELS = re.compile(r"^S1[0-4]$")


def earlier_truth(path: Path) -> int | None:
    if not path.is_file():
        return None
    return len(json.loads(path.read_text(encoding="utf-8")).get("panels", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    args = parser.parse_args()

    rows: list[dict] = []
    for spec in json.loads((BENCH / "testset.json").read_text())["figures"]:
        bundle = Path(spec["bundle"]).name
        stem = spec["self_ref"].lstrip("#/").replace("/", "_")
        known = earlier_truth(BENCH / "truth" / f"{bundle}__{stem}.json")
        if known:
            rows.append(
                {
                    "id": spec["id"],
                    "group": "bench",
                    "bundle": bundle,
                    "picture": stem,
                    "known_charts": known,
                    "known_from": "truth/ (rounds 1 to 3)",
                }
            )
    for spec in json.loads((BENCH / "round-4" / "testset.json").read_text())["figures"]:
        stem = spec["self_ref"].lstrip("#/").replace("/", "_")
        known = earlier_truth(BENCH / "round-4" / "truth" / f"{SHOWCASE}__{stem}.json")
        source = "round-4/truth/"
        if known is None and _PANELS.match(spec["id"]):
            known, source = SAMPLED[spec["id"]], "round-4/truth-sample/STRUCTURE.md"
        if known:
            rows.append(
                {
                    "id": spec["id"],
                    "group": "showcase",
                    "bundle": SHOWCASE,
                    "picture": stem,
                    "known_charts": known,
                    "known_from": source,
                }
            )
    flags = json.loads(
        (BENCH / "round-3" / "splitter-page" / "flags.json").read_text(encoding="utf-8")
    )
    graded = sorted(key for key, (grade, _) in flags.items() if grade != "not_chart")
    for number, key in enumerate(graded, start=1):
        bundle, stem = key.split("/")
        rows.append(
            {
                "id": f"W{number:02d}",
                "group": "other",
                "bundle": bundle,
                "picture": stem,
                "known_charts": None,
                "known_from": None,
                "round3_grade_of_rules": flags[key][0],
            }
        )

    images = ROUND / "figures"
    images.mkdir(exist_ok=True)
    rules: dict[str, dict] = {}
    for row in rows:
        folder = args.prepared / row["bundle"] / "figure-to-data" / row["picture"]
        prepared = PreparedFigure.load(folder)
        shutil.copyfile(folder / prepared.image, images / f"{row['id']}.png")
        row.update(
            prepared=f"{row['bundle']}/figure-to-data/{row['picture']}",
            width=prepared.width,
            height=prepared.height,
            capture=prepared.capture,
            source_kind=prepared.source_kind,
            figure_type=prepared.figure_type,
        )
        rules[row["id"]] = {
            "boxes": [
                to_grid(list(panel.bbox), prepared.width, prepared.height)
                for panel in prepared.panels
            ],
            "labels": [panel.id for panel in prepared.panels],
            "method": prepared.split_method,
            "notes": prepared.split_notes,
        }
    (ROUND / "figures.json").write_text(
        json.dumps({"figures": rows}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_candidate(
        "rules",
        "The splitter of the prepare phase as it is today "
        "(docling/engines/figure_data/panels.py, mode auto): tick-label axes, "
        "then gutters and panel letters. No model.",
        rules,
    )
    by_group: dict[str, int] = {}
    for row in rows:
        by_group[row["group"]] = by_group.get(row["group"], 0) + 1
    print(f"{len(rows)} figures: {by_group}")


if __name__ == "__main__":
    main()
