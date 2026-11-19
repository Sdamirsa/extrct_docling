"""The sample of the final test: the figures that are tricky today.

    uv run --no-sync python .../scripts/final_sample.py

A figure is tricky when the rule splitter cuts it wrong, or when the
rules' cutter, started from the chart list of Gemma, Sonnet or Gemini,
cuts it wrong (the candidates of the first part, no caption). Writes
``final-test/sample.json`` and prints the ids.
"""

from __future__ import annotations

import json

from common import ROUND, figures, read_candidate
from score import WHOLE, judge_figure

PROBES = ["rules", "gemma4-26b-qat-cut", "sonnet-5-5-cut", "gemini-3-8-flash-cut"]


def main() -> None:
    rows = figures()
    wrong: dict[str, list[str]] = {}
    for name in PROBES:
        raw = read_candidate(name)
        for figure in rows:
            record = json.loads(
                (ROUND / "truth" / f"{figure['id']}.json").read_text(encoding="utf-8")
            )
            truth = [chart["box"] for chart in record["charts"]]
            boxes = raw.get(figure["id"], {}).get("boxes") or [WHOLE]
            if not judge_figure(truth, boxes)["right"]:
                wrong.setdefault(figure["id"], []).append(name)
    target = ROUND / "final-test" / "sample.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "rule": "cut wrong by the rule splitter, or by the rules' cutter "
                "started from the chart list of Gemma, Sonnet or Gemini "
                "(first part, no caption)",
                "tricky": sorted(wrong),
                "cut_wrong_by": dict(sorted(wrong.items())),
                "easy": sorted(f["id"] for f in rows if f["id"] not in wrong),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(" ".join(sorted(wrong)))


if __name__ == "__main__":
    main()
