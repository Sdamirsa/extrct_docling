# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""One paper through the whole pipeline with several reading methods, side
by side (round 4).

    BENCH_ROUND=round-4 uv run --no-sync python \
        docs/mini-bench/chart-to-data/scripts/compare_bundles.py <output root> [label ...]

``<output root>/<label>/<bundle>/`` is the bundle one ``amir-batch
--figure-data ...`` run wrote (``scripts/run_round4.sh``), and
``<output root>/<label>.time`` that command's exit code and wall time.

Written:

- ``<round>/metrics/pipeline.json`` and ``pipeline.md``: per run the time of
  the command and of its parts, what the step made of the figures, cost,
  and what reached the bundle's exports; per figure what each run returned;
  for the figures with a truth file the scorer's numbers; for the figures
  with a sample only (``truth-sample/``: the printed label of a few bars
  chosen by rule) how many of the sampled labels a run returned; for every
  figure how far two runs agree (the share of one run's values that the
  other has within 5 % of the axis range under the same chart, category
  and series); the judges' verdicts (``<round>/judge/<label>.json``)
  where a run has been judged; and, for a figure that was read again
  after a fix (``<round>/after-fix/runs/<label>/``), the count of that
  second reading beside the first;
- ``<output root>/comparison.html``: the same with the figures and every
  reading, for looking at. It links the figure images inside the bundles,
  so it stays beside them and is not published.
