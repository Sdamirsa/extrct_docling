# Figure data: pictures_5 of Zodiac (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC.

**What the figure shows (model):** Evaluation of diagnostic lability across different models using notched box plots, and comparison between single-agent and multi-agent ZODIAC across various evaluation criteria using a grouped bar chart.

## Chart 1: (a) Diagnostic lability (box, vertical)

x axis categorical; y axis linear 0 to 0.4.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ZODIAC |  |  | 0.005 | 0 | 0.007 |  | vlm | 0.8 |
| GPT-4o |  |  | 0.091 | 0 | 0.218 |  | vlm | 0.8 |
| Gemini -Pro |  |  | 0.048 | 0 | 0.155 |  | vlm | 0.8 |
| Llama-3.1 -405B |  |  | 0.107 | 0 | 0.193 |  | vlm | 0.8 |
| Mixtral -8x22B |  |  | 0.127 | 0.105 | 0.2 |  | vlm | 0.8 |
| BioGPT -Large |  |  | 0.13 | 0.014 | 0.223 |  | vlm | 0.8 |
| Meditron -70B |  |  | 0.055 | 0.025 | 0.109 |  | vlm | 0.8 |
| Med42 -70B |  |  | 0.036 | 0.009 | 0.066 |  | vlm | 0.8 |

- Note: Quartiles (Q1, Q3): ZODIAC (0.000, 0.007), GPT-4o (0.055, 0.136), Gemini -Pro (0.007, 0.105), Llama-3.1 -405B (0.000, 0.164), Mixtral -8x22B (0.114, 0.159), BioGPT -Large (0.070, 0.182), Meditron -70B (0.027, 0.073), Med42 -70B (0.018, 0.041).
- Note: Outliers: ZODIAC (0.016), Mixtral -8x22B (0.007), BioGPT -Large (0.359).

## Chart 2: (b) Signle-agent v.s. multi-agent (grouped_bar, vertical)

x axis categorical; y axis linear 1 to 5.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ACC |  | Signle-agent | 4.11 |  |  |  | vlm | 0.8 |
| ACC |  | Multi-agent (this work) | 4.39 |  |  |  | vlm | 0.8 |
| CPL |  | Signle-agent | 4.41 |  |  |  | vlm | 0.8 |
| CPL |  | Multi-agent (this work) | 4.48 |  |  |  | vlm | 0.8 |
| ORG |  | Signle-agent | 4.27 |  |  |  | vlm | 0.8 |
| ORG |  | Multi-agent (this work) | 4.73 |  |  |  | vlm | 0.8 |
| CPH |  | Signle-agent | 4.93 |  |  |  | vlm | 0.8 |
| CPH |  | Multi-agent (this work) | 4.98 |  |  |  | vlm | 0.8 |
| SCI |  | Signle-agent | 4.07 |  |  |  | vlm | 0.8 |
| SCI |  | Multi-agent (this work) | 4.43 |  |  |  | vlm | 0.8 |
| CNS |  | Signle-agent | 4.43 |  |  |  | vlm | 0.8 |
| CNS |  | Multi-agent (this work) | 4.5 |  |  |  | vlm | 0.8 |
| FFH |  | Signle-agent | 4.39 |  |  |  | vlm | 0.8 |
| FFH |  | Multi-agent (this work) | 4.84 |  |  |  | vlm | 0.8 |
| FFB |  | Signle-agent | 5 |  |  |  | vlm | 0.8 |
| FFB |  | Multi-agent (this work) | 5 |  |  |  | vlm | 0.8 |

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-154849_cloud_google-gemini-3.8-flash.json`.
