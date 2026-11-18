# Figure data: pictures_4 of EchoAgent-EHM (page 6)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 5. ROC curves for LVEF in the CAMUS dataset, derived from segmentation results of models with 'hands'.

**What the figure shows (model):** ROC curves for three LVEF classes (EF<40%, 40%≤EF<50%, EF≥50%) on CAMUS for five segmentation models (OnimiaNet, H2former, EchoAgent, MemSAM, EchoONE), with AUROC printed in each legend.

## Chart 1: OnimiaNet (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 87.97 |  |  | 87.97% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 65.74 |  |  | 65.74% | printed | 0.85 |
| EF≥50% |  | AUROC | 76.77 |  |  | 76.77% | printed | 0.85 |

- Note: ROC curves; only printed AUROC recorded, curves not traced.

## Chart 2: H2former (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 89.81 |  |  | 89.81% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 77.99 |  |  | 77.99% | printed | 0.85 |
| EF≥50% |  | AUROC | 76 |  |  | 76.00% | printed | 0.85 |

- Note: ROC curves; only printed AUROC recorded, curves not traced.

## Chart 3: EchoAgent (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 98.43 |  |  | 98.43% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 87.79 |  |  | 87.79% | printed | 0.85 |
| EF≥50% |  | AUROC | 93.88 |  |  | 93.88% | printed | 0.85 |

- Note: ROC curves; only printed AUROC recorded, curves not traced.

## Chart 4: MemSAM (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 91.56 |  |  | 91.56% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 56.28 |  |  | 56.28% | printed | 0.85 |
| EF≥50% |  | AUROC | 80.46 |  |  | 80.46% | printed | 0.85 |

- Note: ROC curves; only printed AUROC recorded, curves not traced.

## Chart 5: EchoONE (line)

x axis "1 - Specificity" linear 0 to 1; y axis "Sensitivity" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| EF<40% |  | AUROC | 93.79 |  |  | 93.79% | printed | 0.85 |
| 40%≤EF<50% |  | AUROC | 65.68 |  |  | 65.68% | printed | 0.85 |
| EF≥50% |  | AUROC | 85.56 |  |  | 85.56% | printed | 0.85 |

- Note: ROC curves; only printed AUROC recorded, curves not traced.

## Not read, or uncertain

- The ROC curve shapes (sensitivity vs 1 - specificity) in all 5 panels were not traced point by point. Only the printed AUROC per curve was recorded, 15 values in total. The curves are dense step lines with no markers.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113655_agent_claude-sonnet-5-5.json`.
