# Figure data: pictures_5 of AgentMD (page 5)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Fig. 3 | Evaluations of AgentMD on RiskQA. a ExampleofaquestioninRiskQAand howAgentMDanswersit. b TheperformanceofGPT-3.5-based AgentMDcompared to Chain-of-Thought (CoT) prompting on RiskQA. c The performance of GPT-4based AgentMD compared to CoT prompting on RiskQA. d The accuracy of tool

**What the figure shows (model):** Three bar charts of accuracy: AgentMD vs CoT and random baselines on RiskQA with GPT-3.5 (b) and GPT-4 (c), and accuracy of AgentMD tool selection compared with MedCPT (d), each with error bars.

## Chart 1: Accuracy on RiskQA (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Random |  |  | 0.2 |  |  | 0.200 | printed | 0.95 |
| CoT (GPT-3.5) |  |  | 0.321 | 0.3 | 0.343 | 0.321 | printed | 0.95 |
| AgentMD (GPT-3.5) |  |  | 0.546 | 0.521 | 0.572 | 0.546 | printed | 0.95 |

- Note: Error bars estimated from the image; Random has no error bar.

## Chart 2: Accuracy on RiskQA (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Random |  |  | 0.2 |  |  | 0.200 | printed | 0.95 |
| CoT (GPT-4) |  |  | 0.409 | 0.385 | 0.433 | 0.409 | printed | 0.95 |
| AgentMD (GPT-4) |  |  | 0.877 | 0.862 | 0.894 | 0.877 | printed | 0.95 |

- Note: Error bars estimated from the image; Random has no error bar.

## Chart 3: Accuracy of AgentMD Tool Selection (bar, vertical)

x axis categorical; y axis "Accuracy" linear 0 to 1.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| MedCPT |  |  | 0.723 | 0.698 | 0.747 | 0.723 | printed | 0.95 |
| AgentMD (GPT-3.5) |  |  | 0.663 | 0.638 | 0.687 | 0.663 | printed | 0.95 |
| AgentMD (GPT-4) |  |  | 0.823 | 0.802 | 0.843 | 0.823 | printed | 0.95 |

- Note: Error bars estimated from the image.

## Not read, or uncertain

- Panel a (example question) is not part of the supplied image.

## Checks

- 3 charts found by their tick labels

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-180500_cloud_anthropic-claude-sonnet-5.5.json`.
