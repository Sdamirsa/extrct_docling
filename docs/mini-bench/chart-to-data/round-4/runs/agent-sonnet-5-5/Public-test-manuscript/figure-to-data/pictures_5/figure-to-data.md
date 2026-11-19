# Figure data: pictures_5 of Public-test-manuscript (page 21)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6. Historical performance of GPT models on gastroenterology MCQ: (a) three ACG

**What the figure shows (model):** Two panels of GPT model accuracy (%) on gastroenterology MCQs: (left) GPT-3.5 Turbo 0125 and GPT-4 0613 across three tests, (right) a scatter of 11 GPT model versions by release period.

## Chart a1 (line, vertical)

y axis [%] linear 44.57 to 71.59.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 1 | GPT-3.5 Turbo 0125 | 71.59 |  |  | 71.59% | printed | 0.95 |
|  | 2 | GPT-3.5 Turbo 0125 | 63.58 |  |  | 63.58% | printed | 0.95 |
|  | 3 | GPT-3.5 Turbo 0125 | 70.3 |  |  | 70.3 | printed | 0.95 |
|  | 1 | GPT-4 0613 | 44.57 |  |  | 44.57% | printed | 0.95 |
|  | 2 | GPT-4 0613 | 46.3 |  |  | 46.30% | printed | 0.95 |
|  | 3 | GPT-4 0613 | 53.4 |  |  | 53.4 | printed | 0.95 |

- Note: No axis labels or tick labels printed; x = 1,2,3 are the three unlabeled tests. Third-point labels are cut off by the panel edge (70.3.., 53.4..); values estimated from pixel positions.

## Chart a2: Historical performance of GPT models by model version (scatter, vertical)

x axis categorical; y axis [%] linear 9.26 to 63.58.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 1 | GPT3: babbage-002 (2021-09) | 9.26 |  |  | 9.26% | printed | 0.95 |
|  | 1 | GPT3: davinci-002 (2021-09) | 12.35 |  |  | 12.35% | printed | 0.95 |
|  | 1 | GPT3.5-Instruct (2021-09) | 39.51 |  |  | 39.51% | printed | 0.95 |
|  | 1 | GPT3.5-0613 (2021-09) | 43.83 |  |  | 43.83% | printed | 0.95 |
|  | 1 | GPT4-0613 (2021-09) | 63.58 |  |  | 63.58% | printed | 0.95 |
|  | 2 | GPT3.5-1106 (2023-04) | 46.3 |  |  | 46.30% | printed | 0.95 |
|  | 2 | GPT4-1106 (2023-04) | 62.35 |  |  | 62.35% | printed | 0.95 |
|  | 3 | GPT3.5-0125 (2023-12) | 48.15 |  |  | 48.15% | printed | 0.95 |
|  | 3 | GPT4-0125 (2023-12) | 65.43 |  |  | 65.43% | printed | 0.95 |
|  | 4 | GPT4o-20240513 (2023-09) | 75.93 |  |  | 75.93% | printed | 0.7 |
|  | 4 | GPT4omini-20240718 (2023-09) | 56 |  |  | 56.0% | printed | 0.95 |

- Note: Axes unlabeled; x = column position 1-4 (2021-09, 2023-04, 2023-12, latest). Markers of the same colour share a family; assignment of values to specific models within a family (esp. GPT3.5-Instruct vs GPT3.5-0613, babbage vs davinci, 4o vs 4omini) inferred from legend order and colour, not directly printed.

## Not read, or uncertain

- Axis titles and tick labels are not printed in either chart, so x positions are only ordinal and the test names for the left chart's three points are unknown.
- The last point of each line in chart a1 has its label cut off (70.3.., 53.4..), so those two values are estimates from pixel position.
- In chart a2, the assignment of values to individual models within a colour family is inferred from legend order, not printed. The least certain are GPT3.5-Instruct vs GPT3.5-0613, babbage vs davinci, and 4o vs 4omini.
- The caption is truncated ("three ACG..."), so the exact test sets are unknown.

## Checks

- panel a2: 75.93 outside the axis range [9.26, 63.58] (4.0/GPT4o-20240513 (2023-09))

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-091835_agent_claude-sonnet-5-5.json`.
