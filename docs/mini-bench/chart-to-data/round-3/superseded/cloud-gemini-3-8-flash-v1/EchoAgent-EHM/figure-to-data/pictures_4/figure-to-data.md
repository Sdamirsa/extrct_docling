# Figure data: pictures_4 of EchoAgent-EHM (page 6)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 5. ROC curves for LVEF in the CAMUS dataset, derived from segmentation results of models with 'hands'.

**What the figure shows (model):** ROC curves for left ventricular ejection fraction (LVEF) classification in the CAMUS dataset across five segmentation models.

## Chart 1: OnimiaNet (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 87.97 |  |  | 87.97% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 65.74 |  |  | 65.74% | printed | 0.85 |
| EF≥50% |  | AUROC | 76.77 |  |  | 76.77% | printed | 0.85 |

## Chart 2: H2former (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 89.81 |  |  | 89.81% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 77.99 |  |  | 77.99% | printed | 0.85 |
| EF≥50% |  | AUROC | 76 |  |  | 76.00% | printed | 0.85 |

## Chart 3: EchoAgent (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 98.43 |  |  | 98.43% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 87.79 |  |  | 87.79% | printed | 0.85 |
| EF≥50% |  | AUROC | 93.88 |  |  | 93.88% | printed | 0.85 |

## Chart 4: MemSAM (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 91.56 |  |  | 91.56% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 56.28 |  |  | 56.28% | printed | 0.85 |
| EF≥50% |  | AUROC | 80.46 |  |  | 80.46% | printed | 0.85 |

## Chart 5: EchoONE (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 93.79 |  |  | 93.79% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 65.68 |  |  | 65.68% | printed | 0.85 |
| EF≥50% |  | AUROC | 85.56 |  |  | 85.56% | printed | 0.85 |

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-154006_cloud_google-gemini-3.8-flash.json`.
