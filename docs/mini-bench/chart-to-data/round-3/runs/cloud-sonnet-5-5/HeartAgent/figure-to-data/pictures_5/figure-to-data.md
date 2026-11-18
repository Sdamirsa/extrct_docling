# Figure data: pictures_5 of HeartAgent (page 12)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig.  7  |  Performance  of  human - AI  collaboration  for  cardiology  differential  diagnosis  and explanation. One hundred clinical notes from the MIMIC dataset were randomly selected. HeartAgent was built on Llama-3.3-70B, and the clinician team of two cardiologists provided consensus predictions.

**What the figure shows (model):** Four bar charts of accuracy on MIMIC for HeartAgent, Expert, and Expert + HeartAgent, for top-1 and top-3 diagnosis and explanation.

## Chart 1: Top-1 Diagnosis Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.58 |  |  |  | vlm | 0.8 |
| Expert |  |  | 0.69 |  |  |  | vlm | 0.8 |
| Expert + HeartAgent |  |  | 0.84 |  |  |  | vlm | 0.8 |

## Chart 2: Top-1 Explanation Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.48 |  |  |  | vlm | 0.8 |
| Expert |  |  | 0.63 |  |  |  | vlm | 0.8 |
| Expert + HeartAgent |  |  | 0.8 |  |  |  | vlm | 0.8 |

## Chart 3: Top-3 Diagnosis Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.6 |  |  |  | vlm | 0.8 |
| Expert |  |  | 0.65 |  |  |  | vlm | 0.8 |
| Expert + HeartAgent |  |  | 0.73 |  |  |  | vlm | 0.8 |

## Chart 4: Top-3 Explanation Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.535 |  |  |  | vlm | 0.8 |
| Expert |  |  | 0.55 |  |  |  | vlm | 0.8 |
| Expert + HeartAgent |  |  | 0.675 |  |  |  | vlm | 0.8 |

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153255_cloud_anthropic-claude-sonnet-5.5.json`.
