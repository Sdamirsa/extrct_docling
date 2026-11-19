# Figure data: pictures_8 of Public-test-manuscript (page 58)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Supplementary Figure S2. Confusion matrix of GPT-3.5 performance in the extraction of selected options from the raw textual response of LLMs.

**What the figure shows (model):** This figure is a confusion matrix comparing GPT-3.5 extracted options from LLM textual responses against blinded human validation.

## Chart 1: GPT-3.5 Extracted Option from LLM Textual Response (heatmap, horizontal)

y axis "Blinded Human Validation".

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| A | A |  | 16 |  |  | 16 | printed | 0.95 |
| B | B |  | 25 |  |  | 25 | printed | 0.95 |
| C | C |  | 24 |  |  | 24 | printed | 0.95 |
| D | D |  | 13 |  |  | 13 | printed | 0.95 |
| E | E |  | 4 |  |  | 4 | printed | 0.95 |
| 2OP | 2OP |  | 1 |  |  | 1 | printed | 0.95 |
| EOP | EOP |  | 5 |  |  | 5 | printed | 0.95 |
| NOP | NOP |  | 5 |  |  | 5 | printed | 0.95 |
| Error | Error |  | 3 |  |  | 3 | printed | 0.95 |
| A | GPT: Require Evaluation |  | 0 |  |  | 0 | printed | 0.95 |
| B | GPT: Require Evaluation |  | 0 |  |  | 0 | printed | 0.95 |
| C | GPT: Require Evaluation |  | 0 |  |  | 0 | printed | 0.95 |
| D | GPT: Require Evaluation |  | 0 |  |  | 0 | printed | 0.95 |
| E | GPT: Require Evaluation |  | 0 |  |  | 0 | printed | 0.95 |
| 2OP | GPT: Require Evaluation |  | 1 |  |  | 1 | printed | 0.95 |
| EOP | GPT: Require Evaluation |  | 5 |  |  | 5 | printed | 0.95 |
| NOP | GPT: Require Evaluation |  | 5 |  |  | 5 | printed | 0.95 |
| Error | GPT: Require Evaluation |  | 3 |  |  | 3 | printed | 0.95 |
| A | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |
| B | Parsing Failed |  | 2 |  |  | 2 | printed | 0.95 |
| C | Parsing Failed |  | 1 |  |  | 1 | printed | 0.95 |
| D | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |
| E | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |
| 2OP | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |
| EOP | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |
| NOP | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |
| Error | Parsing Failed |  | 0 |  |  | 0 | printed | 0.95 |

- Note: no axis calibrated from tick labels; values are the model's

## Checks

- 3 blocks, one chart seen by the model: read whole

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-094515_ollama_gemma4-26b-a4b-it-qat.json`.
