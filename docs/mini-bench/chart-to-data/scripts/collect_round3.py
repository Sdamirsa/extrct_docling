# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Bring one method's run of the figure-to-data step into the round folder.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/collect_round3.py \
        <work folder>/<label> <label>

Copies ``<label>/<bundle>/figure-to-data/`` to
``round-3/runs/<label>/<bundle>/figure-to-data/`` (the readings, the run
records, the session traces; images and evidence are git-ignored) and
writes ``round-3/runs/<label>/timing.json``, one row per figure, in the
form the scripts of the earlier rounds read.

With ``--audit`` it also writes ``round-3/runs/<label>/AUDIT.md``: for each
agent session, the tools it was offered and the tools it called. A cloud
run has none: its model gets one HTTP request and no tool.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
ROUND = BENCH / "round-3"
ALLOWED = {
    "agent": {
        "mcp__figure__look",
        "mcp__figure__record_chart",
        "mcp__figure__finish",
    },
}


def main() -> None:
    work, label = Path(sys.argv[1]), sys.argv[2]
    target = ROUND / "runs" / label
    if target.exists():
        shutil.rmtree(target)
    rows: list[dict] = []
    audit: list[str] = []
    for step in sorted(work.glob("*/figure-to-data")):
        bundle = step.parent.name
        shutil.copytree(step, target / bundle / "figure-to-data")
        records = sorted((step / "runs").glob("*.json"))
        if not records:
            continue
        run = json.loads(records[-1].read_text(encoding="utf-8"))
        for figure in run["figures"]:
            folder = step / figure["folder"]
            result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
            gpu = max(
                (m.get("size_vram", 0) for m in result.get("ollama_ps", [])),
                default=None,
            )
            rows.append(
                {
                    "bundle": bundle,
                    "self_ref": figure["self_ref"],
                    "mode": run["method"],
                    "model": run["model"],
                    "backend": run["backend"],
                    "status": figure["status"],
                    "panels": figure["charts"],
                    "rows": figure["values"],
                    "seconds": figure["seconds"],
                    "calls": figure["calls"],
                    "tool_calls": figure["tool_calls"],
                    "prompt_tokens": figure["input_tokens"],
                    "eval_tokens": figure["output_tokens"],
                    "cost_usd": figure["cost_usd"],
                    "gpu_bytes": gpu,
                    "issues": len(result.get("issues", [])),
                    "notes": figure["notes"],
                }
            )
            trace = folder / "trace.json"
            if trace.is_file() and run["method"] == "agent":
                audit.append(audit_row(bundle, figure["folder"], trace, run["method"]))
    (target / "timing.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    seconds = sum(row["seconds"] for row in rows)
    costs = [row["cost_usd"] for row in rows if row["cost_usd"] is not None]
    print(
        f"{label}: {len(rows)} figures, {seconds:.0f} s, "
        f"{sum(row['rows'] for row in rows)} values, "
        f"cost {sum(costs):.2f}" + ("" if costs else " (not reported)"),
        dict(Counter(row["status"] for row in rows)),
    )
    if "--audit" in sys.argv and audit:
        (target / "AUDIT.md").write_text(
            f"# What the {label} sessions could do, and did\n\n"
            "Read from each session's event stream (`trace.json`, kept "
            "locally). `offered` is every tool the session had; a session "
            "has no file, shell or web tool unless it is listed here.\n\n"
            "| figure | offered | called | outside the allowed set |\n"
            "|---|---|---|---|\n" + "\n".join(audit) + "\n",
            encoding="utf-8",
        )


def audit_row(bundle: str, folder: str, trace: Path, method: str) -> str:
    events = json.loads(trace.read_text(encoding="utf-8"))["events"]
    offered: list[str] = []
    called: Counter[str] = Counter()
    for event in events:
        if event["type"] == "init":
            offered = event.get("tools") or []
        elif event["type"] == "assistant":
            for block in event["content"]:
                if block.get("type") == "tool_use":
                    called[str(block.get("name"))] += 1
    allowed = ALLOWED.get(method, set())
    outside = sorted((set(offered) | set(called)) - allowed)
    calls = ", ".join(f"{name.split('__')[-1]} x{n}" for name, n in called.items())
    return (
        f"| {bundle} {folder} | {', '.join(t.split('__')[-1] for t in offered)} "
        f"| {calls or 'none'} | {', '.join(outside) or 'none'} |"
    )


if __name__ == "__main__":
    main()
