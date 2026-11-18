# Judge prompt, round 3

Given to one fresh `claude-fable-5-2` sub-agent per run (general-purpose
agent, tools on, read-only on the repo). `<RUN>` is the run folder name
under `round-3/runs/`; machine paths are written relative to the repo root.

It is the round-2 prompt ([`../../round-2/judge/PROMPT.md`](../../round-2/judge/PROMPT.md))
with the same verdicts, error codes and severities, so the three rounds can
be compared. What differs: the paths point into `round-3/`, and the run's
files are the figure-to-data step's (one folder per figure with the reading
as markdown and JSON).

```text
You are the judge of a chart-to-data mini benchmark. For ONE run you compare what it extracted from 15 figures with the reference truth, and you classify HOW it was wrong, not only how much. Be strict and concrete: every error type you assign needs evidence (a value pair, a missing series, a wrong label).

Rules: read-only on the repository; write exactly one file, docs/mini-bench/chart-to-data/round-3/judge/<RUN>.json, and nothing else. Do not run models, Ollama, the GPU or the `claude` command. Use `CUDA_VISIBLE_DEVICES= uv run --no-sync python` from the repo root if you need Python (never `uv sync` or plain `uv run`; a hook rejects commands that contain ".venv" or ".env", so put any Python that reads the environment into a file). Do not read other runs' folders under round-3/runs/ or round-3/judge/inputs/, nor round-3/superseded/, round-3/README.md or round-3/LOG.md, nor other judges' output, nor anything of the earlier rounds (docs/mini-bench/chart-to-data/runs/, judge/, metrics/, round-2/, README.md): judge this run on its own.

Material, under docs/mini-bench/chart-to-data/:
- round-3/judge/inputs/<RUN>/<figure id>.md: one sheet per figure with the truth and the prediction side by side (panels, kinds, series, values) and the automatic scorer's numbers. Start from these.
- figures/<figure id>__<bundle>__pictures_<N>.png: the figure crop. Look at it (Read the PNG) whenever the sheet alone does not show why a value is wrong.
- truth/<bundle>__pictures_<N>.json: the full truth. truth/README.md says how it was made.
- round-3/runs/<RUN>/<bundle>/figure-to-data/pictures_<N>/: the run's output for one figure: figure-to-data.json (the record), figure-to-data.md (the same as a person sees it), result.json (how it was obtained: calls, seconds, and `issues`, what the step's own checks reported). round-3/runs/<RUN>/timing.json has one row per figure with its `status` and `notes`.
- testset.json: the 15 figures. A1-A5 are every chart candidate of one paper: only A3 holds data; A1, A2, A4, A5 are diagrams or ECG traces whose truth has no panels. B1-B5 and C1, C3, C4, C5 are data charts; C2 is a schematic without data.
The scorer matches a predicted value to a truth value of the same panel, series and category; a match is a hit when within 2 % / 5 % of the panel's axis range. A name mismatch ("Series 1" for "GPT-4o") makes correct numbers count as missing plus extra: say so when that is what happened, it is a different failure from a wrong number.

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

Write docs/mini-bench/chart-to-data/round-3/judge/<RUN>.json as:
{"model": "<RUN>", "judged_by": "claude-fable-5-2", "date": "<today>",
 "figures": [{"figure_id": "A1", "verdict": "...", "error_types": ["..."], "severity": 0, "usable": true, "evidence": "..."}, ... all 15 ...],
 "summary": {"verdict_counts": {...}, "error_type_counts": {...}, "usable_figures": N, "dominant_failure": "<one code>", "assessment": "<4-6 sentences: what this run does well, how it typically fails, what kind of figure it can be trusted on>"}}
Validate that the file is valid JSON with all 15 figures before you finish.

Report back in under 200 words: the verdict counts, the dominant failure, and the two most telling pieces of evidence.
```
