# Figure data: pictures_3 of Public-test-manuscript (page 18)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-20, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 4. LLM Performance on Text-Only Gastroenterology Multiple-choice Questions.

**What the figure shows (model):** Horizontal stacked bars showing, for each of 36 LLM configurations, the percentage of 300 ACG gastroenterology questions answered Correct, 2OP, EOP, NOP, Error or Incorrect; only the Correct share is printed.

## Chart 1: All 2022 ACG questions (N = 300) (stacked_bar, horizontal)

x axis "Percentage" [%] linear 0 to 100; y axis categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 47.7 |  |  | 47.7% | printed | 0.95 |
| GPT-3.5 API |  | Correct | 46 |  |  | 46.0% | printed | 0.95 |
| GPT-4 Web |  | Correct | 66 |  |  | 66.0% | printed | 0.95 |
| GPT-4 API |  | Correct | 66 |  |  | 66.0% | printed | 0.95 |
| GPT-4o API |  | Correct | 73.7 |  |  | 73.7% | printed | 0.95 |
| GPT-4omini API |  | Correct | 56 |  |  | 56.0% | printed | 0.95 |
| Claude3-Hiaku Web |  | Correct | 50 |  |  | 50.0% | printed | 0.85 |
| Claude3-Haiku API |  | Correct | 50.3 |  |  | 50.3% | printed | 0.95 |
| Claude3-Sonnet Web |  | Correct | 55.3 |  |  | 55.3% | printed | 0.95 |
| Claude3-Sonnet API |  | Correct | 52.3 |  |  | 52.3% | printed | 0.95 |
| Claude3-Opus Web |  | Correct | 65.7 |  |  | 65.7% | printed | 0.95 |
| Claude3-Opus API |  | Correct | 66 |  |  | 66.0% | printed | 0.95 |
| Claude3.5-Sonnet API |  | Correct | 74 |  |  | 74.0% | printed | 0.95 |
| Mistralv2-7b Poe |  | Correct | 40.7 |  |  | 40.7% | printed | 0.95 |
| Mistralv2-7b-Q8 Local |  | Correct | 37.3 |  |  | 37.3% | printed | 0.95 |
| Mistral-Large Poe |  | Correct | 60.3 |  |  | 60.3% | printed | 0.95 |
| Mixtral-8x7b Poe |  | Correct | 54.3 |  |  | 54.3% | printed | 0.95 |
| Llama2-7b Poe |  | Correct | 30.7 |  |  | 30.7% | printed | 0.95 |
| Llama2-7b-Q8 Local |  | Correct | 30.3 |  |  | 30.3% | printed | 0.95 |
| medicineLLM-7b-Q8 Local |  | Correct | 27 |  |  | 27.0% | printed | 0.95 |
| Llama2-13b Poe |  | Correct | 33 |  |  | 33.0% | printed | 0.95 |
| Llama2-13b-Q5 Local |  | Correct | 33.4 |  |  | 33.4% | printed | 0.95 |
| Llama2-70b Poe |  | Correct | 37.3 |  |  | 37.3% | printed | 0.95 |
| Llama3-8b Poe |  | Correct | 43.3 |  |  | 43.3% | printed | 0.95 |
| Llama3-8b-Q8 Local |  | Correct | 31 |  |  | 31.0% | printed | 0.95 |
| OpenBioLLM-8b-Q8 Local |  | Correct | 29 |  |  | 29.0% | printed | 0.95 |
| Llama3-70b Poe |  | Correct | 54.7 |  |  | 54.7% | printed | 0.95 |
| Llama3.1-8b Poe |  | Correct | 43 |  |  | 43.0% | printed | 0.95 |
| Llama3.1-70b Poe |  | Correct | 58.3 |  |  | 58.3% | printed | 0.95 |
| Llama3.1-405b Poe |  | Correct | 64 |  |  | 64.0% | printed | 0.95 |
| Gemini Web |  | Correct | 41.3 |  |  | 41.3% | printed | 0.95 |
| GeminiAdvanced Web |  | Correct | 51.7 |  |  | 51.7% | printed | 0.95 |
| Gemma2-9b Poe |  | Correct | 44.7 |  |  | 44.7% | printed | 0.95 |
| Gemma2-9b-Q8 Local |  | Correct | 45.3 |  |  | 45.3% | printed | 0.95 |
| Gemma2-27b Poe |  | Correct | 50 |  |  | 50.0% | printed | 0.85 |
| Phi3-3b-Q16 Local |  | Correct | 42.7 |  |  | 42.7% | printed | 0.95 |
| Phi3-14b-Q6 Local |  | Correct | 48.7 |  |  | 48.7% | printed | 0.95 |

- Note: Only the Correct segment is printed per bar; the other segments extend to 100%.
- Note: Quantized-model and fine-tuned-model markers appear beside some rows.

## Not read, or uncertain

- 2OP, EOP, NOP, Error and Incorrect segments for all 37 bars were not tabulated (no printed values; mostly small slivers, Incorrect fills the remainder to 100%).

## Checks

- the rule splitter finds 2 chart(s), the model lists 1: read whole
- panel 1: stacked segments do not sum to 100: GPT-3.5 Web sums to 47.7; GPT-3.5 API sums to 46; GPT-4 Web sums to 66; GPT-4 API sums to 66; GPT-4o API sums to 73.7

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261120-162816_cloud_anthropic-claude-sonnet-5.5.json`.
