# Truth prompt, part B-others

Given to a fresh `claude-fable-5-2` sub-agent (general-purpose agent, tools on, no access to model outputs). Machine paths are replaced by `<repo>` and `<scratch>`; nothing else is changed.

```text
You are creating the reference truth ("frontier truth") for a chart-to-data mini benchmark: what numeric data each of five figures really shows. Several local vision models will be scored against your files, so accuracy and independence matter more than speed.

## Hard rules
- READ-ONLY on the repo <repo> and its samples: do not edit, create, move or delete anything there, no state-changing git commands. Another agent is working in it.
- Write ONLY under <scratch>/figdata/truth/ (exists; five Cardiologent truth files are already there: you may read `Cardiologent__pictures_3.json` as a worked example of the conventions, do not modify them) and, for scratch work, .../scratchpad/figdata/truth-work2/ (create it).
- Do NOT read anything under .../scratchpad/figdata/runs/ (model predictions land there), any `figure_data` folder inside a bundle, or anything under docs/mini-bench/. Do not use a figure's VLM description (in the bundle's HTML / figures.jsonl `vlm_caption`) as a source: it is model-written. The paper's own text and captions (document.json texts) are fine and useful as confirmation.
- Use `CUDA_VISIBLE_DEVICES= uv run --no-sync python ...` from the repo root for Python (never `uv sync` / plain `uv run`). A hook rejects any command containing the string ".venv". Stay off the GPU; do not call Ollama.

## The figures
Bundles are under <repo>/samples/aca-papers_out/<bundle>/ (document.json, figures.jsonl, images/picture_NNN.png crops at 1.5x). Source PDFs are in <repo>/samples/aca-papers/ (pypdfium2 is installed: extract the embedded bitmap of a raster figure at native resolution, or read vector drawing objects and the text layer when the figure is vector; render at scale 4-6 for anything you measure).
1. bundle `Dynamic-Specialist-MAS`, `#/pictures/1`, images/picture_002.png, PDF `Dynamic-Specialist-MAS.pdf` page 5 — grouped bar chart, 3 clinical problems x 4 outcome series, a count printed above each bar.
2. bundle `Med-RwR`, `#/pictures/6`, images/picture_007.png, PDF `Med-RwR.pdf` page 21 — three line-chart panels (Accuracy Reward, Format Reward, Completion Length) over training iterations: a smoothed line plus raw points.
3. bundle `EchoAgent-EHM`, `#/pictures/4`, images/picture_005.png, PDF `EchoAgent-EHM.pdf` page 6 — five ROC panels (one per model), three curves each, with the AUROC of each curve printed in the panel's legend.
4. bundle `Eunjung_Lee_ssrn-7427517_2`, `#/pictures/2`, images/picture_003.png, PDF `Eunjung Lee ssrn-7427517 (2).pdf` page 10 — horizontal forest plot, five rating domains, point and CI each, value on the x axis (-1.5..1.5). A grey diagonal watermark crosses the figure; it is not data.
5. bundle `RiskAgent_Synergizing_Language_Models_with_Validated_Tools_for`, `#/pictures/7`, images/picture_008.png, PDF of the same name page 15 — ten box-plot panels (two rows a/b x five categories), three models each.

## Truth format
Schema `extrct.figure-data/1`, the same as the model output. Read before writing:
- <repo>/docling/engines/figure_data/schema.py (ChartData, Panel, Axis, DataPoint, allowed `kind` and `source` literals: authoritative),
- <repo>/tools/figure-labeler/README.md and validate.py (labelling conventions, validator),
- the existing truth files in <repo>/tests/data/figure_data/truth/ for how multi-panel figures (F2-F4), printed labels (F1) and intervals are recorded,
- <repo>/docling/engines/figure_data/scoring.py and verify.py, to see how the scorer matches panels, series, categories and values and which axis it treats as the value axis for each `kind`. Choose `kind` and the placement of values so that a correct prediction scores as correct; where the natural kind would make the scorer normalise by the wrong axis, say so and choose the kind that scores correctly (the Cardiologent truth used `other` for a vertical interval plot for this reason).
One file per figure in the truth folder, named `<bundle>__pictures_<N>.json`, with `figure.bundle` = the bundle folder name exactly, `figure.self_ref`, `figure.image_path`, and page / bbox copied from that picture's prov in the bundle's document.json. `panels[].bbox_px` in the pixel frame of the bundle crop (images/picture_NNN.png). Validate every file with tools/figure-labeler/validate.py (read its source for the invocation) and with `docling.engines.figure_data.schema.ChartData.model_validate_json`.

## What to record, per figure
- Printed numbers are `source: "printed"`, `confidence: 1.0`, with `label_printed` exactly as printed. Measured values are `source: "raster"` (or `"vector"` when read from vector objects), with a confidence that reflects your measurement error.
- Calibrate each numeric axis from at least three tick labels; cross-check the calibration on something with a known value where one exists (a printed label, a gridline) and report the residual. State the estimated error of measured values in axis units.
- Series and category names exactly as printed (legend text, tick labels; line breaks as spaces).
- Figure 1: all 12 bars from the printed counts; also measure 3-4 bar tops to confirm the labels belong to the bars you think.
- Figure 2: for each panel, the smoothed line's value at each x tick position (and at the first and last point); if the raw points are individually resolvable, add them as a second series, otherwise say they were left out and why. Give the x axis ticks as printed.
- Figure 3: for each of the five panels and three curves, the printed AUROC as a printed value (category or series = the EF class label as printed, panel title = the model name). Do not trace the curves point by point unless the schema and scorer have a sensible place for it; say what you decided.
- Figure 4: centre and both CI bounds for each of the five domains (values on the x axis), measured; check the paper text on pages 10-11 for the stated mean differences and CIs and report agreement.
- Figure 5: for each of the ten panels and three models, the box statistics the schema can hold (median as `value`, and the box or whisker bounds in `err_lo` / `err_hi`: read schema.py and the README for the box-plot convention and state which bounds you used); note outlier points if the schema has a place for them. Each panel has its own y axis: calibrate each.
Do not guess: where a value cannot be read reliably, leave it out and list it under the truth file's `uncertain` field (the Cardiologent files show its use).

## Report (under 600 words)
Per figure: panels, series, number of values by source, calibration residuals, the convention choices you made (kind, interval bounds, what was left out), anything uncertain, and agreement with numbers stated in the paper text. List the files written.
```
