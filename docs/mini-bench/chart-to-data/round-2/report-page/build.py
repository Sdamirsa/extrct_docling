"""Build the round-2 report page: one self-contained HTML file with a
summary view and a figure-by-figure view (figure, truth, one card per run).

    uv run --no-sync python docs/mini-bench/chart-to-data/round-2/report-page/build.py <out.html>

Reads the truth, both rounds' runs and judge files, text.json (the
page's prose and the recommended model) and template.html beside this
script. The figure crops under figures/ are embedded in the page, so
the output holds the papers' artwork: keep it out of the repository and
share it only privately.
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

MODELS = [
    ("gemma4_31b-it-q8_0", "Gemma 4 31B", "8-bit"),
    ("gemma4_26b-a4b-it-q8_0", "Gemma 4 26B-A4B", "8-bit"),
    ("gemma4_26b-a4b-it-qat", "Gemma 4 26B-A4B", "4-bit QAT"),
]
AGENT = ("claude-sonnet-5-5-blind", "Claude Sonnet 5.5", "blind sub-agent, by eye")
AGENT_SECONDS = 134
ERROR_ROWS = [
    ("PANEL_STRUCTURE", "Panels merged, lost or misplaced"),
    ("NO_OUTPUT", "Nothing returned for a data chart"),
    ("GEOMETRY_MISMEASURED", "Values mismeasured from mark positions"),
    ("MISSING_VALUES", "Part of the data not returned"),
    ("INTERVAL_BOUNDS", "Interval bounds wrong"),
    ("SERIES_NAMES", "Series names wrong or invented"),
    ("CATEGORY_LABELS", "Category labels wrong or missing"),
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

    def run(base: Path, key: str, name: str, build: str, rnd: int, kind: str) -> dict:
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
                "split": clock.get("panel_split"),
                "note": (
                    pred.uncertain[0]
                    if pred and pred.uncertain and (kind == "engine" or not pred.panels)
                    else None
                ),
                "pred": chart_view(pred.dump() if pred else None, MAX_ROWS),
            }
        errors: dict[str, int] = {}
        for f in judge["figures"]:
            for code in f["error_types"]:
                errors[code] = errors.get(code, 0) + 1
        seconds = [per[i]["seconds"] or 0.0 for i in per]
        gpu = max((r.get("gpu_bytes") or 0 for r in timing.values()), default=0) / 1e9
        return {
            "key": f"r{rnd}:{key}",
            "model": key,
            "name": name,
            "build": build,
            "round": rnd,
            "kind": kind,
            "usableData": sum(1 for i in data_ids if per[i]["usable"]),
            "mislead": sum(1 for f in judge["figures"] if f["severity"] == 3),
            "leftAlone": sum(
                1 for i in empty_ids if per[i]["verdict"] == "true_negative"
            ),
            "declined": sum(
                1
                for i in data_ids
                if per[i]["pred"] and not per[i]["pred"]["panels"] and per[i]["note"]
            ),
            "named05": named,
            "loose05": loose,
            "returned": returned,
            "seconds": sum(seconds) if kind == "engine" else AGENT_SECONDS,
            "secondsNoData": sum(per[i]["seconds"] or 0.0 for i in empty_ids),
            "paper": sum(per[i]["seconds"] or 0.0 for i in per if i.startswith("A")),
            "gpu": gpu,
            "errors": errors,
            "assessment": judge["summary"].get("assessment"),
            "dominant": judge["summary"].get("dominant_failure"),
            "per": per,
        }

    runs = [run(ROUND, key, name, build, 2, "engine") for key, name, build in MODELS]
    runs.append(run(ROUND, *AGENT, 2, "agent"))
    runs += [run(BENCH, key, name, build, 1, "engine") for key, name, build in MODELS]

    def ablation(label: str, folder: Path) -> dict:
        preds, timing = load_charts(folder), load_timing(folder)
        named = loose = panels = 0
        for fig in figures:
            if not fig["hasData"]:
                continue
            truth, pred = truth_charts[keys[fig["id"]]], preds.get(keys[fig["id"]])
            score = score_figure(
                truth, series_lenient(truth, pred) if pred else ChartData()
            )
            named += score.hits_05
            loose += nameless_hits(truth, pred)
            panels += score.panels_matched
        return {
            "label": label,
            "named": named,
            "loose": loose,
            "panels": panels,
            "seconds": sum(r.get("seconds") or 0.0 for r in timing.values()),
        }

    abl = TEXT["ablationModel"]
    blob = {
        "figures": figures,
        "runs": runs,
        "errorRows": ERROR_ROWS,
        "models": [{"key": k, "name": n, "build": b} for k, n, b in MODELS],
        "pick": TEXT["pick"],
        "truthValues": 560,
        "truthPanels": sum(len(truth_charts[keys[i]].panels) for i in data_ids),
        "ablationModel": TEXT["ablationModelName"],
        "ablation": [
            ablation("Round 1 engine", BENCH / "runs" / abl),
            ablation(
                "Round 2 engine without the new splitter (prompt, context, reply format, checks)",
                ROUND / "ablation" / "no-split" / abl,
            ),
            ablation("Round 2 engine", ROUND / "runs" / abl),
        ],
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
                "declined",
                "named05",
                "loose05",
                "returned",
                "seconds",
                "paper",
                "gpu",
                "dominant",
            )
        }
        for r in runs
    }
    print(json.dumps({"runs": summary, "ablation": blob["ablation"]}, indent=1))
    print(OUT, f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
