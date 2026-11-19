# Figure data: pictures_5 of Public-test-manuscript (page 21)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6. Historical performance of GPT models on gastroenterology MCQ: (a) three ACG

**What the figure shows (model):** Two panels of GPT model accuracy (%) on gastroenterology multiple-choice questions: (a1) line chart of GPT-3.5 Turbo 0125 and GPT-4 0613 across three test sets; (a2) scatter of many GPT models in four x columns.

## Chart a1 (line)

x axis categorical; y axis "Accuracy" [%] linear 44.57 to 71.59.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 1 |  | GPT-3.5 Turbo 0125 | 71.59 |  |  | 71.59% | printed | 0.95 |
| 2 |  | GPT-3.5 Turbo 0125 | 63.58 |  |  | 63.58% | printed | 0.95 |
| 3 |  | GPT-3.5 Turbo 0125 | 70.3 |  |  | 70.3 | printed | 0.95 |
| 1 |  | GPT-4 0613 | 44.57 |  |  | 44.57% | printed | 0.95 |
| 2 |  | GPT-4 0613 | 46.3 |  |  | 46.30% | printed | 0.95 |
| 3 |  | GPT-4 0613 | 53.4 |  |  | 53.4 | printed | 0.95 |

- Note: X tick labels not visible; categories numbered in order. Last labels are cut off at the crop edge (70.3x, 53.4x).

## Chart a2 (scatter)

x axis categorical; y axis "Accuracy" [%] linear 9.26 to 63.58.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 1 |  | GPT3: babbage-002 (2021-09) | 9.26 |  |  | 9.26% | printed | 0.95 |
| 1 |  | GPT3: davinci-002 (2021-09) | 12.35 |  |  | 12.35% | printed | 0.95 |
| 1 |  | GPT3.5-Instruct (2021-09) | 39.51 |  |  | 39.51% | printed | 0.95 |
| 1 |  | GPT3.5-0613 (2021-09) | 43.83 |  |  | 43.83% | printed | 0.95 |
| 1 |  | GPT4-0613 (2021-09) | 63.58 |  |  | 63.58% | printed | 0.95 |
| 2 |  | GPT3.5-1106 (2023-04) | 46.3 |  |  | 46.30% | printed | 0.95 |
| 2 |  | GPT4-1106 (2023-04) | 62.35 |  |  | 62.35% | printed | 0.95 |
| 3 |  | GPT3.5-0125 (2023-12) | 48.15 |  |  | 48.15% | printed | 0.95 |
| 3 |  | GPT4-0125 (2023-12) | 65.43 |  |  | 65.43% | printed | 0.95 |
| 4 |  | GPT4o-20240513 (2023-09) | 75.93 |  |  | 75.93% | printed | 0.95 |
| 4 |  | GPT4omini-20240718 (2023-09) | 56 |  |  | 56.0% | printed | 0.95 |

- Note: X tick labels not visible; four columns numbered 1-4. Series assignment of the two orange points in column 1 (39.51, 43.83) is inferred from the legend order and may be swapped.

## Not read, or uncertain

- Axis tick labels and x-axis labels are not visible in either chart

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-085957_cloud_anthropic-claude-sonnet-5.5.json`.
