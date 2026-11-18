# Figure data: pictures_5 of Zodiac (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC.

**What the figure shows (model):** Two panels: (a) notched box plots of diagnostic lability for eight models, and (b) grouped bars comparing single-agent and multi-agent scores on eight categories (ACC to FFB).

## Chart 1: (a) Diagnostic lability (box, vertical)

x axis "Model" categorical; y axis "Diagnostic lability" linear 0 to 0.4.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ZODIAC |  |  | 0.005 | 0.002 | 0.01 |  | agent | 0.8 |
| GPT-4o |  |  | 0.09 | 0 | 0.217 |  | agent | 0.8 |
| Gemini-Pro |  |  | 0.05 | 0.003 | 0.152 |  | agent | 0.8 |
| Llama-3.1-405B |  |  | 0.105 | 0.002 | 0.193 |  | agent | 0.8 |
| Mixtral-8x22B |  |  | 0.125 | 0.102 | 0.2 |  | agent | 0.8 |
| BioGPT-Large |  |  | 0.127 | 0.016 | 0.223 |  | agent | 0.8 |
| Meditron-70B |  |  | 0.055 | 0.007 | 0.106 |  | agent | 0.8 |
| Med42-70B |  |  | 0.03 | 0.007 | 0.065 |  | agent | 0.8 |

- Note: Notched box plot; approximate quartiles (Q1-Q3): ZODIAC 0.003-0.008; GPT-4o 0.057-0.135; Gemini-Pro 0.005-0.103; Llama 0.003-0.163; Mixtral 0.11-0.158; BioGPT 0.07-0.18; Meditron 0.027-0.075; Med42 0.02-0.04.
- Note: Outliers (diamonds): ZODIAC ~0.02; Mixtral ~0.005; BioGPT ~0.357.

## Chart 2: (b) Signle-agent v.s. multi-agent (grouped_bar, vertical)

x axis categorical; y axis linear 1 to 5.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ACC |  | Signle-agent | 4.2 |  |  |  | agent | 0.8 |
| ACC |  | Multi-agent (this work) | 4.45 |  |  |  | agent | 0.8 |
| CPL |  | Signle-agent | 4.5 |  |  |  | agent | 0.8 |
| CPL |  | Multi-agent (this work) | 4.55 |  |  |  | agent | 0.8 |
| ORG |  | Signle-agent | 4.35 |  |  |  | agent | 0.8 |
| ORG |  | Multi-agent (this work) | 4.75 |  |  |  | agent | 0.8 |
| CPH |  | Signle-agent | 4.93 |  |  |  | agent | 0.8 |
| CPH |  | Multi-agent (this work) | 4.95 |  |  |  | agent | 0.8 |
| SCI |  | Signle-agent | 4.17 |  |  |  | agent | 0.8 |
| SCI |  | Multi-agent (this work) | 4.45 |  |  |  | agent | 0.8 |
| CNS |  | Signle-agent | 4.5 |  |  |  | agent | 0.8 |
| CNS |  | Multi-agent (this work) | 4.55 |  |  |  | agent | 0.8 |
| FFH |  | Signle-agent | 4.45 |  |  |  | agent | 0.8 |
| FFH |  | Multi-agent (this work) | 4.85 |  |  |  | agent | 0.8 |
| FFB |  | Signle-agent | 5 |  |  |  | agent | 0.8 |
| FFB |  | Multi-agent (this work) | 5 |  |  |  | agent | 0.8 |

## Not read, or uncertain

- Panel (b) has no printed y-axis name and its bar values are estimated against the ticks at 1, 3 and 5.
- Panel (a) quartiles and outliers are recorded only in the notes, not as separate points; all values are visual estimates.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-115222_agent_claude-sonnet-5-5.json`.
