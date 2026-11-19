# Figure data: pictures_7 of AgentMD (page 6)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig. 4 | Individual-level evaluation results on the emergency department provider notes. a AgentMD is applied to emergency department provider notes from Yale Medicine with a toolkit of 16 commonly used calculators. For each calculator, the patients are then ranked by the overall risk, and the top 5 patients are

**What the figure shows (model):** This figure illustrates the workflow of AgentMD, showing how admission notes are processed into risk summaries and then evaluated by clinicians, alongside performance metrics.

## Chart a: a (bar, horizontal)

y axis categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Patient X | 855 | CURB-65 Score | * |  |  |  | vlm | 0.5 |
| Patient Y | 815 | CURB-65 Score | * |  |  |  | vlm | 0.5 |
| Patient Z | 795 | CURB-65 Score | * |  |  |  | vlm | 0.5 |
| Patient O | 785 | CURB-65 Score | * |  |  |  | vlm | 0.5 |

- Note: no axis calibrated from tick labels; values are the model's

## Chart b: b (stacked_bar, horizontal)

x axis linear 0 to 100; y axis categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Patient |  | #4da985 | 80.6 |  |  | 80.6% | printed | 0.95 |
| Patient |  | #f4cd4d | 8.7429 |  |  |  | vector | 0.9 |
| Patient |  | #cd615a | 10.6159 |  |  |  | vector | 0.9 |
| Process |  | #4da985 | 52.3 |  |  | 52.3% | printed | 0.95 |
| Process |  | #f4cd4d | 28.4378 |  |  |  | vector | 0.9 |
| Process |  | #cd615a | 19.2144 |  |  |  | vector | 0.9 |
| Result |  | #4da985 | 68.6 |  |  | 68.6% | printed | 0.95 |
| Result |  | #f4cd4d | 29.045 |  |  |  | vector | 0.9 |
| Result |  | #cd615a | 2.3238 |  |  |  | vector | 0.9 |
| 4 |  | #4ca883 | 22.6443 |  |  |  | vector | 0.9 |
| 4 |  | #f3cc4c | 22.6443 |  |  |  | vector | 0.9 |
| 4 |  | #cd6059 | 22.6443 |  |  |  | vector | 0.9 |

## Chart c: c (bar, horizontal)

