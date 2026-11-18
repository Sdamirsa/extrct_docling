"""Build the round-3 report page: one self-contained HTML file with a
summary view and a figure-by-figure view (figure, truth, one card per run).

    uv run --no-sync python docs/mini-bench/chart-to-data/round-3/report-page/build.py <out.html>

Reads the truth, the runs and judge files of round 3 and of the two runs of
round 2 and the one of round 1 it is compared with, text.json (the page's
prose) and template.html beside this script, and two examples of what the
step writes (../examples/). The figure crops under figures/ are embedded
in the page, so the output holds the papers' artwork: keep it out of the
repository and share it only privately.
"""

import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
BENCH = ROUND.parent
sys.path.insert(0, str(BENCH / "scripts"))

from analyze import load_charts, load_timing, series_lenient  # noqa: E402
from compare_runs import nameless_hits  # noqa: E402

from docling.engines.figure_data.schema import ChartData  # noqa: E402
from docling.engines.figure_data.scoring import score_figure  # noqa: E402

OUT = Path(sys.argv[1])
TEXT = json.loads((HERE / "text.json").read_text(encoding="utf-8"))
MAX_ROWS = 80
BLIND_SECONDS = 134

# base folder, run key, name, build, round, kind (the method in round 3),
# where the figure goes, what stands in the cost column when the run
# reports no cost
RUNS = [
    (
        ROUND,
        "ollama-gemma4-26b-qat",
        "ollama",
        "Gemma 4 26B-A4B (4-bit QAT) in the measured engine",
        3,
        "engine",
        "nowhere: local GPU",
        "local GPU",
    ),
    (
        ROUND,
        "cloud-sonnet-5-5",
        "cloud, Sonnet 5.5",
        "one API call per figure, through OpenRouter",
        3,
        "cloud",
        "OpenRouter and the host it picks",
        "",
    ),
    (
        ROUND,
        "cloud-gemini-3-8-flash",
        "cloud, Gemini 3.8 Flash",
        "one API call per figure, through OpenRouter",
        3,
        "cloud",
        "OpenRouter and the host it picks",
        "",
    ),
    (
        ROUND,
        "agent-sonnet-5-5",
        "agent",
        "Claude Sonnet 5.5, one session per figure",
        3,
        "agent",
        "Anthropic",
        "",
    ),
    (
        BENCH / "round-2",
        "gemma4_26b-a4b-it-qat",
        "Gemma 4 26B-A4B",
        "4-bit QAT, the engine before the step",
        2,
        "engine",
        "nowhere: local GPU",
        "local GPU",
    ),
    (
        BENCH / "round-2",
        "claude-sonnet-5-5-blind",
        "Claude Sonnet 5.5",
        "bare images, all 15 in one session",
        2,
        "blind",
        "Anthropic",
        "not recorded",
    ),
    (
        BENCH,
        "gemma4_26b-a4b-it-qat",
        "Gemma 4 26B-A4B",
        "4-bit QAT, the first engine",
        1,
        "engine",
        "nowhere: local GPU",
        "local GPU",
    ),
]
ERROR_ROWS = [
    ("PANEL_STRUCTURE", "Panels merged, lost or misplaced"),
    ("NO_OUTPUT", "Nothing returned for a data chart"),
    ("GEOMETRY_MISMEASURED", "Values mismeasured from mark positions"),
    ("MISSING_VALUES", "Part of the data not returned"),
    ("INTERVAL_BOUNDS", "Interval bounds wrong"),
    ("SERIES_NAMES", "Series names wrong or invented"),
    ("CATEGORY_LABELS", "Category labels wrong or missing"),
    ("VALUE_ASSIGNMENT", "Right numbers under the wrong name"),
    ("HALLUCINATED_ON_NON_CHART", "Data returned for a non-chart"),
    ("INVENTED_VALUES", "Values invented on a data chart"),
    ("PRINTED_LABEL_MISREAD", "Printed number ignored or misread"),
]


