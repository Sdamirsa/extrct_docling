"""Two synthetic charts with random values, in the style of bench figures C1
and B4, for a control: can a reader's precision come from the image alone?
The values exist nowhere but in this script's output.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/control_charts.py \
        <folder for S1.png and S2.png> <file for the drawn values>

Keep the drawn values where the reader cannot see them.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

out, secret = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261117)
truth = {}

fig, axes = plt.subplots(1, 4, figsize=(15.2, 4.05), dpi=100)
names = ["Baseline", "Reviewer", "Reviewer + Baseline"]
titles = ["Top-1 Recall on Set A", "Top-1 Precision on Set A", "Top-3 Recall on Set A", "Top-3 Precision on Set A"]
bars = {}
for ax, title in zip(axes, titles):
    vals = np.round(rng.uniform(0.31, 0.86, 3), 3)
    bars[title] = dict(zip(names, vals.tolist()))
    ax.bar(names, vals, width=0.4, color=["#c9e2e2", "#cfccdc", "#aeb9d2"])
    ax.set_ylim(0.2, 0.9)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_title(title, fontsize=10)
    ax.tick_params(axis="x", rotation=30)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
axes[0].set_ylabel("Accuracy")
fig.tight_layout()
fig.savefig(out / "S1.png")
truth["S1"] = bars

fig, ax = plt.subplots(figsize=(10.2, 5.2), dpi=150)
domains = ["Overall quality", "Clarity", "Completeness", "Accuracy", "Readability"]
centres = np.round(rng.uniform(-1.1, 0.9, 5), 3)
half = np.round(rng.uniform(0.12, 0.38, 5), 3)
ys = np.arange(len(domains))[::-1]
ax.errorbar(centres, ys, xerr=half, fmt="o", color="#1f3b63", capsize=4)
ax.axvline(0, color="grey", linestyle="--", linewidth=1)
ax.set_yticks(ys, domains)
ax.set_xlim(-1.75, 1.75)
ax.set_xticks([-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5])
ax.set_xlabel("Mean difference (reviewed minus original)")
ax.set_ylabel("Rating domain")
fig.tight_layout()
fig.savefig(out / "S2.png")
truth["S2"] = {
    d: {"value": float(c), "lo": round(float(c - h), 3), "hi": round(float(c + h), 3)}
    for d, c, h in zip(domains, centres, half)
}
secret.write_text(json.dumps(truth, indent=1))
print(json.dumps(truth))
