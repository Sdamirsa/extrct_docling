# Figure data: pictures_5 of HeartAgent (page 12)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig.  7  |  Performance  of  human - AI  collaboration  for  cardiology  differential  diagnosis  and explanation. One hundred clinical notes from the MIMIC dataset were randomly selected. HeartAgent was built on Llama-3.3-70B, and the clinician team of two cardiologists provided consensus predictions.

**What the figure shows (model):** This figure compares the performance of HeartAgent, an Expert, and their combination (Expert + HeartAgent) across four different metrics on the MIMIC dataset: Top-1 Diagnosis, Top-1 Explanation, Top-3 Diagnosis, and Top-3 Explanation.

## Chart 1: Top-1 Diagnosis Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.8.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.5818 |  |  |  | raster | 0.8 |
| Expert |  |  | 0.6909 |  |  |  | raster | 0.8 |
| Expert + HeartAgent |  |  | 0.8416* |  |  |  | raster | 0.55 |

## Chart 2: Top-1 Explanation Performance on MIMIC (bar, vertical)

x axis categorical; y axis linear 0.2 to 0.8.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.4805 |  |  |  | raster | 0.8 |
| Expert |  |  | 0.6286 |  |  |  | raster | 0.8 |
| Expert + HeartAgent |  |  | 0.7974 |  |  |  | raster | 0.8 |

## Chart 3: Top-3 Diagnosis Performance on MIMIC (bar, vertical)

x axis categorical; y axis linear 0.2 to 0.8.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.5974 |  |  |  | raster | 0.8 |
| Expert |  |  | 0.6519 |  |  |  | raster | 0.8 |
| Expert + HeartAgent |  |  | 0.7299 |  |  |  | raster | 0.8 |

## Chart 4: Top-3 Explanation Performance on MIMIC (bar, vertical)

x axis categorical; y axis linear 0.2 to 0.8.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.5351 |  |  |  | raster | 0.8 |
| Expert |  |  | 0.5506 |  |  |  | raster | 0.8 |
| Expert + HeartAgent |  |  | 0.6753 |  |  |  | raster | 0.8 |

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Checks

- 4 charts found by their tick labels
- panel 1: 0.8416 outside the axis range [0.2, 0.8] (Expert + HeartAgent/)

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113639_ollama_gemma4-26b-a4b-it-qat.json`.
