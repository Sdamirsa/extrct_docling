# Figure data: pictures_5 of HeartAgent (page 12)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig.  7  |  Performance  of  human - AI  collaboration  for  cardiology  differential  diagnosis  and explanation. One hundred clinical notes from the MIMIC dataset were randomly selected. HeartAgent was built on Llama-3.3-70B, and the clinician team of two cardiologists provided consensus predictions.

**What the figure shows (model):** Four bar charts compare accuracy of HeartAgent, Expert, and Expert + HeartAgent on MIMIC for top-1 and top-3 diagnosis and explanation, with the combination highest in each.

## Chart 1: Top-1 Diagnosis Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.58 |  |  |  | agent | 0.8 |
| Expert |  |  | 0.69 |  |  |  | agent | 0.8 |
| Expert + HeartAgent |  |  | 0.84 |  |  |  | agent | 0.8 |

## Chart 2: Top-1 Explanation Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.48 |  |  |  | agent | 0.8 |
| Expert |  |  | 0.63 |  |  |  | agent | 0.8 |
| Expert + HeartAgent |  |  | 0.8 |  |  |  | agent | 0.8 |

## Chart 3: Top-3 Diagnosis Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.6 |  |  |  | agent | 0.8 |
| Expert |  |  | 0.65 |  |  |  | agent | 0.8 |
| Expert + HeartAgent |  |  | 0.73 |  |  |  | agent | 0.8 |

## Chart 4: Top-3 Explanation Performance on MIMIC (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0.2 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| HeartAgent |  |  | 0.535 |  |  |  | agent | 0.8 |
| Expert |  |  | 0.55 |  |  |  | agent | 0.8 |
| Expert + HeartAgent |  |  | 0.68 |  |  |  | agent | 0.8 |

## Not read, or uncertain

- Bar values are not printed on the figure. I read them from the axis, to about ±0.01. I enlarged chart 1 only; charts 2–4 were read from the overview image.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113729_agent_claude-sonnet-5-5.json`.
