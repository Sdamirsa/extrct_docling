# Truth prompt, part C-more

Given to a fresh `claude-fable-5-2` sub-agent (general-purpose agent, tools on, no access to model outputs). Machine paths are replaced by `<repo>` and `<scratch>`; nothing else is changed.

```text
You are creating the reference truth ("frontier truth") for a chart-to-data mini benchmark: what numeric data each of five figures really shows. Several local vision models will be scored against your files, so accuracy and independence matter more than speed.

## Hard rules
- READ-ONLY on the repo <repo> and its samples: do not edit, create, move or delete anything there, no state-changing git commands. Other agents are working in it.
- Write ONLY under <scratch>/figdata/truth/ (exists; other agents' truth files are there: you may read `Cardiologent__pictures_3.json` as a worked example of the conventions; do not modify or overwrite any existing file) and, for scratch work, .../scratchpad/figdata/truth-work3/ (create it).
- Do NOT read anything under .../scratchpad/figdata/runs/ (model predictions), any `figure_data` folder inside a bundle, or anything under docs/mini-bench/. Do not use a figure's VLM description (the bundle's HTML / figures.jsonl `vlm_caption`) as a source: it is model-written. The paper's own text and captions (document.json texts) are fine as confirmation.
- Use `CUDA_VISIBLE_DEVICES= uv run --no-sync python ...` from the repo root for Python (never `uv sync` / plain `uv run`). A hook rejects any command containing the string ".venv". Stay off the GPU; do not call Ollama.

## The figures
Bundles: <repo>/samples/aca-papers_out/<bundle>/ (document.json, figures.jsonl, images/picture_NNN.png crops at 1.5x). PDFs: <repo>/samples/aca-papers/<bundle>.pdf. pypdfium2 is installed: extract a raster figure's embedded bitmap at native resolution, or read vector drawing objects and the text layer when the figure is vector; render at scale 4-6 for anything you measure.
1. bundle `HeartAgent`, `#/pictures/5`, images/picture_006.png, page 12 — "Fig. 7 | Performance of human-AI collaboration for cardiology differential diagnosis ..." (classified bar chart).
2. bundle `AgentMD`, `#/pictures/4`, images/picture_005.png, page 5 — classified heatmap (no caption attached; find its caption/panel letter in the page text).
3. bundle `AMIE-Mx`, `#/pictures/14`, images/picture_015.png, page 21 — "Extended Data Fig. 7 | Patient actor ratings ..." (classified bar chart; probably stacked rating distributions).
4. bundle `Zodiac`, `#/pictures/5`, images/picture_006.png, page 10 — "Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC ..." (bar panels).
5. bundle `AMIE-Cardiology`, `#/pictures/3`, images/picture_004.png, page 4 — "Extended Data Fig. 2. The pie charts display the proportions of chosen responses ..." (vector pies with printed percentages). An earlier truth file for this same figure exists at <repo>/tests/data/figure_data/truth/F5.json (made on 2026-11-09 from an older conversion). Do your own reading first; then compare with F5.json, report every difference, and write the file you stand behind (update `figure` to this bundle's document.json prov and crop frame).
Look at each first. If one of them turns out not to be a data chart (a schematic, a screenshot), write a truth file with `"panels": []` and say what it is in `uncertain[0]`, as the Cardiologent no-data files do; do not force data out of it.

## Truth format and conventions
Schema `extrct.figure-data/1`, the same as the model output. Read before writing:
- <repo>/docling/engines/figure_data/schema.py (ChartData, Panel, Axis, DataPoint; allowed `kind` and `source` literals: authoritative),
- <repo>/tools/figure-labeler/README.md and validate.py,
- the truth files in <repo>/tests/data/figure_data/truth/ for multi-panel figures (F2-F4), printed labels and stacked bars (F1), intervals,
- <repo>/docling/engines/figure_data/scoring.py and verify.py: how the scorer matches panels, series, categories and values and which axis it treats as the value axis for each `kind`. Choose `kind` and value placement so that a correct prediction scores as correct; where the natural kind would make the scorer normalise by the wrong axis, say so and pick the kind that scores correctly.
One file per figure, named `<bundle>__pictures_<N>.json`, with `figure.bundle` = the bundle folder name exactly, `figure.self_ref`, `figure.image_path`, page and bbox copied from that picture's prov in the bundle's document.json; `panels[].bbox_px` in the pixel frame of the bundle crop. Validate every file with tools/figure-labeler/validate.py (read its source for the invocation) and with `docling.engines.figure_data.schema.ChartData.model_validate_json`.
- Printed numbers: `source: "printed"`, `confidence: 1.0`, `label_printed` exactly as printed. Values read from vector geometry: `"vector"`. Values measured on the bitmap: `"raster"`, with a confidence reflecting your measurement error.
- Calibrate each numeric axis from at least three tick labels; cross-check on something with a known value (a printed label, a gridline, a total that must be 100 %) and report the residual and the estimated error of measured values in axis units.
- Series and category names exactly as printed (legend text, tick labels; line breaks as spaces). For a heatmap / confusion matrix, one value per cell with row and column labels placed the way the schema and the existing truth files do it (state the choice).
- For stacked bars, every segment (each series' share), measured from the segment boundaries, checked against the bar's total.
- Do not guess: leave out what cannot be read reliably and list it under `uncertain`.

## Report (under 600 words)
Per figure: data chart or not; panels, series, number of values by source; calibration residuals; convention choices (kind, cell placement, interval bounds, what was left out); anything uncertain; agreement with numbers in the paper text; for figure 5 the differences from F5.json. List the files written.
```
