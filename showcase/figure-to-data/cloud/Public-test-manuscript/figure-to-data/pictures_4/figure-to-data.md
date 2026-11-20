# Figure data: pictures_4 of Public-test-manuscript (page 20)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-20, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 5. VLM Performance on Gastroenterology Multiple-Choice Questions with Image Data.

**What the figure shows (model):** Horizontal stacked bars showing the percentage of answers (Correct, 2OP, EOP, NOP, Error, Incorrect) for gastroenterology image multiple-choice questions, by model, platform and image-input condition, with significance versus the no-image reference.

## Chart 1: VLM Performance on Gastroenterology Multiple-Choice Questions with Image Data (stacked_bar, horizontal)

x axis "Percentage" [%] linear 0 to 100; y axis categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT4 Web - no image |  | Correct | 65.2 |  |  | 65.2% | printed | 0.95 |
| GPT4 Web - LLM caption |  | Correct | 59.4 |  |  | 59.4% | printed | 0.95 |
| GPT4 Web - direct image |  | Correct | 68.1 |  |  | 68.1% | printed | 0.95 |
| GPT4 Web - human hint |  | Correct | 73.2 |  |  | 73.2% | printed | 0.95 |
| GPT4 API - no image |  | Correct | 68.8 |  |  | 68.8% | printed | 0.95 |
| GPT4 API - LLM caption |  | Correct | 64.5 |  |  | 64.5% | printed | 0.95 |
| GPT4 API - direct image |  | Correct | 65.2 |  |  | 65.2% | printed | 0.95 |
| GPT4 API - human hint |  | Correct | 71.7 |  |  | 71.7% | printed | 0.95 |
| Claude3Opus Web - no image |  | Correct | 63.8 |  |  | 63.8% | printed | 0.95 |
| Claude3Opus Web - LLM caption |  | Correct | 48.6 |  |  | 48.6% | printed | 0.95 |
| Claude3Opus Web - direct image |  | Correct | 63.8 |  |  | 63.8% | printed | 0.95 |
| Claude3Opus Web - human hint |  | Correct | 76.8 |  |  | 76.8% | printed | 0.95 |
| Claude3Opus API - no image |  | Correct | 68.1 |  |  | 68.1% | printed | 0.95 |
| Claude3Opus API - LLM caption |  | Correct | 68.8 |  |  | 68.8% | printed | 0.95 |
| Claude3Opus API - direct image |  | Correct | 68.8 |  |  | 68.8% | printed | 0.95 |
| Claude3Opus API - human hint |  | Correct | 78.3 |  |  | 78.3% | printed | 0.95 |
| Claude3Sonnet API - no image |  | Correct | 53.7 |  |  | 53.7% | printed | 0.95 |
| Claude3Sonnet API - LLM caption |  | Correct | 54.3 |  |  | 54.3% | printed | 0.95 |
| Claude3Sonnet API - direct image |  | Correct | 73.9 |  |  | 73.9% | printed | 0.95 |
| Claude3Sonnet API - human hint |  | Correct | 56.5 |  |  | 56.5% | printed | 0.95 |
| GeminiAdvanced Web - no image |  | Correct | 25 |  |  | 25.0% | printed | 0.95 |
| GeminiAdvanced Web - LLM caption |  | Correct | 47.8 |  |  | 47.8% | printed | 0.85 |
| GeminiAdvanced Web- direct image |  | Correct | 20.3 |  |  | 20.3% | printed | 0.95 |
| GeminiAdvanced Web - human hint |  | Correct | 54.3 |  |  | 54.3% | printed | 0.95 |

- Note: Significance vs reference: GPT4 Web ns; GPT4 API ns; Claude3Opus Web LLM caption ****, direct ns, human hint **; Claude3Opus API caption ns, direct ns, hint *; Claude3Sonnet API caption ns, direct ****, hint ns; Gemini caption ****, direct ns, hint ****.
- Note: Only the Correct segments are labelled; other segments (2OP, EOP, NOP, Error, Incorrect) are not tabulated.

## Not read, or uncertain

- Non-Correct segments (2OP, EOP, NOP, Error, Incorrect) of all 24 bars were not read; they are visible but unlabelled.

## Checks

- panel 1: stacked segments do not sum to 100: GPT4 Web - no image sums to 65.2; GPT4 Web - LLM caption sums to 59.4; GPT4 Web - direct image sums to 68.1; GPT4 Web - human hint sums to 73.2; GPT4 API - no image sums to 68.8

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261120-162816_cloud_anthropic-claude-sonnet-5.5.json`.
