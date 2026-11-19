# Figure data: pictures_12 of Public-test-manuscript (page 64)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Supplementary Figure S6. Performance stratified by patient care phase

**What the figure shows (model):** Five stacked-bar charts of LLM answer outcomes (Correct, ZOP, EOP, NOP, Error, Incorrect) by model, one chart per question type: Complication, Diagnosis, Investigation, Pathophysiology and Treatment. Only approximate Correct percentages are read, and the Llama models are skipped.

## Chart 1: Question type: Complication (N = 55) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] log 0 to 100.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 56.4 |  |  |  | vlm | 0.8 |
| GPT-3.5 API |  | Correct | 52.7 |  |  |  | vlm | 0.8 |
| GPT-4 Web |  | Correct | 67 |  |  |  | vlm | 0.8 |
| GPT-4 API |  | Correct | 60 |  |  |  | vlm | 0.8 |
| GPT-4o API |  | Correct | 74.5* |  |  |  | vlm | 0.55 |
| GPT-4omini API |  | Correct | 54.5* |  |  |  | vlm | 0.55 |
| Claude3-haiku Web |  | Correct | 40* |  |  |  | vlm | 0.55 |
| Claude3-Haiku API |  | Correct | 52.7* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet Web |  | Correct | 60 |  |  |  | vlm | 0.8 |
| Claude3-Sonnet API |  | Correct | 50 |  |  |  | vlm | 0.8 |
| Claude3-Opus Web |  | Correct | 61.8 |  |  |  | vlm | 0.8 |
| Claude3-Opus API |  | Correct | 56.4 |  |  |  | vlm | 0.8 |
| Claude3.5-Sonnet API |  | Correct | 78 |  |  |  | vlm | 0.8 |
| Mistral2-7b Poe |  | Correct | 38.2* |  |  |  | vlm | 0.55 |
| Mistral2-7b-Q8 Local |  | Correct | 34.5* |  |  |  | vlm | 0.55 |
| Mistral Large Poe |  | Correct | 56.4* |  |  |  | vlm | 0.55 |
| Mixtral-8x7b Poe |  | Correct | 56.4* |  |  |  | vlm | 0.55 |
| Gemini Web |  | Correct | 34.5 |  |  |  | vlm | 0.8 |
| GeminiAdvanced Web |  | Correct | 43.6* |  |  |  | vlm | 0.55 |
| Gemma2-9b Poe |  | Correct | 50.9* |  |  |  | vlm | 0.55 |
| Gemma2-9b-Q8 Local |  | Correct | 52.7* |  |  |  | vlm | 0.55 |
| Gemma2-27b Poe |  | Correct | 58.2* |  |  |  | vlm | 0.55 |
| Phi3-3b-Q16 Local |  | Correct | 43 |  |  |  | vlm | 0.8 |
| Phi3-14b-Q6 Local |  | Correct | 54.5* |  |  |  | vlm | 0.55 |

- Note: Values read by eye, approximate.
- Note: Llama/meditron/OpenBioLLM bars (about 14, Correct roughly 24-58%) not tabulated.

