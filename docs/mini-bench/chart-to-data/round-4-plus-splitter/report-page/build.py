"""Build the page of the split check: one self-contained HTML file with a
summary view (every splitter on every figure, the judges, FigEx2) and a
figure view (the figure with the truth boxes and one splitter's boxes drawn
on it).

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/report-page/build.py <out.html>

Reads ``figures.json``, ``truth/``, ``candidates/``, ``results.json``
(``scripts/score.py``), ``extra/one-rule.json`` (``scripts/score_one_rule.py``)
and the two FigEx2 reader files of ``extra/``, and ``template.html`` beside
this script. The figure images are embedded in the page, so the output
holds the papers' artwork: keep it out of the repository and share it only
privately.
"""

import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
sys.path.insert(0, str(ROUND / "scripts"))

from common import area, figures, image_path, overlap, read_candidate  # noqa: E402
from score import CANDIDATES, FOUND, HELD, WHOLE, judge_figure, pair, total  # noqa: E402
from score_final import SETS, VARIANTS  # noqa: E402
from score_one_rule import MODELS, POLICIES  # noqa: E402

IMAGE_SIDE = 1100
# The cuts of the final test (scripts/score_final.py), shown as six more
# rows of the grid: what is recommended, and the design that was tested
# against it (the cloud models ran that on the tricky figures only).
RECOMMENDED = "Recommended: the model lists the charts, then the one rule"
TESTED = "Tested and not taken: caption, both cuts, a ruling where they differ"
FINALS = [
    ("gemma4-26b-qat-recommended", "Local: Gemma 4 26B", "overview call, 5.5 s", RECOMMENDED),
    ("sonnet-5-5-recommended", "Cloud: Sonnet 5.5", "overview call, 3.3 s, 1.0 cent", RECOMMENDED),
    ("gemini-3-8-flash-recommended", "Cloud: Gemini 3.8 Flash", "overview call, 5.3 s, 0.3 cent", RECOMMENDED),
    ("gemma4-26b-qat-final", "Gemma, with caption and ruling", "two calls on 36 of 51 figures", TESTED),
    ("sonnet-5-5-final", "Sonnet, with caption and ruling", "two calls on 27 of 34 figures", TESTED),
    ("gemini-3-8-flash-final", "Gemini, with caption and ruling", "two calls on 26 of 34 figures", TESTED),
]
# The row groups of the page and, per splitter, what one figure takes
# (README, "What was compared").
SECTIONS = [
    ("No model call", ["rules", "heron", "heron-cut", "figex2-detector"]),
    ("A local model", ["figex2-scored", "figex2", "gemma4-26b-qat", "gemma4-26b-qat-cut"]),
    (
        "A cloud model",
        ["sonnet-5-5", "gemini-3-8-flash", "sonnet-5-5-cut", "gemini-3-8-flash-cut"],
    ),
]
CALL = {
    "rules": "rules of the prepare phase, no model",
    "heron": "layout detector, 0.05 s, 164 MB",
    "heron-cut": "layout detector, 0.05 s, 164 MB",
    "figex2-detector": "93 MB detector, 0.2 s",
    "figex2-scored": "8 s, 17 GB + 2.6 GB",
    "figex2": "8 s, 17 GB + 2.6 GB",
    "gemma4-26b-qat": "overview call, 5.5 s",
    "gemma4-26b-qat-cut": "overview call, 5.5 s",
    "sonnet-5-5": "overview call, 3.3 s, 1.0 cent",
    "sonnet-5-5-cut": "overview call, 3.3 s, 1.0 cent",
    "gemini-3-8-flash": "overview call, 5.3 s, 0.3 cent",
    "gemini-3-8-flash-cut": "overview call, 5.3 s, 0.3 cent",
}
# What FigEx2's captioning model had right as a value reader, by how it
# came to the value (README, "Its captioning model beside the readers").
READER_PARTS = {
    "S03": {"read": 37, "filled": 59, "estimated": 0},
    "S04": {"read": 17, "filled": 81, "estimated": 0},
    "S06": {"read": 0, "filled": 0, "estimated": 28},
    "S08": {"read": 63, "filled": 0, "estimated": 0},
}
READER_NAMES = {
    "S02": "Figure 3",
    "S03": "Figure 4",
    "S04": "Figure 5",
    "S05": "Figure 6",
    "S06": "Figure 7",
    "S08": "Figure S2",
}


