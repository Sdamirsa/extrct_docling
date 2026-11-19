# Figure data: pictures_5 of Public-test-manuscript (page 21)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6. Historical performance of GPT models on gastroenterology MCQ: (a) three ACG

**What the figure shows (model):** Historical performance of various GPT models on gastroenterology multiple-choice questions, shown across tests or timepoints (left) and grouped by model release wave or knowledge cutoff (right).

## Chart a1 (line, vertical)

x axis linear 1 to 3; y axis [%] linear 44.57 to 71.59.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 1 | GPT-3.5 Turbo 0125 | 71.59 |  |  | 71.59% | printed | 0.95 |
|  | 2 | GPT-3.5 Turbo 0125 | 63.58 |  |  | 63.58% | printed | 0.95 |
|  | 3 | GPT-3.5 Turbo 0125 | 70.3 |  |  | 70.3 | printed | 0.95 |
|  | 1 | GPT-4 0613 | 44.57 |  |  | 44.57% | printed | 0.95 |
|  | 2 | GPT-4 0613 | 46.3 |  |  | 46.30% | printed | 0.95 |
|  | 3 | GPT-4 0613 | 53.4 |  |  | 53.4 | printed | 0.95 |

- Note: Labels at x = 3 ('70.3' and '53.4') are partially clipped at the right margin.
- Note: The legend labels are printed as shown in the chart.

## Chart a2 (scatter, vertical)

x axis categorical 1 to 4; y axis [%] linear 9.26 to 63.58.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 1 | GPT4-0613 (2021-09) | 63.58 |  |  | 63.58% | printed | 0.95 |
|  | 1 | GPT3.5-Instruct (2021-09) | 43.83 |  |  | 43.83% | printed | 0.95 |
|  | 1 | GPT3.5-0613 (2021-09) | 39.51 |  |  | 39.51% | printed | 0.95 |
|  | 1 | GPT3: davinci-002 (2021-09) | 12.35 |  |  | 12.35% | printed | 0.95 |
|  | 1 | GPT3: babbage-002 (2021-09) | 9.26 |  |  | 9.26% | printed | 0.95 |
|  | 2 | GPT4-1106 (2023-04) | 62.35 |  |  | 62.35% | printed | 0.95 |
|  | 2 | GPT3.5-1106 (2023-04) | 46.3 |  |  | 46.30% | printed | 0.95 |
|  | 3 | GPT4-0125 (2023-12) | 65.43 |  |  | 65.43% | printed | 0.95 |
|  | 3 | GPT3.5-0125 (2023-12) | 48.15 |  |  | 48.15% | printed | 0.95 |
|  | 4 | GPT4o-20240513 (2023-09) | 75.93 |  |  | 75.93% | printed | 0.7 |
|  | 4 | GPT4omini-20240718 (2023-09) | 56 |  |  | 56.0% | printed | 0.95 |

- Note: The 4 columns correspond to model generations/cutoff dates: (2021-09) at x=1, (2023-04) at x=2, (2023-12) at x=3, and (2023-09) at x=4.

## Not read, or uncertain

- X-axis labels are not visible or were obscured by the black bottom border.

## Checks

- panel a2: 75.93 outside the axis range [9.26, 63.58] (4.0/GPT4o-20240513 (2023-09))

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-102407_cloud_google-gemini-3.8-flash.json`.