def rows_of(panel: dict) -> list[list]:
    return [
        [
            v.get("category"),
            v.get("series"),
            v.get("x"),
            v.get("value"),
            v.get("err_lo"),
            v.get("err_hi"),
            v.get("label_printed"),
            v.get("source"),
        ]
        for v in panel.get("data", [])
    ]


def chart_view(data: dict | None, cap: int) -> dict | None:
    if data is None:
        return None
    panels, total, left = [], 0, cap
    for panel in data.get("panels", []):
        rows = rows_of(panel)
        total += len(rows)
        axes = panel.get("axes") or {}
        panels.append(
            {
                "id": panel.get("id"),
                "title": panel.get("title"),
                "kind": panel.get("kind"),
                "y": (axes.get("y") or {}).get("name"),
                "yr": (axes.get("y") or {}).get("range"),
                "x": (axes.get("x") or {}).get("name"),
                "xr": (axes.get("x") or {}).get("range"),
                "n": len(rows),
                "rows": rows[: max(left, 0)],
                "notes": (panel.get("notes") or [])[:2],
            }
        )
        left -= len(rows)
    return {
        "panels": panels,
        "total": total,
        "uncertain": data.get("uncertain", [])[:6],
    }


def shortened(markdown: str, width: int = 150) -> str:
    """The reading as written, with the long lines cut so that the box
    scrolls little."""
    lines = []
    for line in markdown.splitlines():
        lines.append(line if len(line) <= width else line[: width - 1] + "…")
    return "\n".join(lines)


