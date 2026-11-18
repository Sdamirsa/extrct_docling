# Figure data: pictures_7 of RiskAgent_Synergizing_Language_Models_with_Validated_Tools_for (page 15)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6. Performance for RiskAgent-8B, GPT-4o, and o3-mini. In the boxplot, the central line indicates the median value, while the lower and upper boundaries represent the 25th (Q1) and 75th (Q3) percentiles, respectively. The whiskers extend up to 1.5 times the interquartile range (IQR). We can see that RiskAgent-8B not only consistently achieves the best results across all cases in different runs but also achieves lower perturbations (STD) than o3-mini in most cases, especially in risk prediction for cardiac.

**What the figure shows (model):** Ten box plots comparing RiskAgent-8B, GPT-4o and o3-mini across five risk categories (Stroke/TIA, Shortness of Breath, Internal Medicine, Cardiac, Overall) on MedRisk-Qualitative (a) and MedRisk-Quantitative (b) benchmarks.

## Chart 1: a. MedRisk-Qualitative - Stroke/TIA (box, vertical)

x axis categorical; y axis "Stroke/TIA" linear 53 to 80.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 73.3 | 71.2 | 76.8 |  | vlm | 0.8 |
| GPT-4o |  |  | 57.8 | 57.8 | 59.8 |  | vlm | 0.8 |
| o3-mini |  |  | 57.1 | 57 | 57.7 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈73.3, Q3≈76.1
- Note: GPT-4o: Q1≈57.7, Q3≈59.1; outlier ≈54.9
- Note: o3-mini: Q1≈57.0, Q3≈57.7; outlier ≈63.4; median not clearly distinguishable

## Chart 2: a. MedRisk-Qualitative - Shortness of Breath (box, vertical)

x axis categorical; y axis "Shortness of Breath" linear 49 to 83.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 77.2 | 75.3 | 78.2 |  | vlm | 0.8 |
| GPT-4o |  |  | 52.3 | 51.2 | 53.7 |  | vlm | 0.8 |
| o3-mini |  |  | 53.4 | 52.8 | 53.7 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈75.9, Q3≈77.5
- Note: GPT-4o: Q1≈51.5, Q3≈53.1
- Note: o3-mini: Q1≈53.1, Q3≈53.7; outlier ≈55.0

## Chart 3: a. MedRisk-Qualitative - Internal Medicine (box, vertical)

x axis categorical; y axis "Internal Medicine" linear 49 to 83.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 78.2 | 77.8 | 78.6 |  | vlm | 0.8 |
| GPT-4o |  |  | 50 | 49.9 | 50.1 |  | vlm | 0.8 |
| o3-mini |  |  | 52 | 51.3 | 53 |  | vlm | 0.8 |

- Note: RiskAgent-8B: outliers ≈79.3 and ≈77.0
- Note: GPT-4o: very narrow box; outlier ≈50.3
- Note: o3-mini: Q1≈51.7, Q3≈52.5

## Chart 4: a. MedRisk-Qualitative - Cardiac (box, vertical)

x axis categorical; y axis "Cardiac" linear 50 to 75.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 70.8 | 70.7 | 72.6 |  | vlm | 0.8 |
| GPT-4o |  |  | 53.6 | 52.1 | 54.4 |  | vlm | 0.8 |
| o3-mini |  |  | 52.1 | 51.7 | 54.4 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈70.7, Q3≈71.8
- Note: GPT-4o: Q1≈52.1, Q3≈54.0
- Note: o3-mini: Q1≈51.7, Q3≈52.9

## Chart 5: a. MedRisk-Qualitative - Overall (box, vertical)

x axis categorical; y axis "Overall" linear 49 to 83.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 78.3 | 78 | 78.9 |  | vlm | 0.8 |
| GPT-4o |  |  | 50.6 | 50.5 | 50.7 |  | vlm | 0.8 |
| o3-mini |  |  | 52.6 | 51.7 | 53.2 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈78.1, Q3≈78.8
- Note: GPT-4o: very narrow; outlier ≈51.0
- Note: o3-mini: Q1≈52.1, Q3≈53.0

## Chart 6: b. MedRisk-Quantitative - Stroke/TIA (box, vertical)

x axis categorical; y axis "Stroke/TIA" linear 20 to 83.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 77.8 | 77.3 | 78.5 |  | vlm | 0.8 |
| GPT-4o |  |  | 30.2 | 28 | 32.3 |  | vlm | 0.8 |
| o3-mini |  |  | 54.3 | 47.8 | 55 |  | vlm | 0.8 |

- Note: RiskAgent-8B: outliers ≈80.4 and ≈75.4
- Note: GPT-4o: Q1≈28.8, Q3≈32.3; outlier ≈38.7
- Note: o3-mini: Q1≈47.8, Q3≈55.0

## Chart 7: b. MedRisk-Quantitative - Shortness of Breath (box, vertical)

x axis categorical; y axis "Shortness of Breath" linear 30 to 80.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 75.9 | 75.8 | 76 |  | vlm | 0.8 |
| GPT-4o |  |  | 35 | 34.4 | 36.6 |  | vlm | 0.8 |
| o3-mini |  |  | 59 | 57.8 | 60.4 |  | vlm | 0.8 |

- Note: RiskAgent-8B: collapsed box; outliers ≈76.5 and ≈75.5
- Note: GPT-4o: Q1≈34.8, Q3≈36.3
- Note: o3-mini: Q1≈58.5, Q3≈60.1

## Chart 8: b. MedRisk-Quantitative - Internal Medicine (box, vertical)

x axis categorical; y axis "Internal Medicine" linear 35 to 82.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 75.2 | 74.8 | 77.1 |  | vlm | 0.8 |
| GPT-4o |  |  | 39.4 | 39.2 | 39.6 |  | vlm | 0.8 |
| o3-mini |  |  | 55 | 54.5 | 56.8 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈74.9, Q3≈75.9
- Note: GPT-4o: narrow; outliers ≈40.2 and ≈38.7
- Note: o3-mini: Q1≈54.7, Q3≈56.5

## Chart 9: b. MedRisk-Quantitative - Cardiac (box, vertical)

x axis categorical; y axis "Cardiac" linear 35 to 75.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 70.6 | 69.1 | 71.8 |  | vlm | 0.8 |
| GPT-4o |  |  | 38.1 | 37.7 | 42.8 |  | vlm | 0.8 |
| o3-mini |  |  | 60.2 | 56.7 | 67.5 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈69.9, Q3≈71.1
- Note: GPT-4o: Q1≈37.8, Q3≈40.8
- Note: o3-mini: Q1≈57.1, Q3≈66.8

## Chart 10: b. MedRisk-Quantitative - Overall (box, vertical)

x axis categorical; y axis "Overall" linear 33 to 82.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| RiskAgent-8B |  |  | 76.4 | 75.4 | 77.3 |  | vlm | 0.8 |
| GPT-4o |  |  | 38.2 | 38.2 | 38.2 |  | vlm | 0.8 |
| o3-mini |  |  | 55.8 | 54.6 | 57.2 |  | vlm | 0.8 |

- Note: RiskAgent-8B: Q1≈75.9, Q3≈77.0
- Note: GPT-4o: collapsed box; outliers ≈39.8 and ≈37.3
- Note: o3-mini: Q1≈55.2, Q3≈56.8

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153402_cloud_anthropic-claude-sonnet-5.5.json`.
