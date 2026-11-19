# Figure data: pictures_8 of AgentMD (page 7)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig. 5 | Applying AgentMD onthe MIMIC-III cohort.a AgentMDisappliedto9822 admission notesinMIMIC. b AgentMDcalculation results are aggregated by the risk calculators, and patients are ranked within each tool. c The distribution of the numberofselectedcalculatorsforeachpatient. d Thedistributionof the numberof

**What the figure shows (model):** AgentMD applied to MIMIC-III admission notes: workflow diagrams (a, b), density plots of calculators per patient (c) and patients per calculator (d), density distributions of LLM-rated calculator scores (specificity, urgency, severity, absence) for two example calculators (e), and ROC curves comparing AgentMD with GPT-4 for four calculators (f).

## Chart c: Calculators per patient (line)

x axis "# Calculators / Patient" categorical 0 to 20; y axis "Density" categorical 0 to 0.14.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 0 | Density | 0.05 |  |  |  | vlm | 0.8 |
|  | 3 | Density | 0.137 |  |  |  | vlm | 0.8 |
|  | 5 | Density | 0.12 |  |  |  | vlm | 0.8 |
|  | 10 | Density | 0.04 |  |  |  | vlm | 0.8 |
|  | 15 | Density | 0.004 |  |  |  | vlm | 0.8 |
|  | 20 | Density | 0 |  |  |  | vlm | 0.8 |

- Note: KDE curve; peak about 0.137 near x=3; values at ticks approximate

## Chart d: Patients per calculator (line)

x axis "# Patients / Calculator" categorical 0 to 400; y axis "Density" categorical 0 to 0.012.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 0 | Density | 0.0113 |  |  |  | vlm | 0.8 |
|  | 10 | Density | 0.0121 |  |  |  | vlm | 0.8 |
|  | 100 | Density | 0.0018 |  |  |  | vlm | 0.8 |
|  | 200 | Density | 0.0004 |  |  |  | vlm | 0.8 |
|  | 300 | Density | 0.0003 |  |  |  | vlm | 0.8 |
|  | 400 | Density | 0 |  |  |  | vlm | 0.8 |

- Note: KDE curve; approximate

## Chart e1: Specificity - Short-term Mortality of AE CHF (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.05.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 28 | Density | 0.055* |  |  |  | vlm | 0.55 |

- Note: KDE with main peak ~0.055 at ~28, secondary peaks at ~21 (0.022), ~39 (0.024), ~50 (0.018)

## Chart e2: Urgency - Short-term Mortality of AE CHF (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.12.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 90 | Density | 0.128* |  |  |  | vlm | 0.55 |

- Note: Single peak near 90

## Chart e3: Severity - Short-term Mortality of AE CHF (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.04.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 50 | Density | 0.02 |  |  |  | vlm | 0.8 |
|  | 82 | Density | 0.046* |  |  |  | vlm | 0.55 |

- Note: Two peaks

## Chart e4: Absence - Short-term Mortality of AE CHF (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.02.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 10 | Density | 0.0115 |  |  |  | vlm | 0.8 |
|  | 92 | Density | 0.026* |  |  |  | vlm | 0.55 |

- Note: Two peaks

## Chart e5: Specificity - 4-year Mortality Score (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.04.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 32 | Density | 0.042 |  |  |  | vlm | 0.8 |
|  | 87 | Density | 0.008 |  |  |  | vlm | 0.8 |

- Note: Two peaks

## Chart e6: Urgency - 4-year Mortality Score (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.3.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 20 | Density | 0.31 |  |  |  | vlm | 0.8 |

- Note: Sharp peak at 20; minor bumps at 30 and 50

## Chart e7: Severity - 4-year Mortality Score (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.03.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 13 | Density | 0.0095 |  |  |  | vlm | 0.8 |
|  | 49 | Density | 0.033* |  |  |  | vlm | 0.55 |
|  | 67 | Density | 0.017 |  |  |  | vlm | 0.8 |

- Note: Three peaks

## Chart e8: Absence - 4-year Mortality Score (line)

x axis linear 0 to 100; y axis "Density" linear 0 to 0.2.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
|  | 90 | Density | 0.205 |  |  |  | vlm | 0.8 |

- Note: Single sharp peak near 90

## Chart f1: High-risk Varices Calculator (line)

x axis "False Positive Rate" linear 0 to 1; y axis "True Positive Rate" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| AgentMD |  | AUC | 0.86 |  |  | 0.86 | printed | 0.95 |
| GPT-4 |  | AUC | 0.62 |  |  | 0.62 | printed | 0.95 |

- Note: ROC curves not traced; AUC from legend

## Chart f2: Functional Morbidity Index (line)

x axis "False Positive Rate" linear 0 to 1; y axis "True Positive Rate" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| AgentMD |  | AUC | 0.77 |  |  | 0.77 | printed | 0.95 |
| GPT-4 |  | AUC | 0.58 |  |  | 0.58 | printed | 0.95 |

- Note: ROC curves not traced; AUC from legend

## Chart f3: NSTEMI Risk Calculator (line)

x axis "False Positive Rate" linear 0 to 1; y axis "True Positive Rate" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| AgentMD |  | AUC | 0.97 |  |  | 0.97 | printed | 0.95 |
| GPT-4 |  | AUC | 0.79 |  |  | 0.79 | printed | 0.95 |

- Note: ROC curves not traced; AUC from legend

## Chart f4: IFD Risk Score (line)

x axis "False Positive Rate" linear 0 to 1; y axis "True Positive Rate" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| AgentMD |  | AUC | 0.79 |  |  | 0.79 | printed | 0.95 |
| GPT-4 |  | AUC | 0.61 |  |  | 0.61 | printed | 0.95 |

- Note: ROC curves not traced; AUC from legend

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Not read, or uncertain

- Panels a and b are workflow diagrams with no data.
- KDE density curves in c, d and e are only sampled at peaks and a few ticks, not fully traced.
- ROC curve shapes in f not traced; only legend AUCs recorded.

## Checks

- the rule splitter finds 11 chart(s), the model lists 14: cut between the listed charts
- panel e1: 0.055 outside the axis range [0, 0.05] (28.0/Density)
- panel e2: 0.128 outside the axis range [0, 0.12] (90.0/Density)
- panel e3: 0.046 outside the axis range [0, 0.04] (82.0/Density)
- panel e4: 0.026 outside the axis range [0, 0.02] (92.0/Density)
- panel e7: 0.033 outside the axis range [0, 0.03] (49.0/Density)

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-180500_cloud_anthropic-claude-sonnet-5.5.json`.
