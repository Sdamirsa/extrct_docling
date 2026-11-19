"""Draw the cuts of a few figures as box diagrams for ``examples/``.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/make_examples.py

Only figures of the showcase paper are shown: its images are in the
repository already (``showcase/``, CC BY-NC-ND 4.0), the other papers'
are not. A diagram holds no part of a figure: it is the outline of the
image with the boxes of one cut, so the figure itself stays as it is and
is linked beside it.

Per figure one ``examples/<id>.svg``: the truth, the rule splitter of
today, and the recommended cut with the local and with the cloud model
(``candidates/<model>-recommended.json``, ``score_final.py``).
"""

from __future__ import annotations

import json
from html import escape

from common import ROUND, figures, read_candidate
from score import WHOLE, judge_figure

EXAMPLES = ["S03", "S06", "S11"]
CUTS = [
    ("rules", "Rule splitter, today"),
    ("gemma4-26b-qat-recommended", "Recommended, local"),
    ("sonnet-5-5-recommended", "Recommended, cloud"),
]
WIDTH = 210
GAP = 28
PAD = 12
HEAD = 52
FOOT = 30
INK = "#0e1217"
GOOD = "#0a7d0a"
BAD = "#c22f2f"


def counted(number: int, noun: str) -> str:
    plural = "es" if noun.endswith("x") else "s"
    return f"{number} {noun}{'' if number == 1 else plural}"


def diagram(x: float, height: float, title: str, boxes: list, note: str, colour: str) -> str:
    parts = [
        f'<text x="{x}" y="22" font-size="13" font-weight="600" fill="{INK}">{escape(title)}</text>',
        f'<text x="{x}" y="40" font-size="12" fill="{colour}">{escape(note)}</text>',
        f'<rect x="{x}" y="{HEAD}" width="{WIDTH}" height="{height:.1f}" fill="#ffffff" stroke="#c5ccd6"/>',
    ]
    for index, (x0, y0, x1, y1) in enumerate(boxes, 1):
        bx, by = x + x0 / 1000 * WIDTH, HEAD + y0 / 1000 * height
        bw, bh = (x1 - x0) / 1000 * WIDTH, (y1 - y0) / 1000 * height
        parts.append(
            f'<rect x="{bx + 1.5:.1f}" y="{by + 1.5:.1f}" width="{max(bw - 3, 1):.1f}" '
            f'height="{max(bh - 3, 1):.1f}" fill="{colour}" fill-opacity="0.08" '
            f'stroke="{colour}" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{bx + bw / 2:.1f}" y="{by + bh / 2 + 4:.1f}" font-size="12" '
            f'text-anchor="middle" fill="{colour}">{index}</text>'
        )
    return "\n".join(parts)


def main() -> None:
    by_id = {f["id"]: f for f in figures()}
    target = ROUND / "examples"
    target.mkdir(exist_ok=True)
    for figure_id in EXAMPLES:
        figure = by_id[figure_id]
        record = json.loads((ROUND / "truth" / f"{figure_id}.json").read_text(encoding="utf-8"))
        truth = [chart["box"] for chart in record["charts"]]
        height = WIDTH * figure["height"] / figure["width"]
        columns = [diagram(PAD, height, "Truth", truth, counted(len(truth), "chart"), INK)]
        facts = [f"{figure_id}: truth {len(truth)}"]
        for position, (name, title) in enumerate(CUTS, 1):
            row = read_candidate(name)[figure_id]
            boxes = row.get("boxes") or [WHOLE]
            judged = judge_figure(truth, boxes)
            note = counted(len(boxes), "box") + (
                ": cut right"
                if judged["right"]
                else ": a box off its chart"
                if judged["count_right"]
                else ": wrong number"
            )
            columns.append(
                diagram(
                    PAD + position * (WIDTH + GAP), height, title, boxes, note,
                    GOOD if judged["right"] else BAD,
                )
            )
            facts.append(f"{name} {len(boxes)} {'right' if judged['right'] else 'wrong'} from {row.get('from', '-')}")
        total = 2 * PAD + len(columns) * WIDTH + (len(columns) - 1) * GAP
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" '
            f'height="{HEAD + height + FOOT:.0f}" viewBox="0 0 {total} {HEAD + height + FOOT:.0f}" '
            'font-family="system-ui, -apple-system, Segoe UI, sans-serif">\n'
            f'<rect width="{total}" height="{HEAD + height + FOOT:.0f}" fill="#f6f8fa"/>\n'
            + "\n".join(columns)
            + f'\n<text x="{PAD}" y="{HEAD + height + 20:.0f}" font-size="11" fill="#57606a">'
            "Each diagram is the outline of the figure image with the boxes of one cut.</text>\n</svg>\n"
        )
        (target / f"{figure_id}.svg").write_text(svg, encoding="utf-8")
        print(" | ".join(facts))


if __name__ == "__main__":
    main()
