"""Build the round-4 report page: one self-contained HTML file with a
summary view (the four pipeline runs side by side) and a figure-by-figure
view (figure, truth, one card per run).

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4/report-page/build.py <out.html>

Reads ../metrics/pipeline.json (written by scripts/compare_bundles.py), the
truth, the sample, the runs and the judges' files of round 4, text.json
(the page's prose) and template.html beside this script. The figure images
under ../runs/ are embedded in the page, so the output holds the paper's
artwork: keep it out of the repository and share it only privately.
"""

import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
BENCH = ROUND.parent
sys.path.insert(0, str(BENCH / "scripts"))

from analyze import load_charts  # noqa: E402

from docling.engines.figure_data.schema import ChartData  # noqa: E402

OUT = Path(sys.argv[1])
TEXT = json.loads((HERE / "text.json").read_text(encoding="utf-8"))
PIPELINE = json.loads((ROUND / "metrics" / "pipeline.json").read_text(encoding="utf-8"))
BUNDLE = "Public-test-manuscript"
MAX_ROWS = 120
IMAGE_SIDE = 1100

# run key, name, build, where the figure goes
RUNS = [
    (
        "ollama-gemma4-26b-qat",
        "ollama",
        "Gemma 4 26B-A4B (4-bit QAT) in the measured engine",
        "nowhere: local GPU",
    ),
    (
        "cloud-sonnet-5-5",
        "cloud, Sonnet 5.5",
        "one API call per figure, through OpenRouter",
        "OpenRouter and the host it picks",
    ),
    (
        "cloud-gemini-3-8-flash",
        "cloud, Gemini 3.8 Flash",
        "one API call per figure, through OpenRouter",
        "OpenRouter and the host it picks",
    ),
    (
        "agent-sonnet-5-5",
        "agent",
        "Claude Sonnet 5.5, one session per figure",
        "Anthropic",
    ),
]
# What each dense figure holds (truth-sample/STRUCTURE.md): panels x 37 bars x 6 classes.
HOLDS = {"S10": 666, "S11": 2442, "S12": 1110, "S13": 888, "S14": 666}
ERROR_ROWS = [
    ("MISSING_VALUES", "Values left out"),
    ("GEOMETRY_MISMEASURED", "Marks mismeasured"),
    ("VALUE_ASSIGNMENT", "Right number, wrong name"),
    ("PANEL_STRUCTURE", "Charts split, merged or misplaced"),
    ("INTERVAL_BOUNDS", "Interval or range ends"),
    ("INVENTED_VALUES", "Values the figure does not show"),
    ("SERIES_NAMES", "Series names"),
    ("CATEGORY_LABELS", "Category labels"),
    ("PRINTED_LABEL_MISREAD", "Printed number misread"),
]


def image_uri(path: Path, side: int = IMAGE_SIDE) -> str:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    image.thumbnail((side, side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def table(chart: ChartData | None) -> dict | None:
    """A reading as the page shows it: per chart its id, title, kind and
    rows of category, series, x, value, low, high, printed, source."""
    if chart is None:
        return None
    left = MAX_ROWS
    panels = []
    for panel in chart.panels:
        rows = [
            [v.category, v.series, v.x, v.value, v.err_lo, v.err_hi, v.label_printed, v.source]
            for v in panel.data[:left]
        ]
        left -= len(rows)
        panels.append(
            {
                "id": panel.id,
                "title": panel.title,
                "kind": panel.kind,
                "n": len(panel.data),
                "rows": rows,
            }
        )
    return {
        "total": sum(len(p.data) for p in chart.panels),
        "panels": panels,
        "uncertain": chart.uncertain[:6],
        "description": chart.description,
    }


def main() -> None:
    truth = load_charts(ROUND / "truth")
    sample = load_charts(ROUND / "truth-sample")
    first = ROUND / "runs" / RUNS[0][0] / BUNDLE / "figure-to-data"
    figures = []
    for row in PIPELINE["figures"]:
        key = (BUNDLE, row["self_ref"])
        name, _, shows = row["what"].partition(": ")
        figure, _, page = name.rpartition("page ")
        figures.append(
            {
                "id": row["id"],
                "figure": TEXT["names"][row["id"]],
                "page": page,
                "shows": shows,
                "img": image_uri(first / row["folder"] / "figure.png"),
                "kind": "truth" if key in truth else "sample" if key in sample else "none",
                "truthValues": row["truth_values"],
                "truthCharts": row["truth_charts"],
                "sampleValues": row["sample_values"],
                "holds": HOLDS.get(row["id"]),
                "truth": table(truth.get(key) or sample.get(key)),
            }
        )
    runs = []
    for key, name, build, where in RUNS:
        summary = PIPELINE["runs"][key]
        charts = load_charts(ROUND / "runs" / key)
        judged = json.loads((ROUND / "judge" / f"{key}.json").read_text(encoding="utf-8"))
        per = {}
        for row in PIPELINE["figures"]:
            cell = row["runs"][key]
            per[row["id"]] = {
                "status": cell["status"],
                "reason": cell["reason"],
                "charts": cell["charts"],
                "values": cell["values"],
                "seconds": cell["seconds"],
                "cost": cell["cost_usd"],
                "tokens": cell["output_tokens"],
                "score": cell.get("score"),
                "sample": cell.get("sample"),
                "judge": cell.get("judge"),
                "afterFix": cell.get("after_fix"),
                "pred": table(charts.get((BUNDLE, row["self_ref"]))),
            }
        errors: dict[str, int] = {}
        for figure in judged["figures"]:
            for code in figure["error_types"]:
                errors[code] = errors.get(code, 0) + 1
        runs.append(
            {
                "key": key,
                "name": name,
                "build": build,
                "where": where,
                "method": summary["method"],
                "model": summary["model"],
                "seconds": summary["seconds"],
                "cost": summary["cost_usd"],
                "values": summary["values"],
                "charts": summary["charts"],
                "status": summary["figures"],
                "calls": summary["calls"],
                "toolCalls": summary["tool_calls"],
                "outputTokens": summary["output_tokens"],
                "truth": summary["against_truth"],
                "sample": summary["against_sample"],
                "judge": summary["judge"],
                "exports": summary["exports"],
                "errors": errors,
                "per": per,
            }
        )
    again = ROUND / "after-fix" / "runs" / "cloud-sonnet-5-5" / BUNDLE / "figure-to-data"
    data = {
        "runs": runs,
        "figures": figures,
        "truthValues": runs[0]["truth"]["truth_values"],
        "sampleValues": runs[0]["sample"]["sampled_values"],
        "errorRows": ERROR_ROWS,
        "defect": {
            "before": image_uri(first / "pictures_5" / "figure.png", 760),
            "after": image_uri(again / "pictures_5" / "figure.png", 760),
        },
        "text": TEXT,
    }
    page = (HERE / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page.replace("/*__DATA__*/", payload), encoding="utf-8")
    print(f"{OUT}: {OUT.stat().st_size / 1e6:.1f} MB, {len(figures)} figures, {len(runs)} runs")


if __name__ == "__main__":
    main()