def main() -> None:
    testset = json.loads((BENCH / "testset.json").read_text())
    truth_charts = load_charts(BENCH / "truth")
    figure_rows = {}
    for line in (BENCH / "FIGURES.md").read_text().splitlines():
        cells = [c.strip() for c in line.split(" | ")]
        if (
            len(cells) >= 7
            and cells[0].startswith("| ")
            and cells[0][2:3] in "ABC"
            and cells[0][2:].strip()[1:].isdigit()
        ):
            figure_rows[cells[0][2:].strip()] = cells

    figures, keys = [], {}
    for spec in testset["figures"]:
        bundle = Path(spec["bundle"]).name
        stem = spec["self_ref"].lstrip("#/").replace("/", "_")
        truth = json.loads((BENCH / "truth" / f"{bundle}__{stem}.json").read_text())
        image = BENCH / "figures" / f"{spec['id']}__{bundle}__{stem}.png"
        cells = figure_rows[spec["id"]]
        keys[spec["id"]] = (bundle, spec["self_ref"])
        figures.append(
            {
                "id": spec["id"],
                "paper": cells[1],
                "pdf": cells[2].strip("`"),
                "figure": cells[3],
                "page": cells[4],
                "shows": spec["expected_kind"],
                "ref": spec["self_ref"],
                "hasData": any(p.get("data") for p in truth.get("panels", [])),
                "img": "data:image/png;base64,"
                + base64.b64encode(image.read_bytes()).decode(),
                "truth": chart_view(truth, 400),
                "bundle": bundle,
                "stem": stem,
            }
        )
    data_ids = [f["id"] for f in figures if f["hasData"]]
    empty_ids = [f["id"] for f in figures if not f["hasData"]]

    def run(
        base: Path,
        key: str,
        name: str,
        build: str,
        rnd: int,
        kind: str,
        where: str,
        cost_note: str,
    ) -> dict:
        folder = base / "runs" / key
        judge = json.loads((base / "judge" / f"{key}.json").read_text())
        verdicts = {f["figure_id"]: f for f in judge["figures"]}
        preds, timing = load_charts(folder), load_timing(folder)
        per, named, loose, returned = {}, 0, 0, 0
        for fig in figures:
            pair = keys[fig["id"]]
            truth, pred = truth_charts[pair], preds.get(pair)
            score = score_figure(
                truth, series_lenient(truth, pred) if pred else ChartData()
            )
            free = nameless_hits(truth, pred)
            clock = timing.get(pair, {})
            v = verdicts[fig["id"]]
            if fig["hasData"]:
                named += score.hits_05
                loose += free
                returned += score.pred_values
            per[fig["id"]] = {
                "verdict": v["verdict"],
                "errors": v["error_types"],
                "severity": v["severity"],
                "usable": v["usable"],
                "evidence": v["evidence"],
                "seconds": clock.get("seconds"),
                "tokens": clock.get("eval_tokens"),
                "truthValues": score.truth_values,
                "hits05": score.hits_05,
                "loose05": free,
                "calls": clock.get("calls"),
                "toolCalls": clock.get("tool_calls"),
                "cost": clock.get("cost_usd"),
                "split": clock.get("panel_split"),
                "note": pred.uncertain[0] if pred and pred.uncertain else None,
                "pred": chart_view(pred.dump() if pred else None, MAX_ROWS),
            }
        errors: dict[str, int] = {}
        for f in judge["figures"]:
            for code in f["error_types"]:
                errors[code] = errors.get(code, 0) + 1
        seconds = [per[i]["seconds"] or 0.0 for i in per]
        costs = [per[i]["cost"] for i in per if per[i]["cost"] is not None]
        gpu = max((r.get("gpu_bytes") or 0 for r in timing.values()), default=0) / 1e9
        return {
            "key": f"r{rnd}:{key}",
            "model": key,
            "name": name,
            "build": build,
            "round": rnd,
            "kind": kind,
            "method": kind,
            "where": where,
            "costNote": cost_note,
            "usableData": sum(1 for i in data_ids if per[i]["usable"]),
            "mislead": sum(1 for f in judge["figures"] if f["severity"] == 3),
            "leftAlone": sum(
                1 for i in empty_ids if per[i]["verdict"] == "true_negative"
            ),
            "named05": named,
            "loose05": loose,
            "returned": returned,
            "seconds": BLIND_SECONDS if kind == "blind" else sum(seconds),
            "secondsNoData": sum(per[i]["seconds"] or 0.0 for i in empty_ids),
            "paper": sum(per[i]["seconds"] or 0.0 for i in per if i.startswith("A")),
            "cost": round(sum(costs), 2) if costs else None,
            "toolCalls": sum(per[i]["toolCalls"] or 0 for i in per),
            "gpu": gpu,
            "errors": errors,
            "assessment": judge["summary"].get("assessment"),
            "dominant": judge["summary"].get("dominant_failure"),
            "per": per,
        }

    runs = [run(*spec) for spec in RUNS]
    sample = TEXT["sample"]
    blob = {
        "figures": figures,
        "runs": runs,
        "errorRows": ERROR_ROWS,
        "pick": TEXT["pick"],
        "truthValues": 560,
        "truthPanels": sum(len(truth_charts[keys[i]].panels) for i in data_ids),
        "sampleTitle": sample["title"],
        "sample": shortened((ROUND / sample["file"]).read_text(encoding="utf-8")),
        "embedded": shortened(
            (ROUND / "examples" / "embedded-section.md").read_text(encoding="utf-8")
        ),
        "text": TEXT,
    }
    template = (HERE / "template.html").read_text(encoding="utf-8")
    data = json.dumps(blob, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(template.replace("/*__DATA__*/", data), encoding="utf-8")
    summary = {
        r["key"]: {
            k: r[k]
            for k in (
                "usableData",
                "mislead",
                "leftAlone",
                "named05",
                "loose05",
                "returned",
                "seconds",
                "secondsNoData",
                "paper",
                "cost",
                "toolCalls",
                "gpu",
                "dominant",
            )
        }
        for r in runs
    }
    print(json.dumps(summary, indent=1))
    print(OUT, f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
