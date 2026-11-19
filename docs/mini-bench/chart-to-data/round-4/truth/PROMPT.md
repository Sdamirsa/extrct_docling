# Truth prompt, round 4

Given to three fresh `claude-fable-5-2` sub-agents (general-purpose agent,
tools on), one per part, on 2026-11-19, while the four pipeline runs of the
round were under way. Each was told its part and a scratch folder and to
follow the text below. `<scratch>` stands for that folder.

Parts:

- **A**: `#/pictures/2` (Figure 3) and `#/pictures/5` (Figure 6).
- **B**: `#/pictures/3` (Figure 4).
- **C**: `#/pictures/4` (Figure 5), `#/pictures/6` (Figure 7) and
  `#/pictures/8` (the confusion matrix of the answer extraction).

```text
You are creating the reference truth for round 4 of a chart-to-data mini benchmark: what numeric data each of your figures really shows. Four reading methods (a local model, two cloud models, an agent) are scored against your files, so accuracy and independence matter more than speed.

## Hard rules
- READ-ONLY on the repository (your working directory is its root): do not edit, create, move or delete anything in it, and run no state-changing git command. Other processes are working in it. The ONE exception: you write your truth files into docs/mini-bench/chart-to-data/round-4/truth/ (exists), one file per figure, and nothing else there.
- Scratch work (scripts, renders, notes) goes under <scratch> (create it). A hook rejects shell commands whose text contains ".venv" or ".env": put Python into files under <scratch> (write them with the Write tool) and run them with `CUDA_VISIBLE_DEVICES= uv run --no-sync python <file>` from the repository root. Never `uv sync` or plain `uv run`. Stay off the GPU; do not call Ollama, the `claude` command or any model API.
- Do NOT read: anything under samples/ (the runs of this round are written there); any `figure-to-data` or `figure_data` folder; under docs/mini-bench/chart-to-data/ anything but the two truth folders named below (no runs/, judge/, metrics/, round-2/, round-3/, round-4/runs, README or LOG files of any round). Do not use a figure's VLM description (figures.jsonl `vlm_caption`, the annotations in document.json, the description in the bundle's markdown or HTML): it is model-written. The paper's own text, captions and tables (document.json texts and tables, the PDF's text layer) are fine as a cross-check, never as the source of a value the figure does not show.

## The paper and the figures
PDF: showcase/Public-test-manuscript.pdf (68 pages). Its committed conversion: showcase/default/Public-test-manuscript/ (document.json, figures.jsonl, images/picture_NNN.png: the figure crops at 1.5x). Every figure of your part is an embedded bitmap or a page region without vector marks you can rely on: measure on the bitmap. pypdfium2, Pillow and numpy are installed: extract the embedded image at native resolution where there is one, otherwise render the page at scale 4 to 6 and crop.

The six figures of the round (yours are the ones of your part):
- `#/pictures/2`, page 16, images/picture_003.png: Figure 3, four panels (a-d): horizontal bars and interval plots (a dot with a horizontal error bar per row).
- `#/pictures/3`, page 18, images/picture_004.png: Figure 4, one horizontal stacked bar per model (segments Correct, 2OP, EOP, NOP, Error, Incorrect; the share of Correct is printed in each bar).
- `#/pictures/4`, page 20, images/picture_005.png: Figure 5, horizontal stacked bars per model and image setting, same segment classes.
- `#/pictures/5`, page 21, images/picture_006.png: Figure 6, two panels of points with printed percentages (lines in the first).
- `#/pictures/6`, page 22, images/picture_007.png: Figure 7, four line panels (a-d), each an average line with a shaded minimum-to-maximum range over model temperature.
- `#/pictures/8`, page 58, images/picture_009.png: a confusion matrix with a printed count in every cell.
Look at each of yours first, and read its caption and the text around it in the PDF. If one turns out to hold no data values, write a file with `"panels": []` and say what it is in `uncertain[0]`.

## Format and conventions
Schema `extrct.figure-data/1`, the same record the methods write. Read before writing:
- docling/engines/figure_data/schema.py (ChartData, Panel, Axis, Value; the allowed `kind` and `source` literals are authoritative);
- docling/engines/figure_data/reading.py, the constant CONVENTIONS: how the readers are told to turn a mark into a point (what goes in category, series, x, value, err_lo, err_hi for each kind of chart). Key your truth the same way, so that a correct reading matches it;
- docling/engines/figure_data/scoring.py: how a prediction is matched to the truth (panels, series, categories, values) and which axis a `kind` is normalised by. Choose `kind` and value placement so that a correct prediction scores as correct, and say so when the natural kind would not;
- docs/mini-bench/chart-to-data/truth/README.md and the files beside it (the truth of the earlier rounds; `AMIE-Mx__pictures_14.json` for stacked bars, `Eunjung_Lee_ssrn-7427517_2__pictures_2.json` and `Cardiologent__pictures_3.json` for intervals, `Med-RwR__pictures_6.json` for lines, `tests/data/figure_data/truth/` for a heatmap if there is one) as worked examples of the conventions;
- tools/figure-labeler/validate.py (read its source for the invocation).
One file per figure: docs/mini-bench/chart-to-data/round-4/truth/Public-test-manuscript__pictures_<N>.json, with `figure.bundle` = "Public-test-manuscript", `figure.self_ref`, `figure.image_path`, and page and bbox copied from that picture's prov in showcase/default/Public-test-manuscript/document.json; `panels[].bbox_px` in the pixel frame of the bundle crop (images/picture_NNN.png); `labeler` = {"kind": "agent", "name": "claude-fable-5-2", "date": "2026-11-19"}. Validate every file with tools/figure-labeler/validate.py and with `docling.engines.figure_data.schema.ChartData.model_validate_json`.
- Printed numbers: `source: "printed"`, `confidence: 1.0`, `label_printed` exactly as printed. Values measured on the bitmap: `source: "raster"`, with a confidence that reflects your measurement error.
- Calibrate each numeric axis on at least three tick labels; cross-check on something with a known value (a printed label, a gridline, a total that must be 100 %) and report the residual and the estimated error of the measured values in axis units.
- Series and category names exactly as printed (legend text, tick labels; a line break is a space).
- Stacked bars: one category per bar, one value per segment class that the legend names (a class with no visible segment in a bar is 0), measured from the segment boundaries and checked against the bar's total; the printed share replaces the measured one where it is printed.
- Intervals: the centre in `value`, the ends in `err_lo` / `err_hi` as absolute axis values.
- A line with a shaded range: the line's value in `value`, the range's lower and upper edge at that x in `err_lo` / `err_hi`.
- A matrix: one value per cell, row and column labels placed as the schema, CONVENTIONS and the scorer expect (state the choice).
- Do not guess: leave out what cannot be read reliably and list it under `uncertain`.

## Report (under 500 words)
Per figure: data chart or not; panels, series, number of values by source; calibration residuals; the convention choices you made (kind, how a point is keyed, interval and range bounds, what was left out); anything uncertain; agreement with numbers the paper states in its text or tables. List the files written.
```
