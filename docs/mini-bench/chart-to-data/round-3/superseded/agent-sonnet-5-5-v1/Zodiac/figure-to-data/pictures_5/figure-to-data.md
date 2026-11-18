# Figure data: pictures_5 of Zodiac (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC.

**What the figure shows (model):** Two panels: (a) notched box plots of diagnostic lability for ZODIAC and seven other models, and (b) grouped bars comparing single-agent and multi-agent scores on eight metrics (ACC to FFB) on a 1–5 scale.

## Chart 1: (a) Diagnostic lability (box, vertical)

x axis "Model" categorical; y axis "Diagnostic lability" linear 0 to 0.4.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ZODIAC |  |  | 0.005 | 0 | 0.012 |  | agent | 0.8 |
| GPT-4o |  |  | 0.09 | 0 | 0.217 |  | agent | 0.8 |
| Gemini-Pro |  |  | 0.05 | 0.002 | 0.152 |  | agent | 0.8 |
| Llama-3.1-405B |  |  | 0.105 | 0.002 | 0.193 |  | agent | 0.8 |
| Mixtral-8x22B |  |  | 0.126 | 0.101 | 0.199 |  | agent | 0.8 |
| BioGPT-Large |  |  | 0.127 | 0.015 | 0.223 |  | agent | 0.8 |
| Meditron-70B |  |  | 0.055 | 0.006 | 0.106 |  | agent | 0.8 |
| Med42-70B |  |  | 0.033 | 0.005 | 0.064 |  | agent | 0.8 |

- Note: Notched box plots; quartiles approx (Q1-Q3): ZODIAC ~0.003-0.008; GPT-4o 0.055-0.135; Gemini-Pro 0.005-0.103; Llama 0.003-0.164; Mixtral 0.107-0.157; BioGPT 0.069-0.181; Meditron 0.025-0.075; Med42 0.017-0.041.
- Note: Outliers (diamonds): ZODIAC ~0.02; Mixtral ~0.008 and ~0.003; BioGPT ~0.358.
- Note: Values read from pixel positions, approximate.

## Chart 2: (b) Signle-agent v.s. multi-agent (grouped_bar, vertical)

x axis "Metric" categorical; y axis linear 1 to 5.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ACC |  | Signle-agent | 4.2 |  |  |  | agent | 0.8 |
| ACC |  | Multi-agent (this work) | 4.45 |  |  |  | agent | 0.8 |
| CPL |  | Signle-agent | 4.49 |  |  |  | agent | 0.8 |
| CPL |  | Multi-agent (this work) | 4.55 |  |  |  | agent | 0.8 |
| ORG |  | Signle-agent | 4.34 |  |  |  | agent | 0.8 |
| ORG |  | Multi-agent (this work) | 4.74 |  |  |  | agent | 0.8 |
| CPH |  | Signle-agent | 4.94 |  |  |  | agent | 0.8 |
| CPH |  | Multi-agent (this work) | 4.95 |  |  |  | agent | 0.8 |
| SCI |  | Signle-agent | 4.17 |  |  |  | agent | 0.8 |
| SCI |  | Multi-agent (this work) | 4.45 |  |  |  | agent | 0.8 |
| CNS |  | Signle-agent | 4.49 |  |  |  | agent | 0.8 |
| CNS |  | Multi-agent (this work) | 4.54 |  |  |  | agent | 0.8 |
| FFH |  | Signle-agent | 4.44 |  |  |  | agent | 0.8 |
| FFH |  | Multi-agent (this work) | 4.85 |  |  |  | agent | 0.8 |
| FFB |  | Signle-agent | 5 |  |  |  | agent | 0.8 |
| FFB |  | Multi-agent (this work) | 5 |  |  |  | agent | 0.8 |

- Note: Y axis has ticks 1, 3, 5 only; values read from pixel positions, approximate. Y axis has no printed name.

## Not read, or uncertain

- Box quartiles and outlier diamonds in panel (a) are given only approximately in the chart notes, not as separate points.
- The notch extents of the box plots were not recorded.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113943_agent_claude-sonnet-5-5.json`.
