# Figure data: pictures_2 of Public-test-manuscript (page 16)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3. Impact of output structure (a), temperature (b), Max_token (c), and prompt engineering (d) on LLM MCQ performance .

**What the figure shows (model):** Four-panel figure showing how output structure (a), temperature (b), max token setting (c) and prompt engineering technique (d) affect LLM multiple-choice question accuracy (%).

## Chart 1: a (grouped_bar, horizontal)

x axis "Accuracy (%)" [%] linear 0 to 70; y axis "Response Generation" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| LangChain |  | GPT3-API | 40 |  |  |  | vlm | 0.8 |
| LangChain |  | GPT4-API | 66.7 |  |  |  | vlm | 0.8 |
| Function Call |  | GPT3-API | 43.3 |  |  |  | vlm | 0.8 |
| Function Call |  | GPT4-API | 68.3 |  |  |  | vlm | 0.8 |
| Standard Output |  | GPT3-API | 40 |  |  |  | vlm | 0.8 |
| Standard Output |  | GPT4-API | 55 |  |  |  | vlm | 0.8 |

## Chart 2: b (forest, horizontal)

x axis "Accuracy (%)" [%] linear 38 to 52; y axis "Temperature" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Default (temp=1) |  | best prompt | 47.8 | 44.9 | 50.7 |  | vlm | 0.8 |
| Default (temp=1) |  | raw prompt |  | 44.9 | 51.6 |  | vlm | 0.8 |
| Default - 10% |  | best prompt |  | 38.4 | 51.5 |  | vlm | 0.8 |
| Default - 10% |  | raw prompt | 45 | 41.7 | 48.3 |  | vlm | 0.8 |
| Default - 40% |  | best prompt |  | 38.8 | 46.7 |  | vlm | 0.8 |
| Default - 40% |  | raw prompt | 42.8 | 41.6 | 43.9 |  | vlm | 0.8 |
| Default - 60% |  | best prompt | 45.6 | 42.7 | 48.4 |  | vlm | 0.8 |
| Default - 60% |  | raw prompt |  | 43 | 46.9 |  | vlm | 0.8 |
| Default - 90% |  | best prompt | 46.1 | 43.9 | 48.3 |  | vlm | 0.8 |
| Default - 90% |  | raw prompt |  | 44.5 | 46.7 |  | vlm | 0.8 |
| temp=0 |  | best prompt | 45.6 | 44.5 | 46.7 |  | vlm | 0.8 |
| temp=0 |  | raw prompt |  | 42.8 | 44.9 |  | vlm | 0.8 |

- Note: Raw prompt centre markers are mostly hidden behind the best prompt markers; only visible ones given.

## Chart 3: c (grouped_bar, horizontal)

