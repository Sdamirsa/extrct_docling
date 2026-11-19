# Figure data: pictures_5 of AgentMD (page 5)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig. 3 | Evaluations of AgentMD on RiskQA. a ExampleofaquestioninRiskQAand howAgentMDanswersit. b TheperformanceofGPT-3.5-based AgentMDcompared to Chain-of-Thought (CoT) prompting on RiskQA. c The performance of GPT-4based AgentMD compared to CoT prompting on RiskQA. d The accuracy of tool

**What the figure shows (model):** This figure presents a comparison of accuracy on the RiskQA dataset and tool selection accuracy across different models and methods, including Random, CoT, and AgentMD using GPT-3.5 and GPT-4.

## Chart 1: b c (grouped_bar, vertical)

x axis categorical; y axis linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Random |  | #d7d7d7 | 0.2 |  |  | 0.200 | printed | 0.95 |
| AgentMD |  | #d7d7d7 | 0.321 |  |  | 0.321 | printed | 0.95 |
| AgentMD |  | #e19693 | 0.546 |  |  | 0.546 | printed | 0.95 |

## Chart 2: d (grouped_bar, vertical)

x axis categorical; y axis linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Random |  | #d7d7d7 | 0.2 |  |  | 0.200 | printed | 0.95 |
| AgentMD |  | #d7d7d7 | 0.409 |  |  | 0.409 | printed | 0.95 |
| AgentMD |  | #e19693 | 0.877 |  |  | 0.877 | printed | 0.95 |

## Chart 3: of Accuracy AgentMD Tool Selection (grouped_bar, vertical)

x axis categorical; y axis linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| AgentMD |  | #d7d7d7 | 0.723 |  |  | 0.723 | printed | 0.95 |
| AgentMD |  | #5b85a8 | 0.663 |  |  | 0.663 | printed | 0.95 |
| AgentMD |  | #5b85a8 | 0.823 |  |  | 0.823 | printed | 0.95 |

## Checks

- 3 charts found by their tick labels

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-180501_ollama_gemma4-26b-a4b-it-qat.json`.
