# Figure data: pictures_2 of Public-test-manuscript (page 16)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3. Impact of output structure (a), temperature (b), Max_token (c), and prompt engineering (d) on LLM MCQ performance .

**What the figure shows (model):** Four-panel figure showing LLM multiple-choice-question accuracy under different output structures (a), temperatures (b), max-token settings (c) and prompt-engineering techniques (d).

## Chart 1: Impact of output structure (grouped_bar, horizontal)

x axis "Accuracy (%)" [%] linear 0 to 70; y axis "Response Generation" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| LangChain |  | GPT3-API | 40 |  |  |  | agent | 0.8 |
| LangChain |  | GPT4-API | 66.7 |  |  |  | agent | 0.8 |
| Function Call |  | GPT3-API | 43.3 |  |  |  | agent | 0.8 |
| Function Call |  | GPT4-API | 68.3 |  |  |  | agent | 0.8 |
| Standard Output |  | GPT3-API | 40 |  |  |  | agent | 0.8 |
| Standard Output |  | GPT4-API | 55 |  |  |  | agent | 0.8 |

## Chart 2: Impact of temperature (forest, horizontal)

x axis "Accuracy (%)" [%] linear 38 to 52; y axis "Temperature" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Default (temp=1) |  | best prompt | 47.8 | 44.9 | 50.65 |  | agent | 0.8 |
| Default (temp=1) |  | raw prompt | 48.3 | 45 | 51.6 |  | agent | 0.8 |
| Default - 10% |  | best prompt | 45 | 38.45 | 51.5 |  | agent | 0.8 |
| Default - 10% |  | raw prompt | 45 | 41.7 | 48.25 |  | agent | 0.8 |
| Default - 40% |  | best prompt | 42.76 | 38.86 | 46.66 |  | agent | 0.8 |
| Default - 40% |  | raw prompt | 42.76 | 41.66 | 43.86 |  | agent | 0.8 |
| Default - 60% |  | best prompt | 45.5 | 42.65 | 48.4 |  | agent | 0.8 |
| Default - 60% |  | raw prompt | 45 | 43.07 | 46.9 |  | agent | 0.8 |
| Default - 90% |  | best prompt | 46.1 | 43.9 | 48.25 |  | agent | 0.8 |
| Default - 90% |  | raw prompt | 45.5 | 44.4 | 46.6 |  | agent | 0.8 |
| temp=0 |  | best prompt | 45.5 | 44.45 | 46.6 |  | agent | 0.8 |
| temp=0 |  | raw prompt | 43.86 | 42.78 | 44.95 |  | agent | 0.8 |

- Note: Where the two series' error bars overlap, which cap belongs to which series was inferred from colour and symmetry about the centre.

## Chart 3: Impact of Max_token (grouped_bar, horizontal)

