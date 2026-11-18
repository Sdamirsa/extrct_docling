# Figure data: pictures_1 of Dynamic-Specialist-MAS (page 5)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 2: Distribution of note-level prediction outcomes, grouped by clinical problem and by which methods were correct.

**What the figure shows (model):** Grouped bar chart of note-level prediction outcome counts (MAS vs baseline correct/incorrect) for three clinical problems.

## Chart 1 (grouped_bar, vertical)

x axis "Clinical Problem" categorical; y axis "Number of Cases" [cases] linear 0 to 350.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Congestive Heart Failure |  | MAS Correct, Baseline Incorrect (MAS ○, Base ✕) | 13 |  |  | 13 | printed | 0.95 |
| Congestive Heart Failure |  | MAS Incorrect, Baseline Correct (MAS ✕, Base ○) | 6 |  |  | 6 | printed | 0.95 |
| Congestive Heart Failure |  | Both Correct (○) | 299 |  |  | 299 | printed | 0.95 |
| Congestive Heart Failure |  | Both Incorrect (✕) | 102 |  |  | 102 | printed | 0.95 |
| Acute Kidney Injury |  | MAS Correct, Baseline Incorrect (MAS ○, Base ✕) | 25 |  |  | 25 | printed | 0.95 |
| Acute Kidney Injury |  | MAS Incorrect, Baseline Correct (MAS ✕, Base ○) | 25 |  |  | 25 | printed | 0.95 |
| Acute Kidney Injury |  | Both Correct (○) | 255 |  |  | 255 | printed | 0.95 |
| Acute Kidney Injury |  | Both Incorrect (✕) | 115 |  |  | 115 | printed | 0.95 |
| Sepsis |  | MAS Correct, Baseline Incorrect (MAS ○, Base ✕) | 25 |  |  | 25 | printed | 0.95 |
| Sepsis |  | MAS Incorrect, Baseline Correct (MAS ✕, Base ○) | 26 |  |  | 26 | printed | 0.95 |
| Sepsis |  | Both Correct (○) | 283 |  |  | 283 | printed | 0.95 |
| Sepsis |  | Both Incorrect (✕) | 86 |  |  | 86 | printed | 0.95 |

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153235_cloud_anthropic-claude-sonnet-5.5.json`.
