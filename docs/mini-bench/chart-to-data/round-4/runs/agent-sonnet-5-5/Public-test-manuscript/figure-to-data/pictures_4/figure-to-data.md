# Figure data: pictures_4 of Public-test-manuscript (page 20)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 5. VLM Performance on Gastroenterology Multiple-Choice Questions with Image Data.

**What the figure shows (model):** Horizontal stacked bars of answer outcome percentages (Correct, 2OP, EOP, NOP, Error, Incorrect) for GPT4, Claude3 Opus, Claude3 Sonnet and GeminiAdvanced under four image conditions on gastroenterology multiple-choice questions.

## Chart 1: VLM Performance on Gastroenterology Multiple-Choice Questions with Image Data (stacked_bar, horizontal)

x axis "Percentage" linear 0 to 100; y axis "Model - condition" categorical.

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

- Note: Only the Correct (dark green) segment, printed as a label on each bar, is recorded. The other segments (2OP, EOP, NOP, Error, Incorrect) are not recorded; stacks do not sum to 100 because EOP (light grey) blends with the background and leaves gaps.
- Note: Significance marks vs the no-image reference, right of bars: GPT4 Web: ref, ns, ns, ns; GPT4 API: ref, ns, ns, ns; Claude3Opus Web: ref, ****, ns, **; Claude3Opus API: ref, ns, ns, *; Claude3Sonnet API: ref, ns, ****, ns; GeminiAdvanced Web: ref, ****, ns, ****.

## Not read, or uncertain

- The 2OP, EOP, NOP, Error and Incorrect segments of all 24 bars were not recorded. They have no printed labels and are small, so reading them would be estimates only. Only the printed Correct percentages were recorded.
- The significance marks (ref, ns, *, **, ****) to the right of each bar are written in the chart notes, not as data points.

## Checks

- panel 1: stacked segments do not sum to 100: GPT4 Web - no image sums to 65.2; GPT4 Web - LLM caption sums to 59.4; GPT4 Web - direct image sums to 68.1; GPT4 Web - human hint sums to 73.2; GPT4 API - no image sums to 68.8

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-091835_agent_claude-sonnet-5-5.json`.
