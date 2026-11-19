"""One rule for every reading method, scored from the candidate files.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/score_one_rule.py

No model runs. The rule: the reading model lists the charts; when the rule
splitter's own cut has that many charts it is taken, and when it has not,
the model's boxes are the seeds of the splitter's cutter (``cutter.py``).

The rule was written after the tables of ``score.py`` were read, on the
same 51 figures: it is a reading of those results, not a test of them.
Beside it the table has what it is made of and what it replaces: the
model's own boxes, the seeded cut everywhere, the measured arbiter (the
rules' cut, else Heron's, else the model's boxes) and the rule with Heron
put between its two steps.

Also counted: on the figures where the rule splitter and the model find a
different number of charts, which of the two has the number right.

Writes ``extra/one-rule.json`` and prints the tables.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from common import ROUND, figures, read_candidate
from score import GROUPS, WHOLE, judge_figure, total

MODELS = [
    ("gemma4-26b-qat", "Gemma 4 26B (local)"),
    ("sonnet-5-5", "Sonnet 5.5 (cloud)"),
    ("gemini-3-8-flash", "Gemini 3.8 Flash (cloud)"),
]
ONE_RULE = "one_rule"
POLICIES = [
    ("own", "The model's own boxes"),
    ("seeded", "The model's boxes as seeds, on every figure"),
    ("arbiter", "Measured arbiter: rules' cut, else Heron's, else own boxes"),
    (ONE_RULE, "One rule: rules' cut on the same count, else seeded"),
    ("one_rule_heron", "The one rule with Heron's cut between its two steps"),
]

Cuts = dict[str, list[list[float]]]
Pick = Callable[[str], tuple[str, list[list[float]]]]


def main() -> None:
    rows = figures()
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

    rules, heron = cuts("rules"), cuts("heron")
    out: dict[str, Any] = {}
    for model, title in MODELS:
        own, seeded = cuts(model), cuts(f"{model}-cut")

        def same(other: Cuts, figure_id: str, own: Cuts = own) -> bool:
            return len(other[figure_id]) == len(own[figure_id])

        def one_rule(i: str, own: Cuts = own, seeded: Cuts = seeded) -> tuple:
            return ("rules", rules[i]) if same(rules, i) else ("seeded", seeded[i])

        def arbiter(i: str, own: Cuts = own) -> tuple:
            if same(rules, i):
                return "rules", rules[i]
            return ("heron", heron[i]) if same(heron, i) else ("own", own[i])

        def with_heron(i: str, own: Cuts = own, seeded: Cuts = seeded) -> tuple:
            if same(rules, i):
                return "rules", rules[i]
            return ("heron", heron[i]) if same(heron, i) else ("seeded", seeded[i])

        picks: dict[str, Pick] = {
            "own": lambda i, own=own: ("own", own[i]),
            "seeded": lambda i, seeded=seeded: ("seeded", seeded[i]),
            "arbiter": arbiter,
            ONE_RULE: one_rule,
            "one_rule_heron": with_heron,
        }
        scored: dict[str, Any] = {}
        for key, _ in POLICIES:
            judged, source = {}, {}
            for f in rows:
                source[f["id"]], boxes = picks[key](f["id"])
                judged[f["id"]] = judge_figure(truth[f["id"]], boxes)
            taken: dict[str, dict[str, int]] = {}
            for figure_id, name in source.items():
                cell = taken.setdefault(name, {"figures": 0, "right": 0})
                cell["figures"] += 1
                cell["right"] += judged[figure_id]["right"]
            scored[key] = {
                "all": total(list(judged.values())),
                "groups": {
                    group: sum(judged[f["id"]]["right"] for f in rows if f["group"] == group)
                    for group, _ in GROUPS
                },
                "taken": taken,
                "source": source,
                "right": {i: r["right"] for i, r in judged.items()},
            }
        agree = [f["id"] for f in rows if same(rules, f["id"])]
        differ = [f["id"] for f in rows if not same(rules, f["id"])]
        scored["count"] = {
            "agree": len(agree),
            "agree_cut_right": sum(scored[ONE_RULE]["right"][i] for i in agree),
            "differ": len(differ),
            "differ_model_count_right": sum(
                len(own[i]) == len(truth[i]) for i in differ
            ),
            "differ_rules_count_right": sum(
                len(rules[i]) == len(truth[i]) for i in differ
            ),
            "differ_cut_right": sum(scored[ONE_RULE]["right"][i] for i in differ),
        }
        out[model] = {"title": title, **scored}

    (ROUND / "extra" / "one-rule.json").write_text(
        json.dumps(out, indent=1) + "\n", encoding="utf-8"
    )
    print("| Model | Cut from | Figures cut right | Bench | Showcase | Other | Whole |")
    print("|---|---|---|---|---|---|---|")
    for model, title in MODELS:
        for key, label in POLICIES:
            cell = out[model][key]
            mark = "**" if key == ONE_RULE else ""
            print(
                f"| {title} | {label} | {mark}{cell['all']['right']} of 51{mark} | "
                + " | ".join(str(cell["groups"][group]) for group, _ in GROUPS)
                + f" | {cell['all']['held']} |"
            )
    print()
    print(
        "| Model | Same count as the rules | cut right | Different count | "
        "model's count right | rules' count right | cut right |"
    )
    print("|---|---|---|---|---|---|---|")
    for model, title in MODELS:
        c = out[model]["count"]
        print(
            f"| {title} | {c['agree']} | {c['agree_cut_right']} | {c['differ']} | "
            f"{c['differ_model_count_right']} | {c['differ_rules_count_right']} | "
            f"{c['differ_cut_right']} |"
        )


if __name__ == "__main__":
    main()
