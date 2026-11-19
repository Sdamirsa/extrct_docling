# Figure data: pictures_11 of Public-test-manuscript (page 63)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Supplementary Figure S5. Performance Stratified by Question Subject

**What the figure shows (model):** Eleven small stacked-bar panels, one per clinical question subject (colon, endoscopy, esophagus, IBD, IBS, liver, miscellaneous, nutrition, pancreatico-biliary, small bowel, stomach). Each shows the percentage of answers per LLM that were Correct, 2OP, EOP, NOP, Error or Incorrect. Only the Correct segments for the first 13 models of the colon panel were read.

## Chart 1: Question type: COLON (N = 49) (stacked_bar, vertical)

x axis categorical; y axis "Percentage" [%] categorical 0 to 100.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| GPT-3.5 Web |  | Correct | 44.9* |  |  |  | vlm | 0.55 |
| GPT-3.5 API |  | Correct | 46.9 |  |  |  | vlm | 0.8 |
| GPT-4 Web |  | Correct | 55.1* |  |  |  | vlm | 0.55 |
| GPT-4 API |  | Correct | 67.3 |  |  |  | vlm | 0.8 |
| GPT-4o API |  | Correct | 75.5* |  |  |  | vlm | 0.55 |
| GPT-4omini API |  | Correct | 49* |  |  |  | vlm | 0.55 |
| Claude3-Haiku Web |  | Correct | 49* |  |  |  | vlm | 0.55 |
| Claude3-Haiku API |  | Correct | 55.1* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet Web |  | Correct | 59.2* |  |  |  | vlm | 0.55 |
| Claude3-Sonnet API |  | Correct | 57.1* |  |  |  | vlm | 0.55 |
| Claude3-Opus Web |  | Correct | 57.1* |  |  |  | vlm | 0.55 |
| Claude3-Opus API |  | Correct | 67.3* |  |  |  | vlm | 0.55 |
| Claude3.5-Sonnet API |  | Correct | 69.4* |  |  |  | vlm | 0.55 |

- Note: Values are estimated from small, hard-to-read labels.
- Note: Models are grouped GPT, Claude, Mistral, Llama, Gemini/Gemma, Phi-3.

## Chart 2: Question type: ENDOSCOPY (N = 26) (stacked_bar, vertical)

x axis categorical.

No values read.

- Note: Not read.

## Chart 3: Question type: ESOPHAGUS (N = 36) (stacked_bar, vertical)

x axis categorical; y axis log 20 to 80.

No values read.

- Note: Not read.

## Chart 4: Question type: IBD (N = 30) (stacked_bar, vertical)

x axis categorical.

No values read.

- Note: Not read.

## Chart 5: Question type: IBS (N = 14) (stacked_bar, vertical)

x axis categorical; y axis linear 20 to 80.

No values read.

- Note: Not read.

## Chart 6: Question type: LIVER (N = 52) (stacked_bar, vertical)

x axis categorical.

No values read.

- Note: Not read.

## Chart 7: Question type: MISCELLANEOUS (N = 19) (stacked_bar, vertical)

x axis categorical; y axis linear 21 to 100.

No values read.

- Note: Not read.

## Chart 8: Question type: NUTRITION (N = 3) (stacked_bar, vertical)

x axis categorical; y axis linear 20 to 100.

No values read.

- Note: Not read. With N = 3 the Correct values are only 0, 33.3, 66.7 or 100.

## Chart 9: Question type: PANCREATICO-BILIARY (N = 31) (stacked_bar, vertical)

x axis categorical; y axis linear 21 to 100.

No values read.

- Note: Not read.

## Chart 10: Question type: SMALL BOWEL (N = 22) (stacked_bar, vertical)

x axis categorical; y axis linear 20 to 100.

No values read.

- Note: Not read.

## Chart 11: Question type: STOMACH (N = 17) (stacked_bar, vertical)

x axis categorical; y axis linear 7 to 100.

No values read.

- Note: Not read.

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Not read, or uncertain

- Colon panel: Correct values for the Mistral, Llama, Gemini/Gemma and Phi-3 bars (about 22 bars) were not read.
- Colon panel: the 2OP, EOP, NOP, Error and Incorrect segments of every bar were not read.
- Panels 2-11 (about 35 bars each, all six segments per bar) were not read, because the labels are too small to read reliably.

## Checks

- the rule splitter finds 7 chart(s), the model lists 11: cut between the listed charts
- panel 1: 11 of 13 categories are not printed in the figure (e.g. 'Claude3-Haiku API')
- panel 1: stacked segments do not sum to 100: GPT-3.5 Web sums to 44.9; GPT-3.5 API sums to 46.9; GPT-4 Web sums to 55.1; GPT-4 API sums to 67.3; GPT-4o API sums to 75.5

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-182940_cloud_anthropic-claude-sonnet-5.5.json`.