## Chart 2: Question type: Diagnosis (N = 123) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 51.2 |  |  |  | vlm | 0.8 |
| GPT-3.5 API |  | Correct | 40.7 |  |  |  | vlm | 0.8 |
| GPT-4 Web |  | Correct | 73.2 |  |  |  | vlm | 0.8 |
| GPT-4 API |  | Correct | 76 |  |  |  | vlm | 0.8 |
| GPT-4o API |  | Correct | 79.7* |  |  |  | vlm | 0.55 |
| GPT-4omini API |  | Correct | 56.9* |  |  |  | vlm | 0.55 |
| Claude3-haiku Web |  | Correct | 54* |  |  |  | vlm | 0.55 |
| Claude3-Haiku API |  | Correct | 55.5* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet Web |  | Correct | 57 |  |  |  | vlm | 0.8 |
| Claude3-Sonnet API |  | Correct | 55.5 |  |  |  | vlm | 0.8 |
| Claude3-Opus Web |  | Correct | 68 |  |  |  | vlm | 0.8 |
| Claude3-Opus API |  | Correct | 65 |  |  |  | vlm | 0.8 |
| Claude3.5-Sonnet API |  | Correct | 77.5 |  |  |  | vlm | 0.8 |
| Mistral2-7b Poe |  | Correct | 45.5* |  |  |  | vlm | 0.55 |
| Mistral2-7b-Q8 Local |  | Correct | 43* |  |  |  | vlm | 0.55 |
| Mistral Large Poe |  | Correct | 64.2* |  |  |  | vlm | 0.55 |
| Mixtral-8x7b Poe |  | Correct | 58* |  |  |  | vlm | 0.55 |
| Gemini Web |  | Correct | 43.1 |  |  |  | vlm | 0.8 |
| GeminiAdvanced Web |  | Correct | 52* |  |  |  | vlm | 0.55 |
| Gemma2-9b Poe |  | Correct | 43* |  |  |  | vlm | 0.55 |
| Gemma2-9b-Q8 Local |  | Correct | 45* |  |  |  | vlm | 0.55 |
| Gemma2-27b Poe |  | Correct | 44* |  |  |  | vlm | 0.55 |
| Phi3-3b-Q16 Local |  | Correct | 44.7 |  |  |  | vlm | 0.8 |
| Phi3-14b-Q6 Local |  | Correct | 53.7* |  |  |  | vlm | 0.55 |

- Note: Values read by eye, approximate.
- Note: Llama-family bars (Correct roughly 25-76%) not tabulated.

## Chart 3: Question type: Investigation (N = 211) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 47.4 |  |  |  | vlm | 0.8 |
| GPT-3.5 API |  | Correct | 44 |  |  |  | vlm | 0.8 |
| GPT-4 Web |  | Correct | 66 |  |  |  | vlm | 0.8 |
| GPT-4 API |  | Correct | 65 |  |  |  | vlm | 0.8 |
| GPT-4o API |  | Correct | 73.9* |  |  |  | vlm | 0.55 |
| GPT-4omini API |  | Correct | 56* |  |  |  | vlm | 0.55 |
| Claude3-haiku Web |  | Correct | 51.7* |  |  |  | vlm | 0.55 |
| Claude3-Haiku API |  | Correct | 52* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet Web |  | Correct | 53.6 |  |  |  | vlm | 0.8 |
| Claude3-Sonnet API |  | Correct | 52.6 |  |  |  | vlm | 0.8 |
| Claude3-Opus Web |  | Correct | 66 |  |  |  | vlm | 0.8 |
| Claude3-Opus API |  | Correct | 65 |  |  |  | vlm | 0.8 |
| Claude3.5-Sonnet API |  | Correct | 72.5 |  |  |  | vlm | 0.8 |
| Mistral2-7b Poe |  | Correct | 41.7* |  |  |  | vlm | 0.55 |
| Mistral2-7b-Q8 Local |  | Correct | 40* |  |  |  | vlm | 0.55 |
| Mistral Large Poe |  | Correct | 58.8* |  |  |  | vlm | 0.55 |
| Mixtral-8x7b Poe |  | Correct | 55.5* |  |  |  | vlm | 0.55 |
| Gemini Web |  | Correct | 41 |  |  |  | vlm | 0.8 |
| GeminiAdvanced Web |  | Correct | 51* |  |  |  | vlm | 0.55 |
| Gemma2-9b Poe |  | Correct | 40* |  |  |  | vlm | 0.55 |
| Gemma2-9b-Q8 Local |  | Correct | 46* |  |  |  | vlm | 0.55 |
| Gemma2-27b Poe |  | Correct | 48* |  |  |  | vlm | 0.55 |
| Phi3-3b-Q16 Local |  | Correct | 43 |  |  |  | vlm | 0.8 |
| Phi3-14b-Q6 Local |  | Correct | 47.4* |  |  |  | vlm | 0.55 |

