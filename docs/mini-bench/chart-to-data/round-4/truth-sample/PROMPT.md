# Sample-truth prompt, round 4

Given to one fresh `claude-fable-5-2` sub-agent (general-purpose agent,
tools on) on 2026-11-19, while the pipeline runs of the round were under
way. `<scratch>` stands for its scratch folder.

The five supplementary figures `#/pictures/10` to `#/pictures/14` hold 3 to
13 panels of stacked bars with one bar per model: thousands of values, too
many for a full truth. This file asks for a sample fixed by rule, so that
the runs can be scored on something the figure prints.

```text
You are creating a SAMPLE of reference truth for round 4 of a chart-to-data mini benchmark: for five dense figures of one paper, the numbers printed in a fixed sample of bars. Four reading methods are scored against your files, so accuracy and independence matter more than speed.

## Hard rules
- READ-ONLY on the repository (your working directory is its root): do not edit, create, move or delete anything in it, and run no state-changing git command. Other processes are working in it. The ONE exception: you write your files into docs/mini-bench/chart-to-data/round-4/truth-sample/ (exists), one file per figure plus STRUCTURE.md, and nothing else there.
- Scratch work (scripts, renders, notes) goes under <scratch> (create it). A hook rejects shell commands whose text contains ".venv" or ".env": put Python into files under <scratch> (write them with the Write tool) and run them with `CUDA_VISIBLE_DEVICES= uv run --no-sync python <file>` from the repository root. Never `uv sync` or plain `uv run`. Stay off the GPU; do not call Ollama, the `claude` command or any model API.
- Do NOT read: anything under samples/ (the runs of this round are written there); any `figure-to-data` or `figure_data` folder; under docs/mini-bench/chart-to-data/ anything but truth/ (the earlier rounds' truth, as examples of the format) and round-4/truth-sample/ (no runs/, judge/, metrics/, round-2/, round-3/, round-4/runs, round-4/truth, README or LOG files of any round). Do not use a figure's VLM description (figures.jsonl `vlm_caption`, the annotations in document.json, the description in the bundle's markdown or HTML): it is model-written. The paper's own text, captions and tables are fine as a cross-check, never as the source of a value the figure does not show.

## The paper and the figures
PDF: showcase/Public-test-manuscript.pdf. Its committed conversion: showcase/default/Public-test-manuscript/ (document.json, figures.jsonl, images/picture_NNN.png: the figure crops at 1.5x). pypdfium2, Pillow and numpy are installed: extract the embedded image at native resolution where there is one, otherwise render the page at scale 5 to 6 and crop; enlarge further what you read.
- `#/pictures/10`, page 62, images/picture_011.png
- `#/pictures/11`, page 63, images/picture_012.png
- `#/pictures/12`, page 64, images/picture_013.png
- `#/pictures/13`, page 65, images/picture_014.png
- `#/pictures/14`, page 66, images/picture_015.png
Each is a grid of panels; a panel is a stacked bar chart with one vertical bar per model (the model names are the rotated tick labels under the bars), segment classes named in a legend (Correct, 2OP, EOP, NOP, Error, Incorrect), and the share of Correct printed in each bar.

## The sample (fixed, do not choose otherwise)
In each figure take TWO panels: the first and the last in reading order (rows top to bottom, within a row left to right). In each of the two, take the bars at positions 1, 8, 15, 22, 29 and 36 counted from the left (count every bar, also across the gaps between groups of bars). That is 12 bars per figure, 60 in all. For each sampled bar record ONE value: series "Correct", the share printed in the bar. If a sampled bar prints no number, measure the Correct segment against the y axis instead (source "raster") and say so.

## Format
Schema `extrct.figure-data/1` (docling/engines/figure_data/schema.py: ChartData, Panel, Value; read docs/mini-bench/chart-to-data/truth/AMIE-Mx__pictures_14.json as an example of stacked bars and docs/mini-bench/chart-to-data/truth/README.md for the conventions). Read docling/engines/figure_data/reading.py, the constant CONVENTIONS, and docling/engines/figure_data/scoring.py: key each value the way a correct reading would be keyed (category = the bar's tick label exactly as printed, series = "Correct"), and give each sampled panel its real box, since predictions are paired with truth panels by the overlap of their boxes.
One file per figure: docs/mini-bench/chart-to-data/round-4/truth-sample/Public-test-manuscript__pictures_<N>.json, with `figure.bundle` = "Public-test-manuscript", `figure.self_ref`, `figure.image_path`, page and bbox copied from that picture's prov in showcase/default/Public-test-manuscript/document.json; two panels, each with `id`, `title` (the panel's printed title), `kind` "stacked_bar", `orientation` "vertical", the y axis with its range, `bbox_px` = the panel's box (plot area with its tick labels and title) in the pixel frame of the bundle crop (images/picture_NNN.png), and the six sampled values (`source: "printed"`, `confidence: 1.0`, `label_printed` exactly as printed). `labeler` = {"kind": "agent", "name": "claude-fable-5-2", "date": "2026-11-19"}; `uncertain[0]` = "sample: 6 bars of 2 panels, the printed share of Correct only". Validate every file with `docling.engines.figure_data.schema.ChartData.model_validate_json`.

Also write docs/mini-bench/chart-to-data/round-4/truth-sample/STRUCTURE.md: per figure, the number of panels, each panel's printed title in reading order, the number of bars per panel, the segment classes of the legend, and whether every bar prints its Correct share. This says how many values each figure holds.

Read every sampled number twice from an enlarged crop (at least 6x), and check each against the bar's height on the y axis (the printed share must agree with the top of the Correct segment within about 1 %). Do not guess: a label you cannot read reliably is left out and listed under `uncertain`.

## Report (under 300 words)
Per figure: panels, bars per panel, the two sampled panels and the 12 values; anything unreadable; how the tick labels of the sampled bars were read. List the files written.
```
