# Figure data: pictures_12 of Public-test-manuscript (page 64)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-20, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Supplementary Figure S6. Performance stratified by patient care phase

**What the figure shows (model):** Five stacked bar charts showing, for each language model and access mode, the percentage of answers that were Correct, ZOP, EOP, NOP, Error or Incorrect, split by patient care phase (Complication, Diagnosis, Investigation, Pathophysiology, Treatment).

**No data read:** No individual bar segments were extracted for any of the five charts, because the labels are too small and blurred to read reliably. Each chart has about 40 bars with 6 segments each.

## Chart 1: Question type: Complication (N = 55) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] log 0 to 100.

No values read.

- Note: About 40 bars, one per model. Bars are mostly Correct (green) and Incorrect (red), with small grey and orange segments.
- Note: Correct values printed on the bars range from about 24% to 75%. Examples: GPT-4o API about 74.5%, Claude3.5-Sonnet API about 78%, Llama3.1-405b Poe about 56.6%.
- Note: Models are grouped by family: GPT, Claude, Mistral, Llama, Gemini and Gemma, Phi3.

## Chart 2: Question type: Diagnosis (N = 123) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

No values read.

- Note: Correct values range from about 25% to 80%. GPT-4o API is about 80% and Claude3.5-Sonnet API about 78%.

## Chart 3: Question type: Investigation (N = 211) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

No values read.

- Note: Correct values range from about 17% to 74%. GPT-4o API is about 74%.

## Chart 4: Question type: Pathophysiology (N = 3) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

No values read.

- Note: With N = 3, Correct takes only the values 0, 33.3, 66.7 and 100%.

## Chart 5: Question type: Treatment (N = 217) (stacked_bar, vertical)

x axis "Model" categorical; y axis "Percentage" [%] linear 0 to 100.

No values read.

- Note: Correct values range from about 29% to 76%. Claude3.5-Sonnet API is about 75.6% and GPT-4o API about 73.7%.

## Not read, or uncertain

- The printed percentage labels on the bars are mostly illegible.

## Checks

- the rule splitter finds 1 chart(s), the model lists 5: cut between the listed charts

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261120-162816_cloud_anthropic-claude-sonnet-5.5.json`.