- Note: Values read by eye, approximate.
- Note: Llama-family bars (Correct roughly 27-64%) not tabulated.

## Chart 4: Question type: Pathophysiology (N = 3) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 33.3 |  |  |  | vlm | 0.8 |
| GPT-3.5 API |  | Correct | 0 |  |  |  | vlm | 0.8 |
| GPT-4 Web |  | Correct | 100 |  |  |  | vlm | 0.8 |
| GPT-4 API |  | Correct | 100 |  |  |  | vlm | 0.8 |
| GPT-4o API |  | Correct | 100* |  |  |  | vlm | 0.55 |
| GPT-4omini API |  | Correct | 33.3* |  |  |  | vlm | 0.55 |
| Claude3-haiku Web |  | Correct | 66.7* |  |  |  | vlm | 0.55 |
| Claude3-Haiku API |  | Correct | 66.7* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet Web |  | Correct | 66.7 |  |  |  | vlm | 0.8 |
| Claude3-Sonnet API |  | Correct | 33.3 |  |  |  | vlm | 0.8 |
| Claude3-Opus Web |  | Correct | 100 |  |  |  | vlm | 0.8 |
| Claude3-Opus API |  | Correct | 100 |  |  |  | vlm | 0.8 |
| Claude3.5-Sonnet API |  | Correct | 100 |  |  |  | vlm | 0.8 |
| Mistral2-7b Poe |  | Correct | 0* |  |  |  | vlm | 0.55 |
| Mistral2-7b-Q8 Local |  | Correct | 33.3* |  |  |  | vlm | 0.55 |
| Mistral Large Poe |  | Correct | 66.7* |  |  |  | vlm | 0.55 |
| Mixtral-8x7b Poe |  | Correct | 100* |  |  |  | vlm | 0.55 |
| Gemini Web |  | Correct | 33.3 |  |  |  | vlm | 0.8 |
| GeminiAdvanced Web |  | Correct | 100* |  |  |  | vlm | 0.55 |
| Gemma2-9b Poe |  | Correct | 66.7* |  |  |  | vlm | 0.55 |
| Gemma2-9b-Q8 Local |  | Correct | 66.7* |  |  |  | vlm | 0.55 |
| Gemma2-27b Poe |  | Correct | 100* |  |  |  | vlm | 0.55 |
| Phi3-3b-Q16 Local |  | Correct | 66.7 |  |  |  | vlm | 0.8 |
| Phi3-14b-Q6 Local |  | Correct | 33.3* |  |  |  | vlm | 0.55 |

- Note: N=3 so values are multiples of 33.3; small-text reading is uncertain.
- Note: Llama-family bars not tabulated.

