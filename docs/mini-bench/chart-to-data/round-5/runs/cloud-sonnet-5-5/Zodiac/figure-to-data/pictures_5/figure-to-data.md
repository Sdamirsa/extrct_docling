# Figure data: pictures_5 of Zodiac (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC.

**What the figure shows (model):** (a) Notched box plots of diagnostic lability across repeated executions for ZODIAC and seven baseline LLMs; (b) grouped bars comparing single-agent and multi-agent (this work) scores on eight dimensions.

## Chart a: Diagnostic lability (box, vertical)

x axis categorical; y axis "Diagnostic lability" linear 0 to 0.4.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ZODIAC |  |  | 0.005 | 0 | 0.01 |  | vlm | 0.8 |
| GPT-4o |  |  | 0.09 | 0 | 0.215 |  | vlm | 0.8 |
| Gemini-Pro |  |  | 0.05 | 0 | 0.15 |  | vlm | 0.8 |
| Llama-3.1-405B |  |  | 0.105 | 0 | 0.195 |  | vlm | 0.8 |
| Mixtral-8x22B |  |  | 0.125 | 0.1 | 0.2 |  | vlm | 0.8 |
| BioGPT-Large |  |  | 0.125 | 0.015 | 0.222 |  | vlm | 0.8 |
| Meditron-70B |  |  | 0.055 | 0.005 | 0.105 |  | vlm | 0.8 |
| Med42-70B |  |  | 0.035 | 0.005 | 0.065 |  | vlm | 0.8 |

- Note: Quartiles approx: ZODIAC 0-0.01; GPT-4o 0.055-0.135; Gemini-Pro 0.005-0.105; Llama-3.1 0.005-0.165; Mixtral 0.11-0.16; BioGPT 0.07-0.18; Meditron 0.03-0.075; Med42 0.025-0.04.
- Note: Outliers (diamonds): ZODIAC ~0.02; Mixtral ~0.005; BioGPT ~0.357.

## Chart b: Signle-agent v.s. multi-agent (grouped_bar, vertical)

x axis categorical; y axis linear 1 to 5.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ACC |  | Signle-agent | 4.2 |  |  |  | vlm | 0.8 |
| ACC |  | Multi-agent (this work) | 4.45 |  |  |  | vlm | 0.8 |
| CPL |  | Signle-agent | 4.5 |  |  |  | vlm | 0.8 |
| CPL |  | Multi-agent (this work) | 4.55 |  |  |  | vlm | 0.8 |
| ORG |  | Signle-agent | 4.35 |  |  |  | vlm | 0.8 |
| ORG |  | Multi-agent (this work) | 4.75 |  |  |  | vlm | 0.8 |
| CPH |  | Signle-agent | 4.93 |  |  |  | vlm | 0.8 |
| CPH |  | Multi-agent (this work) | 4.95 |  |  |  | vlm | 0.8 |
| SCI |  | Signle-agent | 4.17 |  |  |  | vlm | 0.8 |
| SCI |  | Multi-agent (this work) | 4.45 |  |  |  | vlm | 0.8 |
| CNS |  | Signle-agent | 4.48 |  |  |  | vlm | 0.8 |
| CNS |  | Multi-agent (this work) | 4.55 |  |  |  | vlm | 0.8 |
| FFH |  | Signle-agent | 4.43 |  |  |  | vlm | 0.8 |
| FFH |  | Multi-agent (this work) | 4.85 |  |  |  | vlm | 0.8 |
| FFB |  | Signle-agent | 5 |  |  |  | vlm | 0.8 |
| FFB |  | Multi-agent (this work) | 5 |  |  |  | vlm | 0.8 |

- Note: Y axis ticks labelled only at 1, 3, 5.

## Checks

- the rule splitter finds 1 chart(s), the model lists 2: cut between the listed charts

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-180719_cloud_anthropic-claude-sonnet-5.5.json`.
