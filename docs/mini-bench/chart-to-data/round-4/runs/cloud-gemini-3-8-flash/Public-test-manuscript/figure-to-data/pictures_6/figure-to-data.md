# Figure data: pictures_6 of Public-test-manuscript (page 22)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure  7.  The  impacts  of  temperature,  prompt  design,  and  random  seeds  on  GPT-3.5 consistency are important.

**What the figure shows (model):** Line charts showing the impact of model temperature on GPT-3.5 consistency (Accuracy %) across raw vs best prompts, before and after determining the random seed.

## Chart 1: Raw Prompt - Without Determining Seed (line, vertical)

x axis "Model Tempreature" categorical; y axis "Accuracy %" [%] linear 25 to 91.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 0 |  | Average | 72.9 | 71.3 | 74.5 |  | vlm | 0.8 |
| 0.1 |  | Average | 75.6 | 73.9 | 77.3 |  | vlm | 0.8 |
| 0.2 |  | Average | 77.4 | 66.3 | 85.6 |  | vlm | 0.8 |
| 0.4 |  | Average | 74.8 | 73 | 77.8 |  | vlm | 0.8 |
| 0.6 |  | Average | 70.6 | 67.8 | 70.6 |  | vlm | 0.8 |
| 0.8 |  | Average | 74.8 | 67.8 | 82.6 |  | vlm | 0.8 |
| 0.9 |  | Average | 74.8 | 67.8 | 77 |  | vlm | 0.8 |
| 1 |  | Average | 80 | 73.6 | 80 |  | vlm | 0.8 |
| 1.2 |  | Average | 78.2 | 71.3 | 86.3 |  | vlm | 0.8 |
| 1.4 |  | Average | 79.1 | 68.7 | 86.3 |  | vlm | 0.8 |
| 1.6 |  | Average | 72.7 | 66.7 | 77 |  | vlm | 0.8 |
| 1.8 |  | Average | 72.7 | 65.8 | 85.6 |  | vlm | 0.8 |
| 2 |  | Average | 47.7 | 40.9 | 52.9 |  | vlm | 0.8 |

- Note: Red ring highlights the maximum average accuracy at temperature 1.
- Note: Yellow rings highlight baseline temperature 0 and local minimum at temperature 0.6.

## Chart 2: Best Prompt - Without Determining Seed (line, vertical)

x axis "Model Tempreature" categorical; y axis "Accuracy %" [%] linear 25 to 91.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 0 |  | Average | 75.6 | 75 | 77.5 |  | vlm | 0.8 |
| 0.1 |  | Average | 76.4 | 74.5 | 80.2 |  | vlm | 0.8 |
| 0.2 |  | Average | 73.9 | 68.5 | 77.5 |  | vlm | 0.8 |
| 0.4 |  | Average | 75.6 | 71 | 80.2 |  | vlm | 0.8 |
| 0.6 |  | Average | 70.4 | 66 | 77.5 |  | vlm | 0.8 |
| 0.8 |  | Average | 78.2 | 71 | 90.5 |  | vlm | 0.8 |
| 0.9 |  | Average | 74.5 | 63 | 80 |  | vlm | 0.8 |
| 1 |  | Average | 79.1 | 74.5 | 83 |  | vlm | 0.8 |
| 1.2 |  | Average | 75.6 | 66 | 80.2 |  | vlm | 0.8 |
| 1.4 |  | Average | 72.7 | 68.5 | 74.5 |  | vlm | 0.8 |
| 1.6 |  | Average | 58.6 | 52.5 | 65 |  | vlm | 0.8 |
| 1.8 |  | Average | 48.7 | 43.5 | 53.5 |  | vlm | 0.8 |
| 2 |  | Average | 35.8 | 24.5 | 43.5 |  | vlm | 0.8 |

- Note: Red ring highlights the maximum average accuracy at temperature 1.
- Note: Yellow ring highlights baseline temperature 0.

## Chart 3: Raw Prompt - After Determining Seed (line, vertical)

x axis "Model Tempreature" categorical; y axis "Accuracy %" [%] linear 25 to 91.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 0 |  | Average | 83.3 | 80 | 88.5 |  | vlm | 0.8 |
| 0.1 |  | Average | 76.7 | 73 | 79 |  | vlm | 0.8 |
| 0.2 |  | Average | 70 | 68 | 74 |  | vlm | 0.8 |
| 0.4 |  | Average | 77.4 | 71 | 83 |  | vlm | 0.8 |
| 0.6 |  | Average | 73.7 | 71 | 76 |  | vlm | 0.8 |
| 0.8 |  | Average | 81.1 | 77 | 85.5 |  | vlm | 0.8 |
| 0.9 |  | Average | 79.2 | 77 | 82 |  | vlm | 0.8 |
| 1 |  | Average | 75.6 | 73 | 78 |  | vlm | 0.8 |
| 1.2 |  | Average | 69.3 | 65.5 | 71 |  | vlm | 0.8 |
| 1.4 |  | Average | 71.3 | 71 | 71.3 |  | vlm | 0.8 |
| 1.6 |  | Average | 76.7 | 65.5 | 83 |  | vlm | 0.8 |
| 1.8 |  | Average | 74.8 | 65.5 | 80 |  | vlm | 0.8 |
| 2 |  | Average | 50 | 41 | 59 |  | vlm | 0.8 |

- Note: Red ring highlights the maximum average accuracy at temperature 0.
- Note: Yellow ring highlights local minimum at temperature 1.4.

## Chart 4: Best Prompt - After Determining Seed (line, vertical)

x axis "Model Tempreature" categorical; y axis "Accuracy %" [%] linear 25 to 91.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| 0 |  | Average | 77.5 | 74.5 | 80.2 |  | vlm | 0.8 |
| 0.1 |  | Average | 75.7 | 72 | 80.2 |  | vlm | 0.8 |
| 0.2 |  | Average | 77.5 | 74.5 | 80.2 |  | vlm | 0.8 |
| 0.4 |  | Average | 73.9 | 65.5 | 77.5 |  | vlm | 0.8 |
| 0.6 |  | Average | 68.5 | 65.5 | 72 |  | vlm | 0.8 |
| 0.8 |  | Average | 75 | 65.5 | 83 |  | vlm | 0.8 |
| 0.9 |  | Average | 81.1 | 77.5 | 83 |  | vlm | 0.8 |
| 1 |  | Average | 83.7 | 80 | 85.5 |  | vlm | 0.8 |
| 1.2 |  | Average | 81.9 | 74.5 | 91 |  | vlm | 0.8 |
| 1.4 |  | Average | 84.6 | 83 | 88.5 |  | vlm | 0.8 |
| 1.6 |  | Average | 75 | 68.5 | 80 |  | vlm | 0.8 |
| 1.8 |  | Average | 72.1 | 65.5 | 77.5 |  | vlm | 0.8 |
| 2 |  | Average | 65.1 | 63 | 66 |  | vlm | 0.8 |

- Note: Red ring highlights the maximum average accuracy at temperature 1.4.
- Note: Yellow ring highlights minimum average accuracy at temperature 2.

## Not read, or uncertain

- The 'Range (Min to Max)' shaded regions are captured as err_lo and err_hi for each 'Average' data point rather than as separate series.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-102407_cloud_google-gemini-3.8-flash.json`.
