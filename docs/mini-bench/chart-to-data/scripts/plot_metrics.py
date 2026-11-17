# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Charts of the mini bench's metrics (run ``analyze.py`` first).

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/plot_metrics.py

Writes PNGs to ``metrics/plots/``: accuracy per model, time per model,
accuracy against time, values returned on figures without data, and the
share of each figure's values each model got within 5 % of the axis range.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH = Path(__file__).resolve().parents[1]
PLOTS = BENCH / "metrics" / "plots"
# Okabe-Ito.
BLUE, ORANGE, GREEN, VERMILLION, GREY = (
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#D55E00",
    "#999999",
)


def save(fig: plt.Figure, name: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(PLOTS / name, dpi=150)
    plt.close(fig)


def main() -> None:
    metrics = json.loads(
        (BENCH / "metrics" / "metrics.json").read_text(encoding="utf-8")
    )
    models = metrics["models"]
    names = sorted(models, key=lambda n: models[n]["within_5pct_of_truth_lenient"] or 0)
    best = names[-1]

    fig, ax = plt.subplots(figsize=(8, 5))
    y = range(len(names))
    ax.barh(
        [i + 0.2 for i in y],
        [100 * (models[n]["within_5pct_of_truth_lenient"] or 0) for n in names],
        height=0.4,
        color=BLUE,
        label="within 5 % of the axis range",
    )
    ax.barh(
        [i - 0.2 for i in y],
        [100 * (models[n]["within_2pct_of_truth_lenient"] or 0) for n in names],
        height=0.4,
        color=ORANGE,
        label="within 2 % of the axis range",
    )
    ax.set_yticks(list(y), names)
    ax.set_xlim(0, 100)
    ax.set_xlabel("truth values read correctly (% of all 560, series-lenient)")
    ax.set_title(
        f"{best} reads {100 * (models[best]['within_5pct_of_truth'] or 0):.0f} % of values within 5 %"
    )
    ax.legend(loc="lower right")
    save(fig, "accuracy_by_model.png")

    by_time = sorted(models, key=lambda n: models[n]["seconds_total"] or 0)
    fig, ax = plt.subplots(figsize=(8, 5))
    wasted = [models[n]["seconds_on_no_data_figures"] or 0 for n in by_time]
    useful = [(models[n]["seconds_total"] or 0) - w for n, w in zip(by_time, wasted)]
    ax.barh(by_time, useful, color=BLUE, label="figures with data")
    ax.barh(
        by_time, wasted, left=useful, color=VERMILLION, label="figures without data"
    )
    ax.set_xlabel("seconds for all figures of the bench")
    ax.set_title(f"{by_time[0]} is fastest; time on no-data figures in red")
    ax.legend(loc="lower right")
    save(fig, "time_by_model.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    for name in names:
        m = models[name]
        ax.scatter(
            m["seconds_median_per_figure"] or 0,
            100 * (m["within_5pct_of_truth_lenient"] or 0),
            s=80,
            color=BLUE,
        )
        ax.annotate(
            name,
            (
                m["seconds_median_per_figure"] or 0,
                100 * (m["within_5pct_of_truth_lenient"] or 0),
            ),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=8,
        )
    ax.set_xlabel("median seconds per figure")
    ax.set_ylabel("truth values within 5 % of the axis range (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Accuracy against time per figure (up and left is better)")
    save(fig, "accuracy_vs_time.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    false_values = [models[n]["values_on_no_data_figures"] for n in names]
    ax.barh(names, false_values, color=VERMILLION)
    ax.set_xlabel("values returned for figures that hold no data (count)")
    ax.set_title("Values invented on diagrams and ECG traces")
    save(fig, "values_on_no_data_figures.png")

    rows = [r for r in metrics["per_figure"] if r["has_data"]]
    figures = sorted({r["figure_id"] for r in rows})
    grid = [
        [
            next(
                (
                    (r["hits_05_lenient"] / r["truth_values"])
                    if r["truth_values"]
                    else 0.0
                    for r in rows
                    if r["model"] == name and r["figure_id"] == figure
                ),
                0.0,
            )
            for figure in figures
        ]
        for name in names
    ]
    fig, ax = plt.subplots(figsize=(12, 8) if len(figures) > 8 else (8, 5))
    image = ax.imshow(grid, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(figures)), figures)
    ax.set_yticks(range(len(names)), names)
    for i, line in enumerate(grid):
        for j, value in enumerate(line):
            ax.text(
                j,
                i,
                f"{100 * value:.0f}",
                ha="center",
                va="center",
                color="white" if value < 0.6 else "black",
                fontsize=8,
            )
    ax.set_xlabel("figure (data charts only)")
    ax.set_title("Share of each figure's values within 5 % of the axis range (%)")
    fig.colorbar(image, ax=ax, label="share of truth values")
    save(fig, "within_5pct_by_figure.png")
    print("plots written to", PLOTS)


if __name__ == "__main__":
    main()
