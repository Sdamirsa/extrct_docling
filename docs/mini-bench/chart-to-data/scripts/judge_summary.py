# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Aggregate the judges' files (``judge/<model>.json``) into
``judge/summary.md`` and ``metrics/plots/error_types_by_model.png``.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/judge_summary.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH = Path(__file__).resolve().parents[1]
VERDICTS = ["correct", "partial", "wrong", "missed", "true_negative", "false_positive"]


def main() -> None:
    judged = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((BENCH / "judge").glob("*.json"))
        if path.name != "config.json"
    }
    codes = sorted(
        {
            code
            for j in judged.values()
            for f in j["figures"]
            for code in f["error_types"]
        }
    )
    lines = [
        "# Judge summary\n",
        "Verdicts per model (15 figures: 10 data charts, 5 without data).\n",
        "| model | " + " | ".join(VERDICTS) + " | usable figures | dominant failure |",
        "|---|" + "---|" * (len(VERDICTS) + 2),
    ]
    counts: dict[str, Counter[str]] = {}
    for name, j in judged.items():
        verdicts = Counter(f["verdict"] for f in j["figures"])
        counts[name] = Counter(code for f in j["figures"] for code in f["error_types"])
        lines.append(
            f"| {name} | "
            + " | ".join(str(verdicts.get(v, 0)) for v in VERDICTS)
            + f" | {sum(1 for f in j['figures'] if f['usable'])} "
            f"| {j['summary'].get('dominant_failure')} |"
        )
    lines += [
        "\nFigures on which each error type was assigned.\n",
        "| error type | " + " | ".join(judged) + " |",
        "|---|" + "---|" * len(judged),
    ]
    lines += [
        f"| {code} | "
        + " | ".join(str(counts[name].get(code, 0)) for name in judged)
        + " |"
        for code in codes
    ]
    lines.append("\n## Assessments\n")
    lines += [
        f"**{name}.** {j['summary'].get('assessment', '')}\n"
        for name, j in judged.items()
    ]
    (BENCH / "judge" / "summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(12, 8))
    image = ax.imshow(
        [[counts[name].get(code, 0) for name in judged] for code in codes],
        cmap="viridis",
        aspect="auto",
    )
    ax.set_xticks(range(len(judged)), list(judged), rotation=45, ha="right")
    ax.set_yticks(range(len(codes)), codes)
    for i, code in enumerate(codes):
        for j, name in enumerate(judged):
            ax.text(
                j, i, counts[name].get(code, 0), ha="center", va="center", color="white"
            )
    ax.set_xlabel("model")
    ax.set_ylabel("error type assigned by the judge")
    ax.set_title("Figures (of 15) on which each error type occurs, per model")
    fig.colorbar(image, ax=ax, label="figures")
    fig.tight_layout()
    plots = BENCH / "metrics" / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    fig.savefig(plots / "error_types_by_model.png", dpi=150)
    print((BENCH / "judge" / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
