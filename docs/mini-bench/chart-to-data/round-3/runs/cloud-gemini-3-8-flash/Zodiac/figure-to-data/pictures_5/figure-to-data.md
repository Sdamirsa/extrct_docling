# Figure data: pictures_5 of Zodiac (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC.

**What the figure shows (model):** Evaluations of diagnostic lability across different models and performance comparison between single-agent and multi-agent ZODIAC across eight clinical criteria.

## Chart a: (a) Diagnostic lability (box, vertical)

x axis categorical; y axis linear 0 to 0.4.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ZODIAC |  |  | 0.005 | 0 | 0.009 |  | vlm | 0.8 |
| GPT-4o |  |  | 0.091 | 0 | 0.217 |  | vlm | 0.8 |
| Gemini -Pro |  |  | 0.05 | 0 | 0.153 |  | vlm | 0.8 |
| Llama-3.1 -405B |  |  | 0.105 | 0 | 0.194 |  | vlm | 0.8 |
| Mixtral -8x22B |  |  | 0.128 | 0.103 | 0.199 |  | vlm | 0.8 |
| BioGPT -Large |  |  | 0.128 | 0.016 | 0.222 |  | vlm | 0.8 |
| Meditron -70B |  |  | 0.055 | 0.025 | 0.107 |  | vlm | 0.8 |
| Med42 -70B |  |  | 0.032 | 0.011 | 0.064 |  | vlm | 0.8 |

- Note: Quartiles and outliers:
- Note: ZODIAC: Q1≈0.003, Q3≈0.007, outlier diamond at 0.016
- Note: GPT-4o: Q1≈0.055, Q3≈0.137
- Note: Gemini -Pro: Q1≈0.007, Q3≈0.105
- Note: Llama-3.1 -405B: Q1≈0.000, Q3≈0.165
- Note: Mixtral -8x22B: Q1≈0.112, Q3≈0.158, outlier diamond at 0.005
- Note: BioGPT -Large: Q1≈0.071, Q3≈0.183, outlier diamond at 0.361
- Note: Meditron -70B: Q1≈0.027, Q3≈0.073
- Note: Med42 -70B: Q1≈0.018, Q3≈0.039

## Chart b: (b) Signle-agent v.s. multi-agent (grouped_bar, vertical)

x axis categorical; y axis linear 1 to 5.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ACC |  | Signle-agent | 4.19 |  |  |  | vlm | 0.8 |
| ACC |  | Multi-agent (this work) | 4.44 |  |  |  | vlm | 0.8 |
| CPL |  | Signle-agent | 4.46 |  |  |  | vlm | 0.8 |
| CPL |  | Multi-agent (this work) | 4.51 |  |  |  | vlm | 0.8 |
| ORG |  | Signle-agent | 4.3 |  |  |  | vlm | 0.8 |
| ORG |  | Multi-agent (this work) | 4.76 |  |  |  | vlm | 0.8 |
| CPH |  | Signle-agent | 4.94 |  |  |  | vlm | 0.8 |
| CPH |  | Multi-agent (this work) | 5 |  |  |  | vlm | 0.8 |
| SCI |  | Signle-agent | 4.14 |  |  |  | vlm | 0.8 |
| SCI |  | Multi-agent (this work) | 4.44 |  |  |  | vlm | 0.8 |
| CNS |  | Signle-agent | 4.46 |  |  |  | vlm | 0.8 |
| CNS |  | Multi-agent (this work) | 4.53 |  |  |  | vlm | 0.8 |
| FFH |  | Signle-agent | 4.41 |  |  |  | vlm | 0.8 |
| FFH |  | Multi-agent (this work) | 4.83 |  |  |  | vlm | 0.8 |
| FFB |  | Signle-agent | 5 |  |  |  | vlm | 0.8 |
| FFB |  | Multi-agent (this work) | 5 |  |  |  | vlm | 0.8 |

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-160847_cloud_google-gemini-3.8-flash.json`.