x axis 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| PERC |  | Paitent Eligibility | 1 |  |  | 1.00 | printed | 0.95 |
| PERC |  | Process Correctness | 1 |  |  | 1.00 | printed | 0.95 |
| PERC |  | Result Usefulness | 1 |  |  | 1.00 | printed | 0.95 |
| PERC |  | Average | 1 |  |  | 1.00 | printed | 0.95 |
| SIRS Criteria |  | Paitent Eligibility | 1 |  |  | 1.00 | printed | 0.95 |
| SIRS Criteria |  | Process Correctness | 1 |  |  | 1.00 | printed | 0.95 |
| SIRS Criteria |  | Result Usefulness | 1 |  |  | 1.00 | printed | 0.95 |
| SIRS Criteria |  | Average | 1 |  |  | 1.00 | printed | 0.95 |
| GBS |  | Paitent Eligibility | 0.8 |  |  | 0.80 | printed | 0.95 |
| GBS |  | Process Correctness | 0.92 |  |  | 0.92 | printed | 0.95 |
| GBS |  | Result Usefulness | 0.92 |  |  | 0.92 | printed | 0.95 |
| GBS |  | Average | 0.88 |  |  | 0.88 | printed | 0.95 |
| qSOFA |  | Paitent Eligibility | 0.95 |  |  | 0.95 | printed | 0.95 |
| qSOFA |  | Process Correctness | 0.75 |  |  | 0.75 | printed | 0.95 |
| qSOFA |  | Result Usefulness | 0.88 |  |  | 0.88 | printed | 0.95 |
| qSOFA |  | Average | 0.86 |  |  | 0.86 | printed | 0.95 |
| CURB-65 Score |  | Paitent Eligibility | 0.9 |  |  | 0.90 | printed | 0.95 |
| CURB-65 Score |  | Process Correctness | 0.81 |  |  | 0.81 | printed | 0.95 |
| CURB-65 Score |  | Result Usefulness | 0.81 |  |  | 0.81 | printed | 0.95 |
| CURB-65 Score |  | Average | 0.84 |  |  | 0.84 | printed | 0.95 |
| GCS |  | Paitent Eligibility | 1 |  |  | 1.00 | printed | 0.95 |
| GCS |  | Process Correctness | 0.55 |  |  | 0.55 | printed | 0.95 |
| GCS |  | Result Usefulness | 0.92 |  |  | 0.92 | printed | 0.95 |
| GCS |  | Average | 0.82 |  |  | 0.82 | printed | 0.95 |
| Wells' DVT |  | Paitent Eligibility | 0.95 |  |  | 0.95 | printed | 0.95 |
| Wells' DVT |  | Process Correctness | 0.55 |  |  | 0.55 | printed | 0.95 |
| Wells' DVT |  | Result Usefulness | 0.83 |  |  | 0.83 | printed | 0.95 |
| Wells' DVT |  | Average | 0.78 |  |  | 0.78 | printed | 0.95 |
| Ottawa Ankle Rules |  | Paitent Eligibility | 0.7 |  |  | 0.70 | printed | 0.95 |
| Ottawa Ankle Rules |  | Process Correctness | 0.67 |  |  | 0.67 | printed | 0.95 |
| Ottawa Ankle Rules |  | Result Usefulness | 0.88 |  |  | 0.88 | printed | 0.95 |
| Ottawa Ankle Rules |  | Average | 0.75 |  |  | 0.75 | printed | 0.95 |
| CHADS2 Score |  | Paitent Eligibility | 0.6 |  |  | 0.60 | printed | 0.95 |
| CHADS2 Score |  | Process Correctness | 0.62 |  |  | 0.62 | printed | 0.95 |
| CHADS2 Score |  | Result Usefulness | 1 |  |  | 1.00 | printed | 0.95 |
| CHADS2 Score |  | Average | 0.74 |  |  | 0.74 | printed | 0.95 |
| Ottawa Knee Rules |  | Paitent Eligibility | 0.85 |  |  | 0.85 | printed | 0.95 |
| Ottawa Knee Rules |  | Process Correctness | 0.69 |  |  | 0.69 | printed | 0.95 |
| Ottawa Knee Rules |  | Result Usefulness | 0.67 |  |  | 0.67 | printed | 0.95 |
| Ottawa Knee Rules |  | Average | 0.73 |  |  | 0.73 | printed | 0.95 |
| CCHR |  | Paitent Eligibility | 0.8 |  |  | 0.80 | printed | 0.95 |
| CCHR |  | Process Correctness | 0.69 |  |  | 0.69 | printed | 0.95 |
| CCHR |  | Result Usefulness | 0.67 |  |  | 0.67 | printed | 0.95 |
| CCHR |  | Average | 0.72 |  |  | 0.72 | printed | 0.95 |
| Wells' PE |  | Paitent Eligibility | 0.95 |  |  | 0.95 | printed | 0.95 |
| Wells' PE |  | Process Correctness | 0.45 |  |  | 0.45 | printed | 0.95 |
| Wells' PE |  | Result Usefulness | 0.75 |  |  | 0.75 | printed | 0.95 |
| Wells' PE |  | Average | 0.72 |  |  | 0.72 | printed | 0.95 |
| PECARN Algorithm |  | Paitent Eligibility | 0.9 |  |  | 0.90 | printed | 0.95 |
| PECARN Algorithm |  | Process Correctness | 0.56 |  |  | 0.56 | printed | 0.95 |
| PECARN Algorithm |  | Result Usefulness | 0.5 |  |  | 0.50 | printed | 0.95 |
| PECARN Algorithm |  | Average | 0.65 |  |  | 0.65 | printed | 0.95 |
| Centor Criteria |  | Paitent Eligibility | 0.75 |  |  | 0.75 | printed | 0.95 |
| Centor Criteria |  | Process Correctness | 0.45 |  |  | 0.45 | printed | 0.95 |
| Centor Criteria |  | Result Usefulness | 0.62 |  |  | 0.62 | printed | 0.95 |
| Centor Criteria |  | Average | 0.61 |  |  | 0.61 | printed | 0.95 |
| HEART Score |  | Paitent Eligibility | 0.65 |  |  | 0.65 | printed | 0.95 |
| HEART Score |  | Process Correctness | 0.42 |  |  | 0.42 | printed | 0.95 |
| HEART Score |  | Result Usefulness | 0.5 |  |  | 0.50 | printed | 0.95 |
| HEART Score |  | Average | 0.52 |  |  | 0.52 | printed | 0.95 |
| CCR |  | Paitent Eligibility | 0.8 |  |  | 0.80 | printed | 0.95 |
| CCR |  | Process Correctness | 0.42 |  |  | 0.42 | printed | 0.95 |
| CCR |  | Result Usefulness | 0 |  |  | 0.00 | printed | 0.95 |
| CCR |  | Average | 0.41 |  |  | 0.41 | printed | 0.95 |

- Note: no axis calibrated from tick labels; values are the model's

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Checks

- the rule splitter finds 5 chart(s), the model lists 3: cut between the listed charts
- panel b: stacked segments do not sum to 100: 4 sums to 67.9329

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-180501_ollama_gemma4-26b-a4b-it-qat.json`.