## Chart 5: Question type: Treatment (N = 217) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 49.8 |  |  |  | vlm | 0.8 |
| GPT-3.5 API |  | Correct | 50 |  |  |  | vlm | 0.8 |
| GPT-4 Web |  | Correct | 64.5 |  |  |  | vlm | 0.8 |
| GPT-4 API |  | Correct | 67 |  |  |  | vlm | 0.8 |
| GPT-4o API |  | Correct | 73.7* |  |  |  | vlm | 0.55 |
| GPT-4omini API |  | Correct | 57.1* |  |  |  | vlm | 0.55 |
| Claude3-haiku Web |  | Correct | 46.5* |  |  |  | vlm | 0.55 |
| Claude3-Haiku API |  | Correct | 51.2* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet Web |  | Correct | 57.1 |  |  |  | vlm | 0.8 |
| Claude3-Sonnet API |  | Correct | 52.5 |  |  |  | vlm | 0.8 |
| Claude3-Opus Web |  | Correct | 66 |  |  |  | vlm | 0.8 |
| Claude3-Opus API |  | Correct | 70 |  |  |  | vlm | 0.8 |
| Claude3.5-Sonnet API |  | Correct | 75.6 |  |  |  | vlm | 0.8 |
| Mistral2-7b Poe |  | Correct | 43.8* |  |  |  | vlm | 0.55 |
| Mistral2-7b-Q8 Local |  | Correct | 40.4* |  |  |  | vlm | 0.55 |
| Mistral Large Poe |  | Correct | 61.8* |  |  |  | vlm | 0.55 |
| Mixtral-8x7b Poe |  | Correct | 57.1* |  |  |  | vlm | 0.55 |
| Gemini Web |  | Correct | 43.8 |  |  |  | vlm | 0.8 |
| GeminiAdvanced Web |  | Correct | 52.1* |  |  |  | vlm | 0.55 |
| Gemma2-9b Poe |  | Correct | 47.9* |  |  |  | vlm | 0.55 |
| Gemma2-9b-Q8 Local |  | Correct | 47.9* |  |  |  | vlm | 0.55 |
| Gemma2-27b Poe |  | Correct | 54* |  |  |  | vlm | 0.55 |
| Phi3-3b-Q16 Local |  | Correct | 43.8 |  |  |  | vlm | 0.8 |
| Phi3-14b-Q6 Local |  | Correct | 52* |  |  |  | vlm | 0.55 |

- Note: Values read by eye, approximate.
- Note: Llama-family bars (Correct roughly 28-62%) not tabulated.

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Not read, or uncertain

- In all five charts the ZOP, EOP, NOP, Error and Incorrect segments are not tabulated. Incorrect is roughly 100 minus Correct minus small segments, and small segments are visible only on a few bars (e.g. Gemini Web).
- Llama-family bars (about 14 per chart: Llama2, meditron, Llama3, OpenBioLLM, Llama3.1) are not tabulated because labels are illegible.
- Printed percentage labels on bars are largely unreadable, so values are estimated from bar heights.

## Checks

- the rule splitter finds 1 chart(s), the model lists 5: cut between the listed charts
- panel 1: 13 of 24 categories are not printed in the figure (e.g. 'Claude3-Haiku API')
- panel 1: stacked segments do not sum to 100: GPT-3.5 Web sums to 56.4; GPT-3.5 API sums to 52.7; GPT-4 Web sums to 67; GPT-4 API sums to 60; GPT-4o API sums to 74.5
- panel 2: 13 of 24 categories are not printed in the figure (e.g. 'Claude3-Haiku API')
- panel 2: stacked segments do not sum to 100: GPT-3.5 Web sums to 51.2; GPT-3.5 API sums to 40.7; GPT-4 Web sums to 73.2; GPT-4 API sums to 76; GPT-4o API sums to 79.7
- panel 3: 13 of 24 categories are not printed in the figure (e.g. 'Claude3-Haiku API')
- panel 3: stacked segments do not sum to 100: GPT-3.5 Web sums to 47.4; GPT-3.5 API sums to 44; GPT-4 Web sums to 66; GPT-4 API sums to 65; GPT-4o API sums to 73.9
- panel 4: 13 of 24 categories are not printed in the figure (e.g. 'Claude3-Haiku API')
- panel 4: stacked segments do not sum to 100: GPT-3.5 Web sums to 33.3; GPT-3.5 API sums to 0; GPT-4omini API sums to 33.3; Claude3-haiku Web sums to 66.7; Claude3-Haiku API sums to 66.7
- panel 5: 13 of 24 categories are not printed in the figure (e.g. 'Claude3-Haiku API')
- panel 5: stacked segments do not sum to 100: GPT-3.5 Web sums to 49.8; GPT-3.5 API sums to 50; GPT-4 Web sums to 64.5; GPT-4 API sums to 67; GPT-4o API sums to 73.7

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-181112_cloud_anthropic-claude-sonnet-5.5.json`.
