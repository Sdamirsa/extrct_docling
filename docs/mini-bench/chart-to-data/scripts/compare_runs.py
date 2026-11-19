# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Score several run folders against the truth, side by side.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/compare_runs.py \
        label=<run folder> [label=<run folder> ...]

Per figure and run: values within 5 % of the axis range with names matched
(the series-lenient scorer of ``analyze.py``), the same with names ignored,
values returned, panels returned, seconds. The names-ignored count pairs
the sorted values of a truth panel with those of the predicted panel in
its place, so it tells a wrong number from a right number under another
name; it also lets chance matches through, and is an upper bound.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from analyze import load_charts, load_timing, round_file, series_lenient

from docling.engines.figure_data.schema import ChartData
from docling.engines.figure_data.scoring import match_panels, score_figure
from docling.engines.figure_data.verify import axis_span


def nameless_hits(truth: ChartData, pred: ChartData | None, share: float = 0.05) -> int:
    if pred is None:
        return 0
    hits = 0
    for truth_panel, pred_panel in match_panels(truth.panels, pred.panels):
        want = sorted(v.value for v in truth_panel.data if v.value is not None)
        have = sorted(v.value for v in pred_panel.data if v.value is not None)
        span = axis_span(truth_panel)
        width = span[1] - span[0] if span else (max(want) - min(want) if want else 0)
        tolerance = share * (width or 1.0)
        i = j = 0
        while i < len(want) and j < len(have):
            if abs(want[i] - have[j]) <= tolerance:
                hits += 1
                i += 1
                j += 1
            elif have[j] < want[i]:
                j += 1
            else:
                i += 1
    return hits


def main() -> None:
    runs = [arg.split("=", 1) for arg in sys.argv[1:]]
    testset = json.loads(round_file("testset.json").read_text(encoding="utf-8"))
    truth = load_charts(round_file("truth"))
    loaded = {
        label: (load_charts(Path(folder)), load_timing(Path(folder)))
        for label, folder in runs
    }
    print(
        f"{'fig':4}{'truth':>6}{'pan':>4} |"
        + "".join(f" {r[0][:22]:^22} |" for r in runs)
    )
    print(f"{'':14} |" + "".join(f" {'named any /ret pan    s':22} |" for _ in runs))
    totals = {label: [0, 0, 0, 0, 0, 0.0] for label, _ in runs}
    truth_values = no_data = 0
    for figure in testset["figures"]:
        key = (Path(figure["bundle"]).name, figure["self_ref"])
        chart = truth.get(key)
        if chart is None:
            # A figure of the test set that has no truth is not scored.
            continue
        wanted = sum(len(p.data) for p in chart.panels)
        truth_values += wanted
        no_data += not wanted
        line = f"{figure['id']:4}{wanted:6}{len(chart.panels):4} |"
        for label, _ in runs:
            preds, timing = loaded[label]
            pred = preds.get(key)
            score = score_figure(
                chart, series_lenient(chart, pred) if pred else ChartData()
            )
            loose = nameless_hits(chart, pred)
            seconds = timing.get(key, {}).get("seconds") or 0.0
            total = totals[label]
            if wanted:
                total[0] += score.hits_05
                total[1] += loose
                total[2] += score.pred_values
            else:
                total[3] += score.pred_values
                total[4] += 0 if score.pred_values else 1
            total[5] += seconds
            line += (
                f" {score.hits_05:5} {loose:3} /{score.pred_values:4}"
                f" {score.pred_panels:3} {seconds:4.0f} |"
            )
        print(line)
    print(
        f"\ntotals over the data charts ({truth_values} truth values) and the "
        f"{no_data} figures without data:"
    )
    for label, _ in runs:
        named, loose, returned, invented, empty, seconds = totals[label]
        print(
            f"  {label:24} within 5 %: {named:4} named, {loose:4} names ignored;"
            f" {returned:4} returned | no-data figures left empty {empty}/{no_data}"
            f" ({invented} values invented) | {seconds:5.0f} s"
        )


if __name__ == "__main__":
    main()
