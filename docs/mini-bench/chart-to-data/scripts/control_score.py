"""Compare a by-eye read of the two control charts with the values they
were drawn from.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/control_score.py \
        docs/mini-bench/chart-to-data/round-2/sonnet/control

The folder holds ``drawn.json`` (written by ``control_charts.py``) and the
reader's ``S1.read.json`` and ``S2.read.json``.
"""

import json
import sys
from pathlib import Path

import numpy as np

out = Path(sys.argv[1])
truth = json.loads((out / "drawn.json").read_text())
s1 = json.loads((out / "S1.read.json").read_text())
errs = []
for panel in s1["panels"]:
    want = truth["S1"][panel["title"]]
    for label, value in panel["bars"].items():
        errs.append(abs(value - want[label]) / 0.7 * 100)
        print(f"S1 {panel['title'][:24]:24} {label[:20]:20} read {value:.3f} drawn {want[label]:.3f}")
e = np.array(errs)
print(f"S1 bars: error as % of the 0.2-0.9 axis: median {np.median(e):.2f}, max {e.max():.2f}")
s2 = json.loads((out / "S2.read.json").read_text())
errs = []
for row in s2["rows"]:
    want = truth["S2"][row["label"]]
    for key in ("value", "lo", "hi"):
        errs.append(abs(row[key] - want[key]) / 3.0 * 100)
    print(f"S2 {row['label'][:16]:16} read {row['value']:.3f} [{row['lo']:.3f}, {row['hi']:.3f}] drawn {want['value']:.3f} [{want['lo']:.3f}, {want['hi']:.3f}]")
e = np.array(errs)
print(f"S2 intervals: error as % of the -1.5..1.5 axis: median {np.median(e):.2f}, max {e.max():.2f}")
