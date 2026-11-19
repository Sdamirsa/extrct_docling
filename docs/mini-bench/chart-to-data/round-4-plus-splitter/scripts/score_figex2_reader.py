"""Count the values FigEx2's captioning model read, the way round 4 counted
them for its four reading methods.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/score_figex2_reader.py

Reads ``extra/figex2-captioner-as-reader.json`` (``probe_figex2_reader.py``)
and the truth of round 4 for the six main figures of the showcase paper
(573 values). A table row of the model becomes a value of the bench's
reading format, a chart per value of its ``chart`` column, and the count is
round 4's own: values paired by their printed name after the charts are
put where the truth has them, right when within 5 % of the axis range
(``scripts/compare_bundles.py``: ``with_truth_boxes``, ``hits``). The
numbers of the four round-4 runs are taken from
``round-4/metrics/pipeline.json`` (Figure 6 as read again after the capture
fix, which is the image the captioning model was given).

Not a run of the step: one plain question per figure, no prepared context,
no crops, no checks. Writes ``extra/figex2-reader-score.json``.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from common import BENCH, ROUND

os.environ.setdefault("BENCH_ROUND", "round-4")
sys.path.insert(0, str(BENCH / "scripts"))

from analyze import load_charts
from compare_bundles import hits, with_truth_boxes

from docling.engines.figure_data.schema import ChartData, Panel, Value

BUNDLE = "Public-test-manuscript"
RUNS = {
    "ollama-gemma4-26b-qat": "ollama, Gemma 4 26B",
    "cloud-sonnet-5-5": "cloud, Sonnet 5.5",
    "cloud-gemini-3-8-flash": "cloud, Gemini 3.8 Flash",
    "agent-sonnet-5-5": "agent, Sonnet 5.5",
}
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_SPECIAL = re.compile(r"<\|.*?\|>|\[DET\]")


def rows_of(reply: str) -> list[tuple[str, str, str, float]]:
    """``(chart, category, series, value)`` of every table row with a number."""
    rows = []
    for line in _SPECIAL.sub("", reply).splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or set(cells[0]) <= set("-: "):
            continue
        number = _NUMBER.search(cells[3].replace(",", ""))
        if number is None:
            continue
        rows.append((cells[0], cells[1], cells[2], float(number.group())))
    return rows


def as_chart(rows: list[tuple[str, str, str, float]], truth: ChartData) -> ChartData:
    whole = [
        min(p.bbox_px[0] for p in truth.panels),
        min(p.bbox_px[1] for p in truth.panels),
        max(p.bbox_px[2] for p in truth.panels),
        max(p.bbox_px[3] for p in truth.panels),
    ]
    panels: dict[str, Panel] = {}
    for chart, category, series, value in rows:
        panel = panels.setdefault(
            chart.casefold(), Panel(id=chart.casefold() or "1", bbox_px=whole)
        )
        panel.data.append(Value(category=category, series=series or None, value=value))
    return ChartData(panels=list(panels.values()))


def main() -> None:
    replies = json.loads(
        (ROUND / "extra" / "figex2-captioner-as-reader.json").read_text(
            encoding="utf-8"
        )
    )["figures"]
    truth = load_charts(BENCH / "round-4" / "truth")
    pipeline = json.loads(
        (BENCH / "round-4" / "metrics" / "pipeline.json").read_text(encoding="utf-8")
    )
    earlier = {f["id"]: f for f in pipeline["figures"]}
    table = []
    for figure_id, answer in replies.items():
        number = int(figure_id[1:])
        chart = truth[BUNDLE, f"#/pictures/{number}"]
        rows = rows_of(answer["asked_for_values"])
        score = hits(chart, with_truth_boxes(chart, as_chart(rows, chart)))
        wanted = sum(len(p.data) for p in chart.panels)
        others = {}
        for label in RUNS:
            cell = earlier[figure_id]["runs"][label]
            others[label] = cell.get("after_fix", cell["score"])["within_5_by_name"]
        table.append(
            {
                "id": figure_id,
                "truth_values": wanted,
                "figex2_returned": len(rows),
                "figex2_right": score["within_5"],
                "round4_right": others,
            }
        )
    total = {
        "truth_values": sum(r["truth_values"] for r in table),
        "figex2_returned": sum(r["figex2_returned"] for r in table),
        "figex2_right": sum(r["figex2_right"] for r in table),
        "round4_right": {
            label: sum(r["round4_right"][label] for r in table) for label in RUNS
        },
    }
    (ROUND / "extra" / "figex2-reader-score.json").write_text(
        json.dumps({"figures": table, "total": total}, indent=1) + "\n",
        encoding="utf-8",
    )
    print(
        "| Figure | Values | FigEx2 captioning model: returned | right | "
        + " | ".join(RUNS.values())
        + " |"
    )
    print("|---|---|---|---|" + "---|" * len(RUNS))
    for row in [*table, {"id": "All six", **total}]:
        print(
            f"| {row['id']} | {row['truth_values']} | {row['figex2_returned']} | "
            f"{row['figex2_right']} | "
            + " | ".join(str(row["round4_right"][label]) for label in RUNS)
            + " |"
        )


if __name__ == "__main__":
    main()
