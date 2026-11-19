"""Score the final test: the figure's caption in the chart list, the raw
rule split beside it, and a ruling call where the two differ.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/score_final.py

For each model (Gemma locally, Sonnet and Gemini through the cloud
endpoint) and the figures it was run on, against the truth of the check:

- ``rules``: the rule splitter alone, as today;
- ``one_rule``: the chart list without caption; the rules' cut when it has
  the list's number of charts, else the rules' cutter started from the list;
- ``caption_one_rule``: the same with the caption in the list call;
- ``ruling`` / ``caption_ruling``: the rules' cut and the cutter started
  from the list are both made; where they are the same cut it is taken,
  where they differ the model sees both and its boolean picks one
  (``run_ruling.py``);
- ``*_by_count``: the same call, read the other way: the cut that has the
  number of charts the model answers, and the boolean only when both or
  neither have it;
- ``either``: the ceiling of any ruling, the figures on which one of the
  two cuts is right.

Writes ``final-test/results.json``, ``final-test/results.md`` and, per
model, ``candidates/<model>-final.json`` (the cut of ``caption_ruling``) and
``candidates/<model>-recommended.json`` (the cut of ``one_rule``).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from common import ROUND, figures, read_candidate, write_candidate
from score import WHOLE, judge_figure, total

FINAL = ROUND / "final-test"
CONFIGS = [
    ("gemma4-26b-qat", "Local: Gemma 4 26B"),
    ("sonnet-5-5", "Cloud: Sonnet 5.5"),
    ("gemini-3-8-flash", "Cloud: Gemini 3.8 Flash"),
]
VARIANTS = [
    ("rules", "Rule splitter alone (today)"),
    ("one_rule", "No caption: the one rule"),
    ("ruling", "No caption: both cuts, a ruling where they differ"),
    ("ruling_by_count", "No caption: the ruling read by its number"),
    ("caption_one_rule", "Caption: the one rule"),
    ("caption_ruling", "Caption: both cuts, a ruling where they differ"),
    ("caption_ruling_by_count", "Caption: the ruling read by its number"),
]
SETS = [("all", "All figures run"), ("tricky", "Tricky today"), ("easy", "Easy today")]

Cuts = dict[str, list[list[float]]]
Pick = Callable[[str], tuple[str, list[list[float]]] | None]


def rulings(name: str) -> dict[str, dict[str, Any]]:
    path = FINAL / "rulings" / f"{name}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["figures"]


def main() -> None:
    rows = figures()
    sample = json.loads((FINAL / "sample.json").read_text(encoding="utf-8"))
    truth = {
        f["id"]: [
            chart["box"]
            for chart in json.loads(
                (ROUND / "truth" / f"{f['id']}.json").read_text(encoding="utf-8")
            )["charts"]
        ]
        for f in rows
    }

    def cuts(name: str) -> Cuts:
        raw = read_candidate(name)
        return {f["id"]: raw.get(f["id"], {}).get("boxes") or [WHOLE] for f in rows}

    def right(figure_id: str, boxes: list[list[float]]) -> bool:
        return judge_figure(truth[figure_id], boxes)["right"]

    rules = cuts("rules")
    out: dict[str, Any] = {}
    for model, title in CONFIGS:
        try:
            listed = read_candidate(f"{model}-caption")
        except FileNotFoundError:
            continue
        ran = [f["id"] for f in rows if "error" not in listed.get(f["id"], {"error": 1})]
        own = {"": cuts(model), "caption": cuts(f"{model}-caption")}
        seeded = {"": cuts(f"{model}-cut"), "caption": cuts(f"{model}-caption-cut")}
        ruled = {"": rulings(model), "caption": rulings(f"{model}-caption")}
        calls = {"": read_candidate(model), "caption": listed}

        def one_rule(kind: str) -> Pick:
            return lambda i: (
                ("rules", rules[i])
                if len(rules[i]) == len(own[kind][i])
                else ("list", seeded[kind][i])
            )

        def ruling(kind: str, by_count: bool) -> Pick:
            def pick(i: str) -> tuple[str, list[list[float]]] | None:
                row = ruled[kind].get(i)
                if row is None or "error" in row:
                    return None
                if row["same"]:
                    return "same", rules[i]
                picked = row["picked"]
                if by_count:
                    has = [
                        name
                        for name, cut in (("rules", rules[i]), ("list", seeded[kind][i]))
                        if len(cut) == row["charts"]
                    ]
                    picked = has[0] if len(has) == 1 else picked
                return picked, rules[i] if picked == "rules" else seeded[kind][i]

            return pick

        picks: dict[str, Pick] = {
            "rules": lambda i: ("rules", rules[i]),
            "one_rule": one_rule(""),
            "ruling": ruling("", False),
            "ruling_by_count": ruling("", True),
            "caption_one_rule": one_rule("caption"),
            "caption_ruling": ruling("caption", False),
            "caption_ruling_by_count": ruling("caption", True),
        }
        sets = {
            "all": ran,
            "tricky": [i for i in ran if i in sample["tricky"]],
            "easy": [i for i in ran if i in sample["easy"]],
        }
        scored: dict[str, Any] = {}
        per_figure: dict[str, dict[str, Any]] = {i: {} for i in ran}
        final_cut: dict[str, dict[str, Any]] = {}
        recommended: dict[str, dict[str, Any]] = {}
        for key, _ in VARIANTS:
            taken = {i: picks[key](i) for i in ran}
            if any(cut is None for cut in taken.values()):
                continue
            judged = {i: judge_figure(truth[i], cut[1]) for i, cut in taken.items() if cut}
            scored[key] = {name: total([judged[i] for i in ids]) for name, ids in sets.items()}
            for i, cut in taken.items():
                if cut:
                    per_figure[i][key] = {"from": cut[0], "right": judged[i]["right"]}
            if key == "caption_ruling":
                for i, cut in taken.items():
                    if cut:
                        final_cut[i] = {
                            "boxes": cut[1],
                            "from": cut[0],
                            "ruling": ruled["caption"].get(i),
                            "list": {
                                k: listed[i].get(k)
                                for k in ("description", "kinds", "seconds", "cost_usd")
                            },
                        }
        # The recommended cut needs no run of the final test: the lists
        # without caption are those of the first part, on all 51 figures.
        for figure in rows:
            i = figure["id"]
            if "error" in calls[""].get(i, {"error": 1}):
                continue
            source, boxes = picks["one_rule"](i) or ("rules", rules[i])
            recommended[i] = {
                "boxes": boxes,
                "from": source,
                "counts": {"rules": len(rules[i]), "list": len(own[""][i])},
                "list": {
                    k: calls[""][i].get(k)
                    for k in ("description", "kinds", "seconds", "cost_usd")
                },
            }
        ceiling = {
            kind or "no_caption": {
                name: sum(right(i, rules[i]) or right(i, seeded[kind][i]) for i in ids)
                for name, ids in sets.items()
            }
            for kind in ("", "caption")
        }
        count = {
            kind or "no_caption": {
                name: {
                    "count_right": sum(len(own[kind][i]) == len(truth[i]) for i in ids),
                    "own_boxes_right": sum(right(i, own[kind][i]) for i in ids),
                    "seeded_right": sum(right(i, seeded[kind][i]) for i in ids),
                }
                for name, ids in sets.items()
            }
            for kind in ("", "caption")
        }
        asked_stats: dict[str, Any] = {}
        for kind in ("", "caption"):
            asked = [
                i for i in ran if ruled[kind].get(i, {}).get("same") is False
                and "error" not in ruled[kind][i]
            ]
            if not asked and not ruled[kind]:
                continue
            stats = {
                "figures": len([i for i in ran if i in ruled[kind]]),
                "asked": len(asked),
                "one_right": 0,
                "one_right_picked": 0,
                "one_right_picked_by_count": 0,
                "neither": 0,
                "neither_flagged": 0,
                "one_right_flagged": 0,
                "both": 0,
                "count_right": 0,
                "seconds": round(sum(ruled[kind][i].get("seconds") or 0 for i in asked), 1),
                "cost_usd": round(sum(ruled[kind][i].get("cost_usd") or 0 for i in asked), 4),
            }
            for i in asked:
                row = ruled[kind][i]
                good = {"rules": right(i, rules[i]), "list": right(i, seeded[kind][i])}
                matches = [
                    name
                    for name, cut in (("rules", rules[i]), ("list", seeded[kind][i]))
                    if len(cut) == row["charts"]
                ]
                by_count = matches[0] if len(matches) == 1 else row["picked"]
                stats["count_right"] += row["charts"] == len(truth[i])
                if good["rules"] and good["list"]:
                    stats["both"] += 1
                elif good["rules"] or good["list"]:
                    stats["one_right"] += 1
                    stats["one_right_picked"] += good[row["picked"]]
                    stats["one_right_picked_by_count"] += good[by_count]
                    stats["one_right_flagged"] += not matches
                else:
                    stats["neither"] += 1
                    stats["neither_flagged"] += not matches
            asked_stats[kind or "no_caption"] = stats
        list_calls = {
            kind or "no_caption": {
                "seconds": round(sum(calls[kind][i].get("seconds") or 0 for i in ran), 1),
                "cost_usd": round(sum(calls[kind][i].get("cost_usd") or 0 for i in ran), 4),
            }
            for kind in ("", "caption")
        }
        out[model] = {
            "title": title,
            "figures": {name: len(ids) for name, ids in sets.items()},
            "charts": {name: sum(len(truth[i]) for i in ids) for name, ids in sets.items()},
            "variants": scored,
            "ceiling": ceiling,
            "list": count,
            "ruling": asked_stats,
            "list_calls": list_calls,
            "per_figure": per_figure,
        }
        if recommended:
            write_candidate(
                f"{model}-recommended",
                f"The recommended cut with {title}: the rule splitter's cut when it "
                "has the number of charts the model lists (no caption), else the "
                "rules' cutter started from the model's boxes.",
                recommended,
            )
        if final_cut:
            write_candidate(
                f"{model}-final",
                f"The final test's cut with {title}: the rule splitter's cut and the "
                "rules' cutter started from the model's chart list (caption given); "
                "where they differ, the cut the model's ruling picked.",
                final_cut,
            )

    (FINAL / "results.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    lines = ["# Final test: results", ""]
    for model, _ in CONFIGS:
        if model not in out:
            continue
        cell = out[model]
        lines += [f"## {cell['title']}", ""]
        heads = [f"{label} ({cell['figures'][name]})" for name, label in SETS]
        lines.append("| Cut from | " + " | ".join(heads) + " | Charts whole, all run |")
        lines.append("|---|" + "---|" * (len(SETS) + 1))
        for key, label in VARIANTS:
            if key not in cell["variants"]:
                continue
            score = cell["variants"][key]
            lines.append(
                f"| {label} | "
                + " | ".join(str(score[name]["right"]) for name, _ in SETS)
                + f" | {score['all']['held']} of {cell['charts']['all']} |"
            )
        for kind, label in (("no_caption", "no caption"), ("caption", "caption")):
            lines.append(
                f"| Ceiling, {label}: one of the two cuts is right | "
                + " | ".join(str(cell["ceiling"][kind][name]) for name, _ in SETS)
                + " | |"
            )
        lines += ["", "| The chart list | Count right | Own boxes cut right | Through the cutter |", "|---|---|---|---|"]
        for kind, label in (("no_caption", "without the caption"), ("caption", "with the caption")):
            c = cell["list"][kind]["all"]
            lines.append(
                f"| {label} | {c['count_right']} of {cell['figures']['all']} | "
                f"{c['own_boxes_right']} | {c['seeded_right']} |"
            )
        lines += ["", "| The ruling call | Asked | One cut right: picked it | read by its number | Neither right: number fits neither | Number of charts right | Seconds a call | USD |", "|---|---|---|---|---|---|---|---|"]
        for kind, label in (("no_caption", "no caption"), ("caption", "caption")):
            if kind not in cell["ruling"]:
                continue
            s = cell["ruling"][kind]
            lines.append(
                f"| {label} | {s['asked']} of {s['figures']} | "
                f"{s['one_right_picked']} of {s['one_right']} | "
                f"{s['one_right_picked_by_count']} of {s['one_right']} | "
                f"{s['neither_flagged']} of {s['neither']} | {s['count_right']} of {s['asked']} | "
                f"{s['seconds'] / max(s['asked'], 1):.1f} | {s['cost_usd']:.2f} |"
            )
        lines.append("")
    (FINAL / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