"""

from __future__ import annotations

import html
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from analyze import ROUND, load_charts, round_file, series_lenient
from compare_runs import nameless_hits

from docling.engines.figure_data.publish import chart_table
from docling.engines.figure_data.schema import ChartData, Panel, Value
from docling.engines.figure_data.scoring import match_panels, score_figure
from docling.engines.figure_data.verify import axis_span

ORDER = [
    "ollama-gemma4-26b-qat",
    "cloud-sonnet-5-5",
    "cloud-gemini-3-8-flash",
    "agent-sonnet-5-5",
]
STATUSES = ["read", "no_data", "not_read", "failed"]
NOTE = "not the authors' numbers"


def load_run(root: Path, label: str) -> dict[str, Any]:
    bundle = next(p for p in sorted((root / label).iterdir()) if (p / "run.json").is_file())
    run = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    check = json.loads((bundle / "check.json").read_text(encoding="utf-8"))
    step = bundle / "figure-to-data"
    record = json.loads(
        sorted((step / "runs").glob("*.json"))[-1].read_text(encoding="utf-8")
    )
    clock = dict(
        part.split("=")
        for part in (root / f"{label}.time").read_text(encoding="utf-8").split()[1:]
    )
    document = json.loads((bundle / "document.json").read_text(encoding="utf-8"))
    tables = pointers = 0
    for picture in document["pictures"]:
        tabular = (picture.get("meta") or {}).get("tabular_chart")
        if tabular is not None:
            shown = tabular["chart_data"]["num_rows"] > 0
            tables += shown
            pointers += not shown
    chunks = [
        json.loads(line)
        for line in (bundle / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    figures = {f["folder"]: f for f in record["figures"]}
    costs = [f["cost_usd"] for f in figures.values() if f["cost_usd"] is not None]
    wall, conversion = float(clock["seconds"]), run["timing"]["duration_seconds"]
    return {
        "label": label,
        "bundle": bundle,
        "method": record["method"],
        "model": record["model"],
        "backend": record["backend"],
        "engine": run["engine"],
        "exit_code": int(clock["exit_code"]),
        "seconds": {
            "command": wall,
            "conversion": round(conversion, 1),
            "reading": record["seconds"],
            # Starting up, releasing the conversion models, preparing the
            # figures, embedding the readings and the bundle check.
            "rest": round(wall - conversion - record["seconds"], 1),
        },
        "figures": {s: sum(f["status"] == s for f in figures.values()) for s in STATUSES},
        "charts": sum(f["charts"] for f in figures.values()),
        "values": sum(f["values"] for f in figures.values()),
        "calls": sum(f["calls"] for f in figures.values()),
        "tool_calls": sum(f["tool_calls"] or 0 for f in figures.values()),
        "input_tokens": sum(f["input_tokens"] for f in figures.values()),
        "output_tokens": sum(f["output_tokens"] for f in figures.values()),
        "cost_usd": round(sum(costs), 4) if costs else None,
        "check": check["figure_data"],
        "check_ok": check["ok"],
        "exports": {
            "tables_at_the_figure": tables,
            "pointer_only": pointers,
            "chunks": len(chunks),
            "chunks_with_figure_data": sum(NOTE in c["text"] for c in chunks),
            "markdown_bytes": (bundle / f"{bundle.name}.md").stat().st_size,
        },
        "by_figure": figures,
        "charts_read": load_charts(step),
    }


def inside(inner: list[float], outer: list[float]) -> float:
    """The share of the box *inner* that lies in the box *outer*."""
    width = min(inner[2], outer[2]) - max(inner[0], outer[0])
    height = min(inner[3], outer[3]) - max(inner[1], outer[1])
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return max(width, 0.0) * max(height, 0.0) / area if area > 0 else 0.0


def with_truth_boxes(
    truth: ChartData, pred: ChartData | None, *, complete: bool = True
) -> ChartData | None:
    """*pred* with its charts put where the truth has them, for a scoring
    that looks at the values and not at how the figure was cut up. The
    scorer pairs charts by the overlap of their boxes, so it leaves out a
    chart the step split in two (the second part pairs with nothing), a
    reading whose charts carry no box of their own (the model numbered the
    charts itself and each got the whole figure) and one whose charts took
    the boxes of a wrong split.

    In this order: a chart goes where the truth chart with the same printed
    title is, or else the one with the same id (the panel letter). When
    the truth is *complete* (every chart of the figure, not a sample of
    them): a chart that no truth chart pairs with after that is merged
    into the truth chart that holds at least 80 % of its box; and when as
    many are then left on both sides, each is given the box of the truth
    chart in its place."""
    if pred is None:
        return None
    fixed = pred.model_copy(deep=True)
    taken: set[str] = set()
    for attribute in ("title", "id"):
        wanted: dict[str, list[Panel]] = {}
        for panel in truth.panels:
            wanted.setdefault(printed_name(getattr(panel, attribute)), []).append(panel)
        names = [printed_name(getattr(panel, attribute)) for panel in fixed.panels]
        for panel, name in zip(fixed.panels, names, strict=True):
            same = wanted.get(name, [])
            if not name or len(same) != 1 or names.count(name) != 1:
                continue
            if same[0].id in taken or any(panel is q for q in placed(fixed, taken)):
                continue
            panel.bbox_px = list(same[0].bbox_px)
            panel.notes = [*panel.notes, f"{PLACED}{same[0].id}"]
            taken.add(same[0].id)
    if not complete:
        return fixed
    partner = {t.id: p for t, p in match_panels(truth.panels, fixed.panels)}
    free = [p for p in fixed.panels if all(p is not q for q in partner.values())]
    for panel in list(free):
        holder = max(truth.panels, key=lambda t: inside(panel.bbox_px, t.bbox_px))
        if inside(panel.bbox_px, holder.bbox_px) < 0.8:
            continue
        free.remove(panel)
        if holder.id in partner:
            partner[holder.id].data.extend(panel.data)
            partner[holder.id].series.extend(panel.series)
            fixed.panels.remove(panel)
        else:
            panel.bbox_px = list(holder.bbox_px)
            partner[holder.id] = panel
    open_truth = [t for t in truth.panels if t.id not in partner]
    if len(open_truth) == len(free):
        for truth_panel, panel in zip(open_truth, free, strict=True):
            panel.bbox_px = list(truth_panel.bbox_px)
    return fixed


PLACED = "placed with truth chart "


def placed(chart: ChartData, taken: set[str]) -> list[Panel]:
    """The charts of *chart* already put where a truth chart of *taken* is."""
    return [
        panel
        for panel in chart.panels
        if any(note.removeprefix(PLACED) in taken for note in panel.notes if note.startswith(PLACED))
    ]


def printed_name(text: object) -> str:
    """A name as compared: case, spacing and the tick dash or dot that a
    text layer or OCR glues to a label do not count; "0", "0.0" and 0.0
    are one tick."""
    if text is None:
        return ""
    try:
        return f"{float(str(text)):g}"
    except ValueError:
        return " ".join(str(text).casefold().split()).rstrip("-. ")


def paired_values(
    truth: ChartData, pred: ChartData | None
) -> list[tuple[Panel, Value, Value]]:
    """Each truth value with the value *pred* has under the same name in
    the chart paired with its chart: first by exact name (category or x,
    and series; the series is left out where the truth chart has one
    series only, which then has no legend entry to copy), then, among what
    is left on both sides, by the closest name when it is at least 85 %
    the same (a reading that corrects the figure's own misspelling). The
    bench scorer pairs any two names less than a fifth apart, first fit;
    on a chart of 37 bars named "Claude3-Sonnet Web", "Claude3-Sonnet
    API", ... that pairs a bar with its neighbour as soon as a reading
    leaves one out."""
    pairs: list[tuple[Panel, Value, Value]] = []
    if pred is None:
        return pairs
    for truth_panel, pred_panel in match_panels(truth.panels, pred.panels):
        one_series = len({v.series for v in truth_panel.data}) == 1

        def key(value: Value, one_series: bool = one_series) -> tuple[str, str]:
            place = value.category if value.category is not None else value.x
            return printed_name(place), "" if one_series else printed_name(value.series)

        have: dict[tuple[str, str], list[Value]] = {}
        for value in pred_panel.data:
            have.setdefault(key(value), []).append(value)
        open_truth: list[Value] = []
        for value in truth_panel.data:
            found = have.get(key(value))
            if found:
                pairs.append((truth_panel, value, found.pop(0)))
            else:
                open_truth.append(value)
        left = [(k, v) for k, values in have.items() for v in values]
        for value in open_truth:
            place, series = key(value)
            close = [
                (SequenceMatcher(None, place, k[0]).ratio(), index)
                for index, (k, _) in enumerate(left)
                if k[1] == series
            ]
            if close and max(close)[0] >= 0.85:
                pairs.append((truth_panel, value, left.pop(max(close)[1])[1]))
    return pairs


def off_by(panel: Panel, truth: Value, got: Value) -> float | None:
    """The difference as a share of the chart's axis range."""
    if truth.value is None or got.value is None:
        return None
    span = axis_span(panel)
    width = (span[1] - span[0]) if span else None
    return abs(got.value - truth.value) / (width or max(abs(truth.value), 1e-9))


def hits(truth: ChartData, pred: ChartData | None) -> dict[str, int]:
    pairs = paired_values(truth, pred)
    errors = [e for p, t, g in pairs if (e := off_by(p, t, g)) is not None]
    return {
        "matched": len(pairs),
        "within_2": sum(e <= 0.02 for e in errors),
        "within_5": sum(e <= 0.05 for e in errors),
    }


def agreement(a: ChartData | None, b: ChartData | None) -> float | None:
    """The share of *a*'s values that *b* has within 5 % of the axis range
    under the same name, with *b*'s charts put where *a* has them; None
    when *a* has none."""
    wanted = sum(len(p.data) for p in a.panels) if a is not None else 0
    if not wanted or a is None:
        return None
    return round(hits(a, with_truth_boxes(a, b))["within_5"] / wanted, 3)


def worst_differences(truth: ChartData, pred: ChartData, limit: int = 12) -> list[str]:
    """The paired values that are furthest from the truth, in axis shares."""
    rows: list[tuple[float, str]] = []
    for panel, value, got in paired_values(truth, pred):
        error = off_by(panel, value, got)
        if error is not None and error > 0.05:
            name = " / ".join(
                str(part)
                for part in (panel.id, value.category, value.series, value.x)
                if part is not None
            )
            rows.append((error, f"{name}: truth {value.value:g}, read {got.value:g}"))
    return [text for _, text in sorted(rows, reverse=True)[:limit]]


def main() -> None:
    root = Path(sys.argv[1])
    labels = sys.argv[2:] or [
        label for label in ORDER if (root / f"{label}.time").is_file()
    ]
    runs = {label: load_run(root, label) for label in labels}
    testset = json.loads(round_file("testset.json").read_text(encoding="utf-8"))
    truth = load_charts(round_file("truth"))
    sample = load_charts(ROUND / "truth-sample")
    again = {
        label: load_charts(ROUND / "after-fix" / "runs" / label) for label in labels
    }
    judged: dict[str, dict[str, Any]] = {}
    for label in labels:
        verdicts = ROUND / "judge" / f"{label}.json"
        if verdicts.is_file():
            judged[label] = json.loads(verdicts.read_text(encoding="utf-8"))
    figures: list[dict[str, Any]] = []
    for spec in testset["figures"]:
        key = (Path(spec["bundle"]).name, spec["self_ref"])
        folder = spec["self_ref"].lstrip("#/").replace("/", "_")
        reference = truth.get(key)
        probe = sample.get(key)
        row: dict[str, Any] = {
            "id": spec["id"],
            "self_ref": spec["self_ref"],
            "folder": folder,
            "what": spec["expected_kind"],
            "truth_values": (
                sum(len(p.data) for p in reference.panels) if reference else None
            ),
            "truth_charts": len(reference.panels) if reference else None,
            "sample_values": sum(len(p.data) for p in probe.panels) if probe else None,
            "runs": {},
            "agreement": {},
        }
        for label, run in runs.items():
            outcome = run["by_figure"].get(folder)
            chart = run["charts_read"].get(key)
            cell: dict[str, Any] = {
                "status": outcome["status"] if outcome else "not prepared",
                "reason": outcome["reason"] if outcome else None,
                "charts": outcome["charts"] if outcome else 0,
                "values": outcome["values"] if outcome else 0,
                "seconds": outcome["seconds"] if outcome else None,
                "cost_usd": outcome["cost_usd"] if outcome else None,
                "output_tokens": outcome["output_tokens"] if outcome else None,
            }
            if reference is not None:
                lenient = score_figure(
                    reference, series_lenient(reference, chart) if chart else ChartData()
                )
                boxed = with_truth_boxes(reference, chart)
                by_name = hits(reference, boxed)
                cell["score"] = {
                    "charts_matched": lenient.panels_matched,
                    "matched": lenient.matched_values,
                    "within_2": lenient.hits_02,
                    "within_5": lenient.hits_05,
                    "mean_error": lenient.mean_norm_error,
                    # Charts put where the truth has them, values paired by
                    # their printed name.
                    "matched_by_name": by_name["matched"],
                    "within_2_by_name": by_name["within_2"],
                    "within_5_by_name": by_name["within_5"],
                    "within_5_names_ignored": nameless_hits(reference, boxed),
                    "worst": worst_differences(reference, boxed) if boxed else [],
                }
                reread = again[label].get(key)
                if reread is not None:
                    cell["after_fix"] = {
                        "values": sum(len(p.data) for p in reread.panels),
                        "within_5_by_name": hits(
                            reference, with_truth_boxes(reference, reread)
                        )["within_5"],
                    }
            verdict = next(
                (
                    f
                    for f in judged.get(label, {}).get("figures", [])
                    if f["figure_id"] == spec["id"]
                ),
                None,
            )
            if verdict is not None:
                cell["judge"] = {
                    k: verdict[k]
                    for k in ("verdict", "error_types", "severity", "usable", "evidence")
                }
            if probe is not None:
                sampled = hits(probe, with_truth_boxes(probe, chart, complete=False))
                cell["sample"] = {
                    "matched": sampled["matched"],
                    "within_5": sampled["within_5"],
                }
            row["runs"][label] = cell
            row["agreement"][label] = {
                other: agreement(chart, runs[other]["charts_read"].get(key))
                for other in labels
                if other != label
            }
        figures.append(row)

    summary = {
        "paper": testset["figures"][0]["pdf"],
        "runs": {
            label: {
                k: v
                for k, v in run.items()
                if k not in ("bundle", "by_figure", "charts_read")
            }
            for label, run in runs.items()
        },
        "figures": figures,
    }
    scored = [f for f in figures if f["truth_values"] is not None]
    for label in labels:
        cells = [f["runs"][label] for f in scored]
        summary["runs"][label]["against_truth"] = {
            "figures": len(scored),
            "truth_values": sum(f["truth_values"] for f in scored),
            "returned": sum(c["values"] for c in cells),
            "matched": sum(c["score"]["matched"] for c in cells),
            "within_5": sum(c["score"]["within_5"] for c in cells),
            "within_5_by_name": sum(c["score"]["within_5_by_name"] for c in cells),
            "within_5_by_name_after_fix": sum(
                c.get("after_fix", c["score"])["within_5_by_name"] for c in cells
            ),
            "within_5_names_ignored": sum(
                c["score"]["within_5_names_ignored"] for c in cells
            ),
        }
    for label, verdicts in judged.items():
        rows = verdicts["figures"]
        summary["runs"][label]["judge"] = {
            "figures": len(rows),
            "verdicts": {
                v: sum(f["verdict"] == v for f in rows)
                for v in ("correct", "partial", "wrong", "missed")
            },
            "usable": sum(bool(f["usable"]) for f in rows),
            "would_mislead": sum(f["severity"] == 3 for f in rows),
            "dominant_failure": verdicts["summary"]["dominant_failure"],
            "assessment": verdicts["summary"]["assessment"],
        }
    probed = [f for f in figures if f["sample_values"] is not None]
    for label in labels:
        cells = [f["runs"][label] for f in probed]
        summary["runs"][label]["against_sample"] = {
            "figures": len(probed),
            "sampled_values": sum(f["sample_values"] for f in probed),
            "matched": sum(c["sample"]["matched"] for c in cells),
            "within_5": sum(c["sample"]["within_5"] for c in cells),
        }
    metrics = ROUND / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    (metrics / "pipeline.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (metrics / "pipeline.md").write_text(markdown(summary, labels), encoding="utf-8")
    (root / "comparison.html").write_text(page(summary, runs, truth), encoding="utf-8")
    print(markdown(summary, labels))
    print("written:", metrics / "pipeline.md", root / "comparison.html")


def money(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "local"


def markdown(summary: dict[str, Any], labels: list[str]) -> str:
    runs = summary["runs"]
    lines = [
        "# One paper, the whole pipeline, each method",
        "",
        f"Paper: `{summary['paper']}`. Written by `scripts/compare_bundles.py`.",
        "",
        "## Time and cost of one `amir-batch` command",
        "",
        "| run | command s | conversion s | reading s | rest s | cost USD | calls | output tokens |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label in labels:
        run, s = runs[label], runs[label]["seconds"]
        lines.append(
            f"| {label} | {s['command']:.0f} | {s['conversion']:.0f} | "
            f"{s['reading']:.0f} | {s['rest']:.0f} | {money(run['cost_usd'])} | "
            f"{run['calls']} | {run['output_tokens']} |"
        )
    lines += [
        "",
        "## What the step made of the chart candidates",
        "",
        "| run | read | no data | not read | failed | charts | values |",
        "|---|---|---|---|---|---|---|",
    ]
    for label in labels:
        run, f = runs[label], runs[label]["figures"]
        lines.append(
            f"| {label} | {f['read']} | {f['no_data']} | {f['not_read']} | "
            f"{f['failed']} | {run['charts']} | {run['values']} |"
        )
    lines += [
        "",
        "## What reached the bundle",
        "",
        "| run | table at the figure | pointer only | chunks | chunks with figure data | markdown bytes | check |",
        "|---|---|---|---|---|---|---|",
    ]
    for label in labels:
        run, e = runs[label], runs[label]["exports"]
        lines.append(
            f"| {label} | {e['tables_at_the_figure']} | {e['pointer_only']} | "
            f"{e['chunks']} | {e['chunks_with_figure_data']} | {e['markdown_bytes']} | "
            f"{'ok' if run['check_ok'] else 'issues'} |"
        )
    if any("against_truth" in runs[label] for label in labels):
        first = runs[labels[0]]["against_truth"]
        lines += [
            "",
            f"## Against the truth ({first['figures']} figures, "
            f"{first['truth_values']} values)",
            "",
            "Three counts of values within 5 % of the axis range. *As scored*: "
            "the bench's scorer of the earlier rounds, which pairs charts by "
            "the overlap of their boxes and values by names less than a "
            "fifth apart, first fit. *By name*: a chart whose box pairs with "
            "none is merged into the truth chart that holds it, or paired by "
            "its id or its place (a chart cut in two, or charts without a "
            "box, still count), and a value is paired with the value under "
            "the same printed name. *Names ignored*: with the charts placed "
            "the same way, the sorted values of paired charts are compared, "
            "whatever they are called; an upper bound that lets chance "
            "matches through.",
            "",
            "| run | returned | as scored | by name | names ignored | by name, "
            "with the figure read again after the fix |",
            "|---|---|---|---|---|---|",
        ]
        for label in labels:
            t = runs[label]["against_truth"]
            lines.append(
                f"| {label} | {t['returned']} | {t['within_5']} | "
                f"{t['within_5_by_name']} | {t['within_5_names_ignored']} | "
                f"{t['within_5_by_name_after_fix']} |"
            )
    if any("judge" in runs[label] for label in labels):
        lines += [
            "",
            "## The judges (the figures with a truth file)",
            "",
            "| run | correct | partial | wrong | missed | usable | would mislead | dominant failure |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for label in labels:
            j = runs[label].get("judge")
            if j is None:
                lines.append(f"| {label} | not judged | | | | | | |")
                continue
            v = j["verdicts"]
            lines.append(
                f"| {label} | {v['correct']} | {v['partial']} | {v['wrong']} | "
                f"{v['missed']} | {j['usable']} of {j['figures']} | "
                f"{j['would_mislead']} | {j['dominant_failure']} |"
            )
        lines += [
            "",
            "| figure | " + " | ".join(labels) + " |",
            "|---|" + "---|" * len(labels),
        ]
        for figure in summary["figures"]:
            if figure["truth_values"] is None:
                continue
            cells = []
            for label in labels:
                j = figure["runs"][label].get("judge")
                cells.append(
                    f"{j['verdict']}, severity {j['severity']}"
                    + ("" if j["usable"] else ", not usable")
                    if j
                    else ""
                )
            lines.append(f"| {figure['id']} | " + " | ".join(cells) + " |")
    probe = runs[labels[0]].get("against_sample", {})
    if probe.get("figures"):
        lines += [
            "",
            f"## Against the sampled bars ({probe['figures']} dense figures, "
            f"{probe['sampled_values']} values)",
            "",
            "A sample fixed by rule: in the first and the last panel of each "
            "figure, the share of Correct of bars 1, 8, 15, 22, 29 and 36 "
            "(printed where the print can be read, else measured against "
            "the axis).",
            "",
            "| run | sampled bars returned under the bar's name | within 5 % |",
            "|---|---|---|",
        ]
        for label in labels:
            t = runs[label]["against_sample"]
            lines.append(f"| {label} | {t['matched']} | {t['within_5']} |")
    lines += [
        "",
        "## Per figure: status, values returned (within 5 % of the truth by "
        "name, or of the sampled bars)",
        "",
        "| figure | truth | " + " | ".join(labels) + " |",
        "|---|---|" + "---|" * len(labels),
    ]
    for figure in summary["figures"]:
        cells = []
        for label in labels:
            cell = figure["runs"][label]
            text = f"{cell['status']}, {cell['values']}"
            if "after_fix" in cell:
                text += (
                    f" ({cell['score']['within_5_by_name']}; read again after "
                    f"the fix: {cell['after_fix']['within_5_by_name']})"
                )
            elif "score" in cell:
                text += f" ({cell['score']['within_5_by_name']})"
            elif "sample" in cell:
                text += f" ({cell['sample']['within_5']})"
            cells.append(text)
        if figure["truth_values"] is not None:
            truth = str(figure["truth_values"])
        elif figure["sample_values"] is not None:
            truth = f"sample of {figure['sample_values']}"
        else:
            truth = "none"
        lines.append(f"| {figure['id']} | {truth} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Agreement between runs",
        "",
        "The share of the row run's values that the column run has within 5 % "
        "of the axis range under the same chart, category and series, summed "
        "over the figures both were given. It needs no truth, and it is not "
        "accuracy: two runs can agree on a wrong value.",
        "",
        "| | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for label in labels:
        cells = []
        for other in labels:
            if other == label:
                cells.append("")
                continue
            total = hits = 0.0
            for figure in summary["figures"]:
                share = figure["agreement"][label].get(other)
                if share is not None:
                    values = figure["runs"][label]["values"]
                    total += values
                    hits += share * values
            cells.append(f"{hits / total:.2f}" if total else "")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def reading_table(chart: ChartData | None) -> str:
    if chart is None:
        return "<p class='none'>no reading</p>"
    table = chart_table(chart, 0.0)
    if table is None:
        reason = chart.uncertain[0] if chart.uncertain else "nothing read"
        return f"<p class='none'>{html.escape(reason)}</p>"
    rows = "".join(
        "<tr>"
        + "".join(
            f"<{tag}>{html.escape(cell.text)}</{tag}>"
            for cell in row
            for tag in ("th" if cell.column_header or cell.row_header else "td",)
        )
        + "</tr>"
        for row in table.grid
    )
    left_out = "".join(f"<li>{html.escape(text)}</li>" for text in chart.uncertain[:8])
    return (
        f"<div class='scroll'><table class='reading'>{rows}</table></div>"
        + (f"<p class='small'>Not read, or uncertain:</p><ul class='small'>{left_out}</ul>" if left_out else "")
    )


def page(
    summary: dict[str, Any],
    runs: dict[str, dict[str, Any]],
    truth: dict[tuple[str, str], ChartData],
) -> str:
    labels = list(runs)
    first = runs[labels[0]]
    bundle_name = first["bundle"].name
    head = "".join(f"<th>{html.escape(label)}</th>" for label in labels)

    def row(name: str, cells: list[str]) -> str:
        return f"<tr><th>{html.escape(name)}</th>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    def of(fn: Any) -> list[str]:
        return [html.escape(str(fn(summary["runs"][label]))) for label in labels]

    overview = (
        f"<table><tr><th></th>{head}</tr>"
        + row("method, model", of(lambda r: f"{r['method']}, {r['model']}"))
        + row("whole command, s", of(lambda r: f"{r['seconds']['command']:.0f}"))
        + row("conversion, s", of(lambda r: f"{r['seconds']['conversion']:.0f}"))
        + row("reading the figures, s", of(lambda r: f"{r['seconds']['reading']:.0f}"))
        + row("cost, USD", of(lambda r: money(r["cost_usd"])))
        + row(
            "figures read / no data / not read / failed",
            of(lambda r: " / ".join(str(r["figures"][s]) for s in STATUSES)),
        )
        + row("charts", of(lambda r: r["charts"]))
        + row("values", of(lambda r: r["values"]))
        + row(
            "table at the figure / pointer only",
            of(
                lambda r: f"{r['exports']['tables_at_the_figure']} / "
                f"{r['exports']['pointer_only']}"
            ),
        )
        + row(
            "within 5 % of the truth (of "
            + str(first_truth(summary, labels))
            + " values in the figures with a truth file)",
            of(lambda r: r.get("against_truth", {}).get("within_5_by_name", "")),
        )
        + row(
            "the same, with Figure 6 read again from its corrected image",
            of(
                lambda r: r.get("against_truth", {}).get(
                    "within_5_by_name_after_fix", ""
                )
            ),
        )
        + row(
            "judges: figures correct / partial, usable (of the "
            + str(len([f for f in summary["figures"] if f["truth_values"] is not None]))
            + " with a truth file)",
            of(
                lambda r: (
                    f"{r['judge']['verdicts']['correct']} / "
                    f"{r['judge']['verdicts']['partial']}, {r['judge']['usable']} usable"
                    + (
                        f", {r['judge']['would_mislead']} would mislead"
                        if r["judge"]["would_mislead"]
                        else ""
                    )
                )
                if "judge" in r
                else ""
            ),
        )
        + row(
            "sampled bars of the dense figures right (of "
            + str(first.get("sampled", 0) or sample_total(summary, labels))
            + ")",
            of(lambda r: r.get("against_sample", {}).get("within_5", "")),
        )
        + row(
            "open",
            [
                f"<a href='{label}/{bundle_name}/preview.html'>viewer</a> · "
                f"<a href='{label}/{bundle_name}/{bundle_name}.html'>document</a> · "
                f"<a href='{label}/{bundle_name}/figure-to-data/'>readings</a>"
                for label in labels
            ],
        )
        + "</table>"
    )
    sections = []
    for figure in summary["figures"]:
        key = (bundle_name, figure["self_ref"])
        image = f"{labels[0]}/{bundle_name}/figure-to-data/{figure['folder']}/figure.png"
        cells = [figure["runs"][label] for label in labels]
        table = (
            f"<table><tr><th></th>{head}</tr>"
            + row("status", [html.escape(c["status"]) for c in cells])
            + row("charts", [str(c["charts"]) for c in cells])
            + row("values", [str(c["values"]) for c in cells])
            + row("seconds", [f"{c['seconds']:.0f}" if c["seconds"] is not None else "" for c in cells])
            + row("cost, USD", [money(c["cost_usd"]) if c["seconds"] is not None else "" for c in cells])
        )
        if figure["truth_values"] is not None:
            table += (
                row(
                    f"within 5 % of the truth ({figure['truth_values']} values, "
                    f"{figure['truth_charts']} charts), as scored",
                    [str(c["score"]["within_5"]) for c in cells],
                )
                + row(
                    "the same, charts put in place and values paired by name",
                    [str(c["score"]["within_5_by_name"]) for c in cells],
                )
                + row(
                    "the same, names ignored too",
                    [str(c["score"]["within_5_names_ignored"]) for c in cells],
                )
            )
        if any("after_fix" in c for c in cells):
            table += row(
                "read again after the fix to the figure's image: within 5 % of "
                "the truth, by name",
                [
                    str(c["after_fix"]["within_5_by_name"]) if "after_fix" in c else ""
                    for c in cells
                ],
            )
        if any("judge" in c for c in cells):
            table += row(
                "judge",
                [
                    html.escape(
                        f"{c['judge']['verdict']}, severity {c['judge']['severity']}"
                        + ("" if c["judge"]["usable"] else ", not usable")
                    )
                    if "judge" in c
                    else ""
                    for c in cells
                ],
            )
        if figure["sample_values"] is not None:
            table += row(
                f"sampled bars right (of {figure['sample_values']})",
                [str(c["sample"]["within_5"]) for c in cells],
            )
        for label in labels:
            table += row(
                f"agrees with {label}",
                [
                    ""
                    if other == label or figure["agreement"][other].get(label) is None
                    else f"{figure['agreement'][other][label]:.2f}"
                    for other in labels
                ],
            )
        table += "</table>"
        readings = ""
        if key in truth:
            readings += (
                "<details><summary>truth</summary>"
                + reading_table(truth[key])
                + "</details>"
            )
        for label in labels:
            cell = figure["runs"][label]
            chart = runs[label]["charts_read"].get(key)
            extra = ""
            if cell.get("reason"):
                extra += f"<p class='small'>{html.escape(cell['reason'])}</p>"
            if "judge" in cell:
                extra += (
                    "<p class='small'>Judge: "
                    + html.escape(
                        f"{cell['judge']['verdict']} "
                        f"({', '.join(cell['judge']['error_types']) or 'no error'}). "
                        f"{cell['judge']['evidence']}"
                    )
                    + "</p>"
                )
            worst = cell.get("score", {}).get("worst") or []
            if worst:
                extra += (
                    "<p class='small'>Furthest from the truth (more than 5 % of the axis):</p>"
                    "<ul class='small'>"
                    + "".join(f"<li>{html.escape(text)}</li>" for text in worst)
                    + "</ul>"
                )
            readings += (
                f"<details><summary>{html.escape(label)}: {cell['status']}, "
                f"{cell['values']} values in {cell['charts']} charts</summary>"
                + extra
                + reading_table(chart)
                + "</details>"
            )
        sections.append(
            f"<section id='{figure['id']}'><h2>{figure['id']} · "
            f"{html.escape(figure['what'])}</h2>"
            f"<div class='pair'><a href='{image}'><img src='{image}' alt='the figure'></a>"
            f"<div>{table}</div></div>{readings}</section>"
        )
    return PAGE.format(
        paper=html.escape(summary["paper"]),
        overview=overview,
        sections="\n".join(sections),
    )


def sample_total(summary: dict[str, Any], labels: list[str]) -> int:
    return summary["runs"][labels[0]].get("against_sample", {}).get("sampled_values", 0)


def first_truth(summary: dict[str, Any], labels: list[str]) -> int:
    return summary["runs"][labels[0]].get("against_truth", {}).get("truth_values", 0)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>One paper, four reading methods</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 14px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 1280px;
    padding: 24px 20px 80px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 16px; margin: 36px 0 10px; }}
  p.lede, .small {{ color: GrayText; }}
  .small {{ font-size: 12px; margin: 6px 0 2px; }}
  table {{ border-collapse: collapse; font-size: 13px; }}
  th, td {{ border: 1px solid color-mix(in srgb, currentColor 22%, transparent);
    padding: 3px 8px; text-align: left; vertical-align: top; }}
  th {{ font-weight: 600; }}
  td {{ font-variant-numeric: tabular-nums; }}
  .pair {{ display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }}
  .pair img {{ max-width: 460px; max-height: 520px; border: 1px solid
    color-mix(in srgb, currentColor 22%, transparent); background: #fff; }}
  details {{ margin: 8px 0; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  .scroll {{ max-height: 420px; overflow: auto; margin-top: 6px; }}
  table.reading {{ font-size: 12px; }}
  .none {{ color: GrayText; font-style: italic; }}
</style></head><body>
<h1>One paper, four reading methods</h1>
<p class="lede">{paper}, converted by <code>amir-batch</code> once per method
with <code>--figure-data</code>. Every number below was read from a figure by a
model: none is the authors'. The figures are the paper's own artwork; this
page links them inside the bundles beside it and is not meant to be
published.</p>
{overview}
{sections}
</body></html>
"""


if __name__ == "__main__":
    main()