x axis "Accuracy (%)" [%] linear 0 to 55; y axis "Experiment Setting" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Best Prompt (candidate 4) |  | MT: 512 | 46.7 |  |  |  | vlm | 0.8 |
| Best Prompt (candidate 4) |  | MT: 1024 | 46.7 |  |  |  | vlm | 0.8 |
| Best Prompt (candidate 4) |  | MT: 512plus | 45 |  |  |  | vlm | 0.8 |
| Give Model Time to Think |  | MT: 512 | 41.7 |  |  |  | vlm | 0.8 |
| Give Model Time to Think |  | MT: 1024 | 46.7 |  |  |  | vlm | 0.8 |
| Give Model Time to Think |  | MT: 512plus | 46.7 |  |  |  | vlm | 0.8 |
| Consensus Technique |  | MT: 512 | 38.3 |  |  |  | vlm | 0.8 |
| Consensus Technique |  | MT: 1024 | 43.3 |  |  |  | vlm | 0.8 |
| Consensus Technique |  | MT: 512plus | 43.3 |  |  |  | vlm | 0.8 |
| Expert Mimicry |  | MT: 512 | 45 |  |  |  | vlm | 0.8 |
| Expert Mimicry |  | MT: 1024 | 45 |  |  |  | vlm | 0.8 |
| Expert Mimicry |  | MT: 512plus | 45 |  |  |  | vlm | 0.8 |
| Confidence Scoring |  | MT: 512 | 46.7 |  |  |  | vlm | 0.8 |
| Confidence Scoring |  | MT: 1024 | 53.3 |  |  |  | vlm | 0.8 |
| Confidence Scoring |  | MT: 512plus | 53.3 |  |  |  | vlm | 0.8 |
| Contextual Embedding |  | MT: 512 | 48.3 |  |  |  | vlm | 0.8 |
| Contextual Embedding |  | MT: 1024 | 43.3 |  |  |  | vlm | 0.8 |
| Contextual Embedding |  | MT: 512plus | 43.3 |  |  |  | vlm | 0.8 |
| Comparative Analysis |  | MT: 512 | 41.7 |  |  |  | vlm | 0.8 |
| Comparative Analysis |  | MT: 1024 | 41.7 |  |  |  | vlm | 0.8 |
| Comparative Analysis |  | MT: 512plus | 41.7 |  |  |  | vlm | 0.8 |
| Elimination Method |  | MT: 512 | 41.7 |  |  |  | vlm | 0.8 |
| Elimination Method |  | MT: 1024 | 46.7 |  |  |  | vlm | 0.8 |
| Elimination Method |  | MT: 512plus | 46.7 |  |  |  | vlm | 0.8 |
| Answer Justification |  | MT: 512 | 48.3 |  |  |  | vlm | 0.8 |
| Answer Justification |  | MT: 1024 | 50 |  |  |  | vlm | 0.8 |
| Answer Justification |  | MT: 512plus | 50 |  |  |  | vlm | 0.8 |
| Chain of Thought |  | MT: 512 | 52.5 |  |  |  | vlm | 0.8 |
| Chain of Thought |  | MT: 1024 | 45 |  |  |  | vlm | 0.8 |
| Chain of Thought |  | MT: 512plus | 45 |  |  |  | vlm | 0.8 |
| Option Analysis |  | MT: 512 | 45 |  |  |  | vlm | 0.8 |
| Option Analysis |  | MT: 1024 | 43.3 |  |  |  | vlm | 0.8 |
| Option Analysis |  | MT: 512plus | 43.3 |  |  |  | vlm | 0.8 |
| Direct Question |  | MT: 512 | 50 |  |  |  | vlm | 0.8 |
| Direct Question |  | MT: 1024 | 48.3 |  |  |  | vlm | 0.8 |
| Direct Question |  | MT: 512plus | 48.3 |  |  |  | vlm | 0.8 |
| Raw |  | MT: 512 | 43.3 |  |  |  | vlm | 0.8 |
| Raw |  | MT: 1024 | 41.7 |  |  |  | vlm | 0.8 |
| Raw |  | MT: 512plus | 43.3 |  |  |  | vlm | 0.8 |

- Note: Bars overlap; the 1024 bar is partly hidden behind the 512 bar in some rows, so its values are estimates.

## Chart 4: d (forest, horizontal)

x axis "Accuracy (%)" [%] linear 34.5 to 53; y axis "Function" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Candidate 6 |  |  | 48.9 | 48.8 | 49 |  | vlm | 0.8 |
| Candidate 5 |  |  | 47.8 | 45.9 | 49.7 |  | vlm | 0.8 |
| Candidate 4 |  |  | 48.9 | 45.4 | 52.4 |  | vlm | 0.8 |
| Candidate 3 |  |  | 43.9 | 42.9 | 44.9 |  | vlm | 0.8 |
| Candidate 2 |  |  | 48.3 | 48.2 | 48.4 |  | vlm | 0.8 |
| Candidate 1 |  |  | 38.3 | 35 | 41.7 |  | vlm | 0.8 |
| Give Model Time to Think |  |  | 43.9 | 41.3 | 46.5 |  | vlm | 0.8 |
| Consensus Technique |  |  | 40 | 37.1 | 42.9 |  | vlm | 0.8 |
| Expert Mimicry |  |  | 45.6 | 44.6 | 46.5 |  | vlm | 0.8 |
| Confidence Scoring |  |  | 45.6 | 43.6 | 47.5 |  | vlm | 0.8 |
| Contextual Embedding |  |  | 46.7 | 43.8 | 49.6 |  | vlm | 0.8 |
| Comparative Analysis |  |  | 42.2 | 41.2 | 43.2 |  | vlm | 0.8 |
| Elimination Method |  |  | 44.2 | 40.6 | 47.7 |  | vlm | 0.8 |
| Answer Justification |  |  | 48.3 | 46.7 | 50 |  | vlm | 0.8 |
| Chain of Thought |  |  | 47.5 | 44 | 51 |  | vlm | 0.8 |
| Option Analysis |  |  | 43.9 | 42.9 | 44.9 |  | vlm | 0.8 |
| Direct Question |  |  | 48.3 | 46.7 | 50 |  | vlm | 0.8 |
| Raw |  |  | 43.9 | 42.9 | 44.9 |  | vlm | 0.8 |

## Checks

- 4 charts found by their tick labels

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-181112_cloud_anthropic-claude-sonnet-5.5.json`.