x axis "Accuracy (%)" [%] linear 0 to 56; y axis "Experiment Setting" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Best Prompt (candidate 4) |  | MT: 512 | 46.7 |  |  |  | agent | 0.8 |
| Best Prompt (candidate 4) |  | MT: 1024 | 45 |  |  |  | agent | 0.8 |
| Best Prompt (candidate 4) |  | MT: 512plus | 45 |  |  |  | agent | 0.8 |
| Give Model Time to Think |  | MT: 512 | 41.7 |  |  |  | agent | 0.8 |
| Give Model Time to Think |  | MT: 1024 | 46.7 |  |  |  | agent | 0.8 |
| Give Model Time to Think |  | MT: 512plus | 46.7 |  |  |  | agent | 0.8 |
| Consensus Technique |  | MT: 512 | 38.3 |  |  |  | agent | 0.8 |
| Consensus Technique |  | MT: 1024 | 43.3 |  |  |  | agent | 0.8 |
| Consensus Technique |  | MT: 512plus | 43.3 |  |  |  | agent | 0.8 |
| Expert Mimicry |  | MT: 512 | 45 |  |  |  | agent | 0.8 |
| Expert Mimicry |  | MT: 1024 | 45 |  |  |  | agent | 0.8 |
| Expert Mimicry |  | MT: 512plus | 45 |  |  |  | agent | 0.8 |
| Confidence Scoring |  | MT: 512 | 46.7 |  |  |  | agent | 0.8 |
| Confidence Scoring |  | MT: 1024 | 53.4 |  |  |  | agent | 0.8 |
| Confidence Scoring |  | MT: 512plus | 53.4 |  |  |  | agent | 0.8 |
| Contextual Embedding |  | MT: 512 | 48.3 |  |  |  | agent | 0.8 |
| Contextual Embedding |  | MT: 1024 | 43.3 |  |  |  | agent | 0.8 |
| Contextual Embedding |  | MT: 512plus | 43.3 |  |  |  | agent | 0.8 |
| Comparative Analysis |  | MT: 512 | 41.7 |  |  |  | agent | 0.8 |
| Comparative Analysis |  | MT: 1024 | 41.7 |  |  |  | agent | 0.8 |
| Comparative Analysis |  | MT: 512plus | 41.7 |  |  |  | agent | 0.8 |
| Elimination Method |  | MT: 512 | 41.7 |  |  |  | agent | 0.8 |
| Elimination Method |  | MT: 1024 | 46.7 |  |  |  | agent | 0.8 |
| Elimination Method |  | MT: 512plus | 46.7 |  |  |  | agent | 0.8 |
| Answer Justification |  | MT: 512 | 48.3 |  |  |  | agent | 0.8 |
| Answer Justification |  | MT: 1024 | 50 |  |  |  | agent | 0.8 |
| Answer Justification |  | MT: 512plus | 50 |  |  |  | agent | 0.8 |
| Chain of Thought |  | MT: 512 | 52.6 |  |  |  | agent | 0.8 |
| Chain of Thought |  | MT: 1024 | 45 |  |  |  | agent | 0.8 |
| Chain of Thought |  | MT: 512plus | 45 |  |  |  | agent | 0.8 |
| Option Analysis |  | MT: 512 | 45 |  |  |  | agent | 0.8 |
| Option Analysis |  | MT: 1024 | 43.3 |  |  |  | agent | 0.8 |
| Option Analysis |  | MT: 512plus | 43.3 |  |  |  | agent | 0.8 |
| Direct Question |  | MT: 512 | 50 |  |  |  | agent | 0.8 |
| Direct Question |  | MT: 1024 | 48.3 |  |  |  | agent | 0.8 |
| Direct Question |  | MT: 512plus | 48.3 |  |  |  | agent | 0.8 |
| Raw |  | MT: 512 | 43.3 |  |  |  | agent | 0.8 |
| Raw |  | MT: 1024 | 41.7 |  |  |  | agent | 0.8 |
| Raw |  | MT: 512plus | 43.3 |  |  |  | agent | 0.8 |

## Chart 4: Impact of prompt engineering (forest, horizontal)

x axis "Accuracy (%)" [%] linear 34.5 to 53; y axis "Function" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Candidate 6 |  |  | 48.85 | 48.85 | 48.85 |  | agent | 0.8 |
| Candidate 5 |  |  | 47.7 | 45.8 | 49.7 |  | agent | 0.8 |
| Candidate 4 |  |  | 48.85 | 45.4 | 52.3 |  | agent | 0.8 |
| Candidate 3 |  |  | 43.9 | 42.9 | 44.8 |  | agent | 0.8 |
| Candidate 2 |  |  | 48.3 | 48.3 | 48.3 |  | agent | 0.8 |
| Candidate 1 |  |  | 38.3 | 35 | 41.7 |  | agent | 0.8 |
| Give Model Time to Think |  |  | 43.9 | 41.3 | 46.4 |  | agent | 0.8 |
| Consensus Technique |  |  | 40 | 37.1 | 42.9 |  | agent | 0.8 |
| Expert Mimicry |  |  | 45.5 | 44.6 | 46.5 |  | agent | 0.8 |
| Confidence Scoring |  |  | 45.5 | 43.6 | 47.5 |  | agent | 0.8 |
| Contextual Embedding |  |  | 46.6 | 43.7 | 49.5 |  | agent | 0.8 |
| Comparative Analysis |  |  | 42.2 | 41.2 | 43.2 |  | agent | 0.8 |
| Elimination Method |  |  | 44.1 | 40.6 | 47.7 |  | agent | 0.8 |
| Answer Justification |  |  | 48.3 | 46.7 | 50 |  | agent | 0.8 |
| Chain of Thought |  |  | 47.5 | 43.95 | 51 |  | agent | 0.8 |
| Option Analysis |  |  | 43.9 | 42.9 | 44.8 |  | agent | 0.8 |
| Direct Question |  |  | 48.3 | 46.7 | 50 |  | agent | 0.8 |
| Raw |  |  | 43.9 | 42.9 | 44.8 |  | agent | 0.8 |

- Note: Candidates 6 and 2 show a dot without visible error bars; err_lo/err_hi set equal to the value.

## Not read, or uncertain

- All values were read from the axes, since the figure prints no numbers. Each is an estimate to about ±0.3 percentage points.
- Panel b: in rows where the best-prompt and raw-prompt error bars overlap, the cap assigned to each series is an inference from colour and symmetry about the centre.
- Panel b: the light raw-prompt centre markers are faint, so their positions are less certain than the dark ones.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-091835_agent_claude-sonnet-5-5.json`.