def image_uri(path: Path) -> str:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    image.thumbnail((IMAGE_SIDE, IMAGE_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def drawn(truth: list[list[float]], boxes: list[list[float]]) -> dict:
    """Each box of a splitter with what the scorer made of it: ``whole``
    (on a chart and holding nine tenths of it), ``clipped`` (on a chart),
    ``off`` (on no chart); and the charts no box is on."""
    boxes = boxes or [WHOLE]
    single = len(truth) == 1 and len(boxes) == 1
    paired = {f: (t, score) for t, f, score in pair(truth, boxes)}
    out, hit = [], set()
    for index, box in enumerate(boxes):
        state = "off"
        if index in paired and paired[index][1] >= FOUND:
            t = paired[index][0]
            hit.add(t)
            held = single or overlap(truth[t], box) >= HELD * area(truth[t])
            state = "whole" if held else "clipped"
        out.append({"b": [round(v, 1) for v in box], "s": state})
    return {"boxes": out, "missed": [t for t in range(len(truth)) if t not in hit]}


def said(name: str, row: dict, raw: dict) -> dict:
    """What a splitter said about a figure beside its boxes."""
    info = {}
    if name == "rules":
        info["method"] = row.get("method")
        info["notes"] = row.get("notes", [])
    if "description" in row:
        info["description"] = row["description"]
        info["kinds"] = row.get("kinds", [])
        info["seconds"] = row.get("seconds")
        info["cost"] = row.get("cost_usd")
    if name == "figex2":
        info["listed"] = row.get("listed", [])
        info["captions"] = raw.get("captions", {})
    if name == "heron":
        info["scores"] = [b["score"] for b in row.get("picture_boxes", [])][:12]
    return info


def round5_section(text: dict | None) -> str:
    """The section on what was built and run after the check (round 5):
    a note, one table and a row of cards, from ``final_text.json``."""
    if not text:
        return ""
    head, *rows = text["table"]
    table = (
        "<thead><tr>"
        + "".join(f"<th{' class=\"r\"' if i else ''}>{cell}</th>" for i, cell in enumerate(head))
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join(
                f"<td{' class=\"r num\"' if i else ''}>{cell}</td>" for i, cell in enumerate(row)
            )
            + "</tr>"
            for row in rows
        )
        + "</tbody>"
    )
    cards = "".join(
        f'<div class="panel"><h3>{card["title"]}</h3><p>{card["text"]}</p></div>'
        for card in text["cards"]
    )
    return (
        f'<section><h2>{text["title"]}</h2><p class="note">{text["note"]}</p>'
        f'<div class="panel scroll"><table>{table}</table></div>'
        f'<div class="cols">{cards}</div></section>'
    )


def main() -> None:
    out = Path(sys.argv[1])
    results = json.loads((ROUND / "results.json").read_text(encoding="utf-8"))
    one_rule = json.loads((ROUND / "extra" / "one-rule.json").read_text(encoding="utf-8"))
    rows = figures()
    truth, shown = {}, []
    for figure in rows:
        record = json.loads(
            (ROUND / "truth" / f"{figure['id']}.json").read_text(encoding="utf-8")
        )
        truth[figure["id"]] = [chart["box"] for chart in record["charts"]]
        shown.append(
            {
                "id": figure["id"],
                "group": figure["group"],
                "paper": figure["bundle"],
                "type": figure.get("figure_type"),
                "size": [figure["width"], figure["height"]],
                "earlier": figure.get("known_charts"),
                "img": image_uri(image_path(figure)),
                "truth": [
                    {"label": c["label"], "b": [round(v, 1) for v in c["box"]]}
                    for c in record["charts"]
                ],
                "note": record.get("note"),
            }
        )
    figex2_raw = read_candidate("figex2-raw")
    names = {key: name for key, name, _ in CANDIDATES}
    splitters = []
    for section, keys in SECTIONS:
        for key in keys:
            raw = read_candidate(key)
            alone = results["alone"][key]
            per = {}
            for figure in rows:
                row = raw.get(figure["id"], {})
                per[figure["id"]] = {
                    **alone["figures"][figure["id"]],
                    **drawn(truth[figure["id"]], row.get("boxes", [])),
                    "said": said(key, row, figex2_raw.get(figure["id"], {})),
                }
            splitters.append(
                {
                    "key": key,
                    "name": names[key],
                    "section": section,
                    "call": CALL[key],
                    "all": alone["all"],
                    "groups": alone["groups"],
                    "n": len(rows),
                    "charts": results["charts"],
                    "per": per,
                }
            )
    for key, name, call, section in FINALS:
        try:
            raw = read_candidate(key)
        except FileNotFoundError:
            continue
        per = {}
        for figure in rows:
            row = raw.get(figure["id"])
            per[figure["id"]] = row and {
                **judge_figure(truth[figure["id"]], row["boxes"]),
                **drawn(truth[figure["id"]], row["boxes"]),
                "said": {
                    "description": row["list"].get("description"),
                    "kinds": row["list"].get("kinds") or [],
                    "seconds": row["list"].get("seconds"),
                    "cost": row["list"].get("cost_usd"),
                    "final": {
                        "from": row["from"],
                        "ruling": row.get("ruling"),
                        "counts": row.get("counts"),
                    },
                },
            }
        ran = [p for p in per.values() if p]
        splitters.append(
            {
                "key": key,
                "name": name,
                "section": section,
                "call": call,
                "all": total(ran),
                "n": len(ran),
                "charts": sum(p["truth"] for p in ran),
                "per": per,
            }
        )
    final_path = ROUND / "final-test" / "results.json"
    final = None
    if final_path.is_file():
        scored = json.loads(final_path.read_text(encoding="utf-8"))
        final = {
            "variants": VARIANTS,
            "sets": SETS,
            "sample": json.loads(
                (ROUND / "final-test" / "sample.json").read_text(encoding="utf-8")
            ),
            "models": [
                {k: v for k, v in cell.items() if k != "per_figure"}
                for cell in scored.values()
            ],
        }
    judges = []
    for key in ("rules", "heron", "figex2", "gemma4-26b-qat", "sonnet-5-5", "gemini-3-8-flash"):
        row = {"name": names[key], "alone": results["alone"][key]["all"]["right"]}
        for judge in ("heron", "figex2"):
            if judge == key:
                continue
            row[judge] = {
                "right": results["with_judge"][judge][key]["all"]["right"],
                "agree": results["agreement"][judge][key]["agree"],
                "agree_right": results["agreement"][judge][key]["agree_right"],
            }
        judges.append(row)
    scores = json.loads(
        (ROUND / "extra" / "figex2-reader-score.json").read_text(encoding="utf-8")
    )
    answers = json.loads(
        (ROUND / "extra" / "figex2-captioner-as-reader.json").read_text(encoding="utf-8")
    )
    reader = {
        "prompt": answers["prompt"],
        "total": scores["total"],
        "figures": [
            {
                **row,
                "name": READER_NAMES[row["id"]],
                "parts": READER_PARTS.get(row["id"], {"read": 0, "filled": 0, "estimated": 0}),
                "answer": answers["figures"][row["id"]]["asked_for_values"],
                "own": answers["figures"][row["id"]]["own_prompt"],
            }
            for row in scores["figures"]
        ],
    }
    data = {
        "figures": shown,
        "splitters": splitters,
        "charts": results["charts"],
        "judges": judges,
        "arbiter": {
            key: {
                "name": names[key],
                **{k: v for k, v in results["count_as_arbiter"][key].items() if k != "source"},
            }
            for key in ("gemma4-26b-qat", "sonnet-5-5", "gemini-3-8-flash")
        },
        "captioner": results["figex2_captioner"],
        "oneRule": {
            "policies": POLICIES,
            "models": [
                {
                    "key": key,
                    "name": title,
                    "count": one_rule[key]["count"],
                    "rows": {
                        policy: {
                            "all": one_rule[key][policy]["all"],
                            "groups": one_rule[key][policy]["groups"],
                            "taken": one_rule[key][policy]["taken"],
                        }
                        for policy, _ in POLICIES
                    },
                }
                for key, title in MODELS
            ],
        },
        "reader": reader,
        "truthCheck": results["truth_check"],
        "final": final,
    }
    page = (HERE / "template.html").read_text(encoding="utf-8")
    # The prose of the final test and the row to highlight per model.
    text = json.loads((HERE / "final_text.json").read_text(encoding="utf-8"))
    page = page.replace("/*__FINAL_NOTE__*/", text["note"])
    page = page.replace(
        "/*__FINAL_DECISION__*/",
        "".join(
            f'<div class="panel"><h3>{card["title"]}</h3><p>{card["text"]}</p></div>'
            for card in text["decision"]
        ),
    )
    page = page.replace("/*__ROUND5__*/", round5_section(text.get("round5")))
    page = page.replace(
        "/*__PICKED__*/",
        ", ".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in text["picked"].items()),
    )
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page.replace("/*__DATA__*/", payload), encoding="utf-8")
    print(f"{out}: {out.stat().st_size / 1e6:.1f} MB, {len(shown)} figures, {len(splitters)} splitters")


if __name__ == "__main__":
    main()
