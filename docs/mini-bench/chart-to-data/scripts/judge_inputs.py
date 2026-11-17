# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Write one compact truth-vs-prediction sheet per model and figure for the
judge (``judge/inputs/<model>/<figure id>.md``).

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/judge_inputs.py

A sheet lists the truth and the prediction panel by panel (kind, series,
values) with the scorer's numbers, so a judge does not have to parse the
JSON; the full files and the figure are named at the top for a closer look.
"""

from __future__ import annotations

import json
from pathlib import Path

from analyze import BENCH, load_charts, load_timing

from docling.engines.figure_data.schema import ChartData
from docling.engines.figure_data.scoring import score_figure

MAX_ROWS = 60


def describe(chart: ChartData | None) -> str:
    if chart is None:
        return "(no prediction file: the run produced nothing for this figure)\n"
    if not chart.panels:
        return "(no panels: the figure holds no data)\n"
    lines: list[str] = []
    for panel in chart.panels:
        y = panel.axes.y if panel.axes else None
        x = panel.axes.x if panel.axes else None
        lines.append(
            f"- panel {panel.id!r} title={panel.title!r} kind={panel.kind} "
            f"orientation={panel.orientation} bbox_px={[round(v) for v in panel.bbox_px]}"
        )
        for name, axis in (("x", x), ("y", y)):
            if axis is not None:
                lines.append(
                    f"  - {name} axis: name={axis.name!r} scale={axis.scale} "
                    f"range={axis.range} ticks={axis.ticks}"
                )
        lines.append(f"  - series: {[s.name for s in panel.series]}")
        lines.append(
            f"  - values ({len(panel.data)}): category | series | x | value | err_lo | err_hi | printed | source"
        )
        for value in panel.data[:MAX_ROWS]:
            lines.append(
                f"    - {value.category} | {value.series} | {value.x} | {value.value} "
                f"| {value.err_lo} | {value.err_hi} | {value.label_printed} | {value.source}"
            )
        if len(panel.data) > MAX_ROWS:
            lines.append(
                f"    - ... {len(panel.data) - MAX_ROWS} more rows in the JSON"
            )
        if panel.notes:
            lines.append(f"  - notes: {panel.notes}")
    return "\n".join(lines) + "\n"


def main() -> None:
    testset = json.loads((BENCH / "testset.json").read_text(encoding="utf-8"))
    truth = load_charts(BENCH / "truth")
    for model_dir in sorted(p for p in (BENCH / "runs").iterdir() if p.is_dir()):
        preds, timing = load_charts(model_dir), load_timing(model_dir)
        out = BENCH / "judge" / "inputs" / model_dir.name
        out.mkdir(parents=True, exist_ok=True)
        for spec in testset["figures"]:
            key = (Path(spec["bundle"]).name, spec["self_ref"])
            chart, pred = truth.get(key), preds.get(key)
            if chart is None:
                continue
            score = score_figure(chart, pred or ChartData(), name=spec["id"])
            clock = timing.get(key, {})
            stem = spec["self_ref"].lstrip("#/").replace("/", "_")
            sheet = (
                f"# {spec['id']} · {key[0]} {key[1]} · model {model_dir.name}\n\n"
                f"- figure: `figures/{spec['id']}__{key[0]}__{stem}.png`\n"
                f"- truth JSON: `truth/{key[0]}__{stem}.json`\n"
                f"- prediction JSON: under `runs/{model_dir.name}/` (`{key[0]}/{stem}.json`)\n"
                f"- expected: {spec['expected_kind']}\n"
                f"- time: {clock.get('seconds')} s, calls {clock.get('calls')}, "
                f"output tokens {clock.get('eval_tokens')}, engine issues {clock.get('issues')}\n\n"
                f"## Scorer\n\n"
                f"panels truth/pred/matched {score.truth_panels}/{score.pred_panels}/{score.panels_matched}, "
                f"kind matches {score.kind_matches}, series F1 {score.series_f1}, category F1 {score.category_f1}, "
                f"values truth/pred/matched {score.truth_values}/{score.pred_values}/{score.matched_values}, "
                f"missing {score.missing_values}, extra {score.extra_values}, "
                f"within 2 % {score.hits_02}, within 5 % {score.hits_05}, "
                f"mean error (share of axis range) {score.mean_norm_error}, printed MAPE {score.printed_mape}\n\n"
                f"## Truth\n\n{describe(chart)}\n"
                f"truth notes: {chart.uncertain}\n\n"
                f"## Prediction\n\n{describe(pred)}"
            )
            (out / f"{spec['id']}.md").write_text(sheet, encoding="utf-8")
    print("sheets written under", BENCH / "judge" / "inputs")


if __name__ == "__main__":
    main()
