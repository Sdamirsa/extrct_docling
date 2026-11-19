# Judge prompt, round 4

Given to one fresh `claude-fable-5-2` sub-agent per run (general-purpose
agent, tools on, read-only on the repo). `<RUN>` is the run folder name
under `round-4/runs/`; machine paths are written relative to the repo root.

It is the round-3 prompt ([`../../round-3/judge/PROMPT.md`](../../round-3/judge/PROMPT.md))
with the same verdicts, error codes and severities, so the rounds can be
compared. What differs: the figures are the six of the showcase paper that
have a truth file (`../testset.json`, `../truth/`), the paths point into
`round-4/`, and the scorer's pairing of panels is spelled out, because a
chart split in two by the step is the first thing this paper shows.

```text
You are the judge of a chart-to-data mini benchmark. For ONE run you compare what it extracted from 6 figures of one paper with the reference truth, and you classify HOW it was wrong, not only how much. Be strict and concrete: every error type you assign needs evidence (a value pair, a missing series, a wrong label).

Rules: read-only on the repository; write exactly one file, docs/mini-bench/chart-to-data/round-4/judge/<RUN>.json, and nothing else. Do not run models, Ollama, the GPU or the `claude` command. Use `CUDA_VISIBLE_DEVICES= uv run --no-sync python` from the repo root if you need Python (never `uv sync` or plain `uv run`; a hook rejects commands that contain ".venv" or ".env", so put any Python that reads the environment into a file). Do not read other runs' folders under round-4/runs/ or round-4/judge/inputs/, nor round-4/README.md, round-4/LOG.md or round-4/metrics/, nor other judges' output, nor anything under samples/, nor anything of the earlier rounds (docs/mini-bench/chart-to-data/runs/, judge/, metrics/, round-2/, round-3/, README.md): judge this run on its own.

Material, under docs/mini-bench/chart-to-data/:
- round-4/judge/inputs/<RUN>/<figure id>.md: one sheet per figure with the truth and the prediction side by side (panels, kinds, series, values) and the automatic scorer's numbers. Start from these.
- figures/<figure id>__<bundle>__pictures_<N>.png: the figure as every reader of this round was given it (captured from the PDF at a higher resolution than the bundle crop that `bbox_px` values refer to). Look at it (Read the PNG; enlarge a part with Pillow when marks are small) whenever the sheet alone does not show why a value is wrong.
- round-4/truth/<bundle>__pictures_<N>.json: the full truth. round-4/truth/README.md says how it was made and which conventions it follows.
- round-4/runs/<RUN>/<bundle>/figure-to-data/pictures_<N>/: the run's output for one figure: figure-to-data.json (the record), figure-to-data.md (the same as a person sees it), result.json (how it was obtained: calls, seconds, and `issues`, what the step's own checks reported). round-4/runs/<RUN>/timing.json has one row per figure with its `status` and `notes`.
- round-4/testset.json: the 12 chart candidates of the paper. You judge the six that have a truth file: S02, S03, S04, S05, S06, S08, all data charts. S09-S14 are dense supplementary figures without a full truth: leave them out.
The scorer pairs a predicted panel with the truth panel whose box it overlaps by more than half, and matches a predicted value to a truth value of the same panel, series and category; a match is a hit when within 2 % / 5 % of the panel's axis range. A chart the run split into two panels (or two it merged) therefore leaves values unpaired that may be right: look at the record before you call them missing, and name the cause (PANEL_STRUCTURE). A name mismatch ("Series 1" for "GPT-4o") makes correct numbers count as missing plus extra: say so when that is what happened, it is a different failure from a wrong number.

Known defect of this round, not the run's fault: the image of S05 that every reader was given has a black background where the page is white, which hides the axis tick labels and titles of both charts (the truth, made from the PDF, is keyed by them: years on the x axis of the first chart, cut-off dates on that of the second). Judge S05 on the values and the series names a reader could see, and say in the evidence that the categories could not be read; do not count that as the run's error.

A run may return no panels for a figure on purpose, with the reason in the record's `uncertain` list ("not a data chart: ...", or "not read: ..."). For a figure without data that is the right answer (true_negative). For a data chart it is "missed" with the code NO_OUTPUT; quote the reason in the evidence, and count it as severity 2 (data missing, nothing misleading), not 3. A run may also say in `uncertain` what part of a chart it left unread: missing values it declares are still MISSING_VALUES, but note in the evidence that they were declared.

For every figure assign:
- verdict: "correct" (every truth value returned within 5 % of the axis range, nothing invented), "partial" (some values right, some missing or wrong), "wrong" (returned data but little or none of it usable), "missed" (a data chart for which no data came back), "true_negative" (no-data figure, nothing returned), "false_positive" (no-data figure, values returned).
- error_types: zero or more of these codes, most damaging first:
  - HALLUCINATED_ON_NON_CHART: values returned for a diagram, schematic or signal trace.
  - NO_OUTPUT: nothing returned for a data chart (empty panels, run cut off, parse failure, declined by the reader).
  - PANEL_STRUCTURE: panels missed, merged, split wrongly or mislocated.
  - WRONG_KIND: chart kind wrong in a way that changes how values are read (ignore harmless synonyms).
  - SERIES_NAMES: series or legend entries missing, invented, renamed or swapped.
  - CATEGORY_LABELS: category / tick labels missing, invented, truncated or misassigned.
  - MISSING_VALUES: part of the data not returned (which part).
  - INVENTED_VALUES: values returned that the figure does not show.
  - PRINTED_LABEL_MISREAD: a number printed in the figure was ignored or misread.
  - GEOMETRY_MISMEASURED: values read from mark positions are off; say whether the error is a constant offset, a scale factor, or scatter.
  - AXIS_CALIBRATION: the axis range, scale (linear/log) or orientation is wrong, shifting every value.
  - INTERVAL_BOUNDS: error bars, CI bounds or box statistics wrong, missing or confused with the centre.
  - VALUE_ASSIGNMENT: right numbers attached to the wrong series or category.
  - UNIT_OR_FORMAT: percent vs fraction, thousands separators, sign.
  - OTHER: anything else, described.
- severity: 0 none, 1 cosmetic (a consumer would still extract the right numbers), 2 some numbers wrong or missing, 3 the extraction would mislead.
- usable: true when a downstream extraction pipeline could take this figure's numbers as they are.
- evidence: one or two sentences with the concrete values or names (truth vs predicted).

Write docs/mini-bench/chart-to-data/round-4/judge/<RUN>.json as:
{"model": "<RUN>", "judged_by": "claude-fable-5-2", "date": "<today>",
 "figures": [{"figure_id": "S02", "verdict": "...", "error_types": ["..."], "severity": 0, "usable": true, "evidence": "..."}, ... all 6 ...],
 "summary": {"verdict_counts": {...}, "error_type_counts": {...}, "usable_figures": N, "dominant_failure": "<one code>", "assessment": "<4-6 sentences: what this run does well, how it typically fails, what kind of figure it can be trusted on>"}}
Validate that the file is valid JSON with all 6 figures before you finish.

Report back in under 200 words: the verdict counts, the dominant failure, and the two most telling pieces of evidence.
```
