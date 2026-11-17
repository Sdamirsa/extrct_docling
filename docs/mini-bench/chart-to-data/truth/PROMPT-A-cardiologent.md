# Truth prompt, part A-cardiologent

Given to a fresh `claude-fable-5-2` sub-agent (general-purpose agent, tools on, no access to model outputs). Machine paths are replaced by `<repo>` and `<scratch>`; nothing else is changed.

```text
You are creating the reference truth ("frontier truth") for a figure-to-data comparison: what numeric data each of five figures of one paper really shows. Local models will be scored against your files, so accuracy and independence matter more than speed.

## Hard rules
- READ-ONLY on the repo <repo> and its samples: do not edit, create, move or delete anything there, no state-changing git commands. Another agent is working in it.
- Write ONLY under <scratch>/figdata/truth/ (create it) and, for your scratch work, .../scratchpad/figdata/truth-work/.
- Do NOT read anything under .../scratchpad/figdata/runs/ (model predictions land there) or any `figure_data` folder inside a bundle: the truth must be independent of the models. Do not read the VLM description of a figure in the bundle's HTML/figures.jsonl as a source of numbers either (it is model-written).
- Use `CUDA_VISIBLE_DEVICES= uv run --no-sync python ...` from the repo root for Python (never `uv sync` / plain `uv run`). A hook rejects any command containing the string ".venv". Stay off the GPU and do not call Ollama.

## The figures
Bundle: <repo>/samples/aca-papers_out/Cardiologent (document.json, figures.jsonl, images/picture_NNN.png crops at 1.5x, images/page_NNNN.png). Source PDF: <repo>/samples/aca-papers/Cardiologent.pdf (pypdfium2 is installed: render a page region at high resolution, e.g. scale 4-6, and read vector drawing objects / the text layer when the figure is vector).
The five figures to label, by self_ref and crop:
- #/pictures/0 images/picture_001.png (page 1, "Figure 1: Deployment scenario")
- #/pictures/2 images/picture_003.png (page 4, "Figure 3: Cardiologent ...")
- #/pictures/3 images/picture_004.png (page 7, "Figure 4: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) ...")
- #/pictures/4 images/picture_005.png (page 13, "Stage 1: Time series encoder")
- #/pictures/5 images/picture_006.png (page 18, "Figure 6: Grounding on ECG window ...")
Look at each (Read the PNG; render from the PDF at higher resolution for anything you measure). Decide for each whether it is a data chart (numeric values plotted against axes or printed as data) or not (schematic, pipeline diagram, waveform illustration). A figure that carries no extractable numeric data series gets a truth file with `"panels": []` and a one-line `"notes"` saying what it is. I expect most of these five are not data charts; do not force data out of a diagram. ECG/PPG waveform traces are signals, not chart data: record them as no-data unless the figure prints numeric values as data points (e.g. a bar or score per model).

## Truth format
Schema `extrct.figure-data/1`, the same as the model output. Read these before writing:
- <repo>/tests/data/figure_data/truth/F5.json (a small complete example) and F1.json's first ~80 lines (printed vs measured values, confidence),
- <repo>/docling/engines/figure_data/schema.py (ChartData, Panel, Axis, DataPoint: the authoritative field list; `source` is one of the allowed literals there, e.g. printed / vector / measured),
- <repo>/tools/figure-labeler/README.md (labelling conventions) and validate.py.
One file per figure: `Cardiologent__pictures_<N>.json` in the truth folder, with `figure.bundle = "Cardiologent"`, `figure.self_ref`, `figure.image_path`, page and bbox copied from the bundle's document.json prov of that picture. The scorer matches truth to prediction by (bundle name, self_ref), panels by overlap/order, series and categories by name, and values numerically, so:
- use the category and series names exactly as printed in the figure (keep line breaks as spaces);
- for a point with an interval (e.g. a CI), put the centre in `value` and the bounds in `err_lo` / `err_hi` as ABSOLUTE axis values if that is what the schema/example convention says (check schema.py's docstrings and F1-F4 for the convention; state which you used);
- a number printed in the figure is `source: "printed"`, `confidence: 1.0`, with `label_printed`; a value you measure from geometry is `source: "measured"` (or "vector" when read from vector objects) with a confidence reflecting your measurement error, and say in `notes` how you measured it (axis calibration from tick positions, pixel/vector coordinates) and the estimated error in axis units;
- fill `axes` (name, scale, min/max ticks) as the figure prints them.
Validate every file: `CUDA_VISIBLE_DEVICES= uv run --no-sync python tools/figure-labeler/validate.py <file>` (read its --help / source for the exact invocation; if it needs a pack folder rather than a bare file, validate by loading the JSON with `docling.engines.figure_data.schema.ChartData.model_validate_json` instead and say so).

## Measuring
For Figure 4 (pictures/3): the bounds of each interval are printed next to the caps; the centre markers are not labelled. Calibrate the y axis from at least three tick labels (pixel or vector coordinates of the tick marks), measure each centre marker's position at high resolution (or from the vector path if the figure is vector in the PDF), convert, and cross-check the calibration by measuring the printed cap values: report the residual. Also check the paper's text (document.json texts on pages 6-8) for the ICC point estimates: if the text states them, use them as `printed`-grade confirmation and say where (quote the sentence), but keep `source` honest about where the value in the figure comes from.

## Report
For each figure: data chart or not, why; for data charts: panels, series, categories, every value with source and confidence, calibration residual, and any value you are unsure of. List the files written. State anything you could not determine. Keep the report under 500 words.
```
