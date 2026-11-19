"""Score every splitter of the check against the truth, alone and with a
second splitter as judge.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/score.py

Reads ``figures.json``, ``truth/`` and ``candidates/``; writes
``results.json`` and ``results.md``.

A figure is **cut right** when the splitter returns as many charts as the
figure has and every chart is found. A chart is **found** when the box
paired with it overlaps it by at least half (intersection over union 0.5;
boxes are paired one to one for the largest total overlap). One chart on
both sides always pairs: a figure that is one chart is cut right by leaving
it whole. A splitter that returns nothing leaves the figure whole. A chart
is **whole in its box** when the box paired with it also covers at least
nine tenths of the chart as the truth drew it (plot, tick labels, axis
titles, own title and legend): the crop made from the box can be read.

**With a judge**: a splitter's cut is kept when the judge finds the same
number of charts in the figure, and the judge's cut is taken when it does
not. No truth is used in that choice.

**A model's count as arbiter**: the model only says how many charts the
figure has. The rule splitter's cut is taken when it has that many charts,
else Heron's when it has, else the model's own boxes. No truth is used.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from common import ROUND, area, figures, iou, overlap, read_candidate
from scipy.optimize import linear_sum_assignment

WHOLE = [0.0, 0.0, 1000.0, 1000.0]
FOUND = 0.5
HELD = 0.9
# name, what it is, kind
CANDIDATES = [
    ("rules", "Rule splitter (today)", "rules"),
    ("heron", "Heron, boxes as they are", "detector"),
    ("heron-cut", "Heron, then the rules' cut", "detector"),
    ("figex2-detector", "FigEx2 detector alone", "detector"),
    ("figex2-scored", "FigEx2 detector, guided", "detector"),
    ("figex2", "FigEx2 as designed", "model"),
    ("gemma4-26b-qat", "Gemma 4 26B (local)", "model"),
    ("sonnet-5-5", "Sonnet 5.5 (cloud)", "model"),
    ("gemini-3-8-flash", "Gemini 3.8 Flash (cloud)", "model"),
    ("gemma4-26b-qat-cut", "Gemma, then the rules' cut", "model"),
    ("sonnet-5-5-cut", "Sonnet, then the rules' cut", "model"),
    ("gemini-3-8-flash-cut", "Gemini, then the rules' cut", "model"),
]
JUDGES = [("heron", "Heron"), ("figex2", "FigEx2")]
ARBITERS = ["gemma4-26b-qat", "sonnet-5-5", "gemini-3-8-flash"]
GROUPS = [("bench", "Bench"), ("showcase", "Showcase paper"), ("other", "Other papers")]


def pair(
    truth: list[list[float]], found: list[list[float]]
) -> list[tuple[int, int, float]]:
    """``(truth index, found index, IoU)`` of the one-to-one pairing with
    the largest total overlap."""
    if not truth or not found:
        return []
    if len(truth) == 1 and len(found) == 1:
        return [(0, 0, 1.0)]
    scores = np.array([[iou(t, f) for f in found] for t in truth])
    rows, cols = linear_sum_assignment(-scores)
    return [(int(r), int(c), float(scores[r, c])) for r, c in zip(rows, cols)]


def judge_figure(truth: list[list[float]], boxes: list[list[float]]) -> dict[str, Any]:
    boxes = boxes or [WHOLE]
    pairs = pair(truth, boxes)
    found = [p for p in pairs if p[2] >= FOUND]
    single = len(truth) == 1 and len(boxes) == 1
    held = sum(
        1
        for t, f, _ in found
        if single or overlap(truth[t], boxes[f]) >= HELD * area(truth[t])
    )
    return {
        "truth": len(truth),
        "returned": len(boxes),
        "found": len(found),
        "held": held,
        "extra": len(boxes) - len(found),
        "count_right": len(boxes) == len(truth),
        "right": len(boxes) == len(truth) and len(found) == len(truth),
    }


def total(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "figures": len(rows),
        "right": sum(r["right"] for r in rows),
        "count_right": sum(r["count_right"] for r in rows),
        "charts": sum(r["truth"] for r in rows),
        "found": sum(r["found"] for r in rows),
        "held": sum(r["held"] for r in rows),
        "extra": sum(r["extra"] for r in rows),
    }


def main() -> None:
    rows = figures()
    truth: dict[str, list[list[float]]] = {}
    notes: dict[str, str] = {}
    for figure in rows:
        record = json.loads((ROUND / "truth" / f"{figure['id']}.json").read_text())
        truth[figure["id"]] = [chart["box"] for chart in record["charts"]]
        if record.get("note"):
            notes[figure["id"]] = record["note"]
    scored = [f for f in rows if truth[f["id"]]]
    left_out = [f["id"] for f in rows if not truth[f["id"]]]

    cuts: dict[str, dict[str, list[list[float]]]] = {}
    raw: dict[str, dict[str, dict[str, Any]]] = {}
    for name, _, _ in CANDIDATES:
        try:
            raw[name] = read_candidate(name)
        except FileNotFoundError:
            continue
        cuts[name] = {
            f["id"]: raw[name].get(f["id"], {}).get("boxes") or [WHOLE] for f in scored
        }

    def table(cut: dict[str, list[list[float]]]) -> dict[str, Any]:
        per = {f["id"]: judge_figure(truth[f["id"]], cut[f["id"]]) for f in scored}
        return {
            "all": total(list(per.values())),
            "groups": {
                key: total([per[f["id"]] for f in scored if f["group"] == key])
                for key, _ in GROUPS
            },
            "figures": per,
        }

    alone = {name: table(cut) for name, cut in cuts.items()}

    judged: dict[str, dict[str, Any]] = {}
    agreement: dict[str, dict[str, Any]] = {}
    for judge, _ in JUDGES:
        if judge not in cuts:
            continue
        judged[judge] = {}
        agreement[judge] = {}
        for name, cut in cuts.items():
            if name == judge:
                continue
            chosen = {
                fid: cut[fid]
                if len(cut[fid]) == len(cuts[judge][fid])
                else cuts[judge][fid]
                for fid in cut
            }
            judged[judge][name] = table(chosen)
            agree = [fid for fid in cut if len(cut[fid]) == len(cuts[judge][fid])]
            differ = [fid for fid in cut if fid not in agree]
            mine, theirs = alone[name]["figures"], alone[judge]["figures"]
            agreement[judge][name] = {
                "agree": len(agree),
                "agree_right": sum(mine[fid]["right"] for fid in agree),
                "differ": len(differ),
                "differ_splitter_right": sum(mine[fid]["right"] for fid in differ),
                "differ_judge_right": sum(theirs[fid]["right"] for fid in differ),
            }

    # The captioning model of FigEx2 by itself says how many panels there
    # are, not where: its count, beside the counts of the other models.
    captioner: dict[str, Any] | None = None
    if "figex2" in raw:
        listed = {
            f["id"]: max(1, len(raw["figex2"].get(f["id"], {}).get("listed", [])))
            for f in scored
        }
        captioner = {
            "count_right": sum(listed[f["id"]] == len(truth[f["id"]]) for f in scored),
            "groups": {
                key: sum(
                    listed[f["id"]] == len(truth[f["id"]])
                    for f in scored
                    if f["group"] == key
                )
                for key, _ in GROUPS
            },
            "counts": listed,
        }

    counters: dict[str, tuple[dict[str, int], dict[str, list[list[float]]]]] = {
        name: ({fid: len(cut) for fid, cut in cuts[name].items()}, cuts[name])
        for name in ARBITERS
        if name in cuts
    }
    if captioner is not None:
        counters["figex2-captioner"] = (captioner["counts"], cuts["figex2"])
    arbiter: dict[str, dict[str, Any]] = {}
    if "rules" in cuts and "heron" in cuts:
        for name, (counts, own) in counters.items():
            source: dict[str, str] = {}
            chosen = {}
            for fid, count in counts.items():
                if len(cuts["rules"][fid]) == count:
                    source[fid], chosen[fid] = "rules", cuts["rules"][fid]
                elif len(cuts["heron"][fid]) == count:
                    source[fid], chosen[fid] = "heron", cuts["heron"][fid]
                else:
                    source[fid], chosen[fid] = "own", own[fid]
            result = table(chosen)
            arbiter[name] = {
                "count_right": sum(
                    counts[f["id"]] == len(truth[f["id"]]) for f in scored
                ),
                "took": {
                    k: sum(v == k for v in source.values())
                    for k in ("rules", "heron", "own")
                },
                "right_by_source": {
                    k: sum(
                        result["figures"][fid]["right"]
                        for fid, v in source.items()
                        if v == k
                    )
                    for k in ("rules", "heron", "own")
                },
                "all": result["all"],
                "groups": result["groups"],
                "source": source,
            }

    known = [f for f in rows if f.get("known_charts")]
    cost = {
        name: {
            "seconds": round(sum(r.get("seconds") or 0 for r in raw[name].values()), 1),
            "cost_usd": round(
                sum(r.get("cost_usd") or 0 for r in raw[name].values()), 4
            ),
            "said_no_data": sum(r.get("has_data") is False for r in raw[name].values()),
            "errors": sum("error" in r for r in raw[name].values()),
        }
        for name in raw
    }
    results = {
        "figures": len(scored),
        "charts": sum(len(truth[f["id"]]) for f in scored),
        "left_out": left_out,
        "truth_check": {
            "figures_with_an_earlier_count": len(known),
            "same_count": sum(len(truth[f["id"]]) == f["known_charts"] for f in known),
            "different": {
                f["id"]: [f["known_charts"], len(truth[f["id"]])]
                for f in known
                if len(truth[f["id"]]) != f["known_charts"]
            },
        },
        "alone": alone,
        "with_judge": judged,
        "agreement": agreement,
        "figex2_captioner": captioner,
        "count_as_arbiter": arbiter,
        "cost": cost,
        "truth_notes": notes,
    }
    (ROUND / "results.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    names = {name: label for name, label, _ in CANDIDATES}
    n = len(scored)
    lines = [
        "# Split check: results",
        "",
        f"{n} figures, {results['charts']} charts. Made by `scripts/score.py`; "
        "the README says what the columns mean.",
        "",
        "## Each splitter alone",
        "",
        "| Splitter | Figures cut right | "
        + " | ".join(label for _, label in GROUPS)
        + " | Right chart count | Charts found | Whole in its box | Extra boxes | Seconds | USD |",
        "|---|---|" + "---|" * len(GROUPS) + "---|---|---|---|---|---|",
    ]
    for name in cuts:
        a = alone[name]["all"]
        groups = " | ".join(
            f"{alone[name]['groups'][key]['right']} of {alone[name]['groups'][key]['figures']}"
            for key, _ in GROUPS
        )
        lines.append(
            f"| {names[name]} | **{a['right']} of {n}** | {groups} | {a['count_right']} | "
            f"{a['found']} of {a['charts']} | {a['held']} | {a['extra']} | "
            f"{cost[name]['seconds']:.0f} | "
            f"{cost[name]['cost_usd'] or ''} |"
        )
    for judge, judge_label in JUDGES:
        if judge not in judged:
            continue
        lines += [
            "",
            f"## With {judge_label} as judge",
            "",
            "| Splitter | Alone | With the judge | They agree on the count | "
            "Right when they agree | They differ | Splitter right | Judge right |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for name in cuts:
            if name == judge:
                continue
            g = agreement[judge][name]
            lines.append(
                f"| {names[name]} | {alone[name]['all']['right']} | "
                f"**{judged[judge][name]['all']['right']}** | {g['agree']} | "
                f"{g['agree_right']} | {g['differ']} | {g['differ_splitter_right']} | "
                f"{g['differ_judge_right']} |"
            )
    if arbiter:
        names["figex2-captioner"] = "FigEx2 captioning model"
        lines += [
            "",
            "## A model's count choosing between the rules' cut and Heron's",
            "",
            "| Count from | Its count is right | Figures cut right | "
            + " | ".join(label for _, label in GROUPS)
            + " | Took the rules' cut (right) | Took Heron's (right) | Took its own boxes (right) |",
            "|---|---|---|" + "---|" * len(GROUPS) + "---|---|---|",
        ]
        for name, a in arbiter.items():
            groups = " | ".join(
                f"{a['groups'][key]['right']} of {a['groups'][key]['figures']}"
                for key, _ in GROUPS
            )
            took = " | ".join(
                f"{a['took'][k]} ({a['right_by_source'][k]})"
                for k in ("rules", "heron", "own")
            )
            lines.append(
                f"| {names[name]} | {a['count_right']} | **{a['all']['right']} of {n}** | "
                f"{groups} | {took} |"
            )
    lines += ["", "## Chart count per figure", ""]
    lines.append("| Figure | Has | " + " | ".join(names[name] for name in cuts) + " |")
    lines.append("|---|---|" + "---|" * len(cuts))
    for figure in scored:
        cells = []
        for name in cuts:
            row = alone[name]["figures"][figure["id"]]
            mark = "" if row["right"] else (" ~" if row["count_right"] else " ✗")
            cells.append(f"{row['returned']}{mark}")
        lines.append(
            f"| {figure['id']} | {len(truth[figure['id']])} | "
            + " | ".join(cells)
            + " |"
        )
    lines += [
        "",
        "✗: wrong number of charts. ~: right number, but a chart is not found "
        "(a box in the wrong place).",
        "",
    ]
    (ROUND / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[: 14 + 2 * len(cuts)]))


if __name__ == "__main__":
    main()
