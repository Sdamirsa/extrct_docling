# Figure data: pictures_5 of Zodiac (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 7: Evaluations on (a) diagnostic lability among multiple executions; (b) single-agent ZODIAC.

**What the figure shows (model):** The figure compares the diagnostic lability of various large language models and evaluates the performance of single-agent versus multi-agent systems across different metrics.

## Chart 1: 0.4 (line, vertical)

x axis categorical; y axis linear 0 to 0.4.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| -Pro |  | #000000 | 0.0042 |  |  |  | vector | 0.9 |
| -Pro |  | #000000 | 0.0105 |  |  |  | vector | 0.9 |
| -Pro |  | #000000 | 0.0493 |  |  |  | vector | 0.9 |
| -Pro |  | #000000 | 0.0881 |  |  |  | vector | 0.9 |
| -Pro |  | #000000 | 0.103 |  |  |  | vector | 0.9 |
| -405B |  | #000000 | 0.0024 |  |  |  | vector | 0.9 |
| -405B |  | #000000 | 0.0451 |  |  |  | vector | 0.9 |
| -405B |  | #000000 | 0.1045 |  |  |  | vector | 0.9 |
| -405B |  | #000000 | 0.1639 |  |  |  | vector | 0.9 |
| -405B |  | #000000 | 0.1629 |  |  |  | vector | 0.9 |
| -8x22B |  | #000000 | 0.1096 |  |  |  | vector | 0.9 |
| -8x22B |  | #000000 | 0.1072 |  |  |  | vector | 0.9 |
| -8x22B |  | #000000 | 0.1261 |  |  |  | vector | 0.9 |
| -8x22B |  | #000000 | 0.1451 |  |  |  | vector | 0.9 |
| -8x22B |  | #000000 | 0.1579 |  |  |  | vector | 0.9 |
| -Large |  | #000000 | 0.0693 |  |  |  | vector | 0.9 |
| -Large |  | #000000 | 0.0827 |  |  |  | vector | 0.9 |
| -Large |  | #000000 | 0.1265 |  |  |  | vector | 0.9 |
| -Large |  | #000000 | 0.1703 |  |  |  | vector | 0.9 |
| -Large |  | #000000 | 0.1809 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0244 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0366 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0557 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0748 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0731 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0165 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0236 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0327 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0418 |  |  |  | vector | 0.9 |
| -70B |  | #000000 | 0.0396 |  |  |  | vector | 0.9 |

## Chart 2: 5 (bar, vertical)

x axis categorical; y axis linear 3 to 5.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| ACC |  | #345b7d | 4.3964 |  |  |  | vector | 0.9 |
| CPL |  | #345b7d | 4.4963 |  |  |  | vector | 0.9 |
| ORG |  | #345b7d | 4.696 |  |  |  | vector | 0.9 |
| CPH |  | #345b7d | 4.8956 |  |  |  | vector | 0.9 |
| SCI |  | #345b7d | 4.3964 |  |  |  | vector | 0.9 |
| CNS |  | #345b7d | 1.5375* |  |  |  | vector | 0.65 |
| CNS |  | #345b7d | 4.4963 |  |  |  | vector | 0.9 |
| FFH |  | #345b7d | 4.7958 |  |  |  | vector | 0.9 |
| FFB |  | #345b7d | 4.9955 |  |  |  | vector | 0.9 |

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Checks

- 2 charts found by their tick labels
- panel 2: 1.5375 outside the axis range [3, 5] (CNS/#345b7d)

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113919_ollama_gemma4-26b-a4b-it-qat.json`.
