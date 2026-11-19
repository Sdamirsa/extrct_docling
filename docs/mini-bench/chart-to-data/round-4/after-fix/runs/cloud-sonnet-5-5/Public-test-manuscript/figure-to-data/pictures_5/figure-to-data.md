# Figure data: pictures_5 of Public-test-manuscript (page 21)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6. Historical performance of GPT models on gastroenterology MCQ: (a) three ACG

**What the figure shows (model):** Two charts of GPT model accuracy on gastroenterology MCQs: (a) accuracy of GPT-3.5 Turbo 0125 and GPT-4 0613 on three ACG self-assessment versions (2021-2023); (b) accuracy of various GPT models by training data cutoff date.

## Chart a (line)

x axis "ACG Self-Assessment Version" linear 2021 to 2023; y axis "Accuracy (%)" [%] linear 40 to 80.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 2021 | GPT-3.5 Turbo 0125 | 71.59 |  |  | 71.59% | printed | 0.95 |
|  | 2022 | GPT-3.5 Turbo 0125 | 63.58 |  |  | 63.58% | printed | 0.95 |
|  | 2023 | GPT-3.5 Turbo 0125 | 70.35 |  |  | 70.35% | printed | 0.95 |
|  | 2021 | GPT-4 0613 | 44.57 |  |  | 44.57% | printed | 0.95 |
|  | 2022 | GPT-4 0613 | 46.3 |  |  | 46.30% | printed | 0.95 |
|  | 2023 | GPT-4 0613 | 53.49 |  |  | 53.49% | printed | 0.95 |

## Chart b (scatter)

x axis "Model Training Data Cutoff Date" categorical; y axis "Accuracy (%)" [%] linear 5 to 78.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 2021-09 |  | GPT3: babbage-002 (2021-09) | 9.26 |  |  | 9.26% | printed | 0.95 |
| 2021-09 |  | GPT3: davinci-002 (2021-09) | 12.35 |  |  | 12.35% | printed | 0.95 |
| 2021-09 |  | GPT3.5-Instruct (2021-09) | 39.51 |  |  | 39.51% | printed | 0.95 |
| 2021-09 |  | GPT3.5-0613 (2021-09) | 43.83 |  |  | 43.83% | printed | 0.95 |
| 2021-09 |  | GPT4-0613 (2021-09) | 63.58 |  |  | 63.58% | printed | 0.95 |
| 2023-12 |  | GPT3.5-0125 (2023-12) | 46.3 |  |  | 46.30% | printed | 0.95 |
| 2023-12 |  | GPT4-0125 (2023-12) | 62.35 |  |  | 62.35% | printed | 0.95 |
| 2023-04 |  | GPT3.5-1106 (2023-04) | 48.15 |  |  | 48.15% | printed | 0.95 |
| 2023-04 |  | GPT4-1106 (2023-04) | 65.43 |  |  | 65.43% | printed | 0.95 |
| 2023-09 |  | GPT4o-20240513 (2023-09) | 75.93 |  |  | 75.93% | printed | 0.95 |
| 2023-09 |  | GPT4omini-20240718 (2023-09) | 56 |  |  | 56.0% | printed | 0.95 |

- Note: Series assignment of the two 2021-09 orange points (39.51 vs 43.83) to GPT3.5-Instruct vs GPT3.5-0613 is inferred, since both share the same color and cutoff date.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-101352_cloud_anthropic-claude-sonnet-5.5.json`.
