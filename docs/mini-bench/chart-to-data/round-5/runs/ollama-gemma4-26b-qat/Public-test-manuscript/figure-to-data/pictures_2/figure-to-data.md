# Figure data: pictures_2 of Public-test-manuscript (page 16)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3. Impact of output structure (a), temperature (b), Max_token (c), and prompt engineering (d) on LLM MCQ performance .

**What the figure shows (model):** This figure presents a comparative analysis of different LLM response generation methods, temperature settings, experiment settings, and functions across various accuracy metrics.

## Chart 1: a (bar, horizontal)

x axis "Accuracy (%)" linear 0 to 70; y axis "Response Generation" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Standard Output |  | GPT3-API | 39.9431 |  |  |  | raster | 0.8 |
| Standard Output |  | GPT4-API | 54.9715 |  |  |  | raster | 0.8 |
| Function Call |  | GPT3-API | 43.2827 |  |  |  | raster | 0.8 |
| Function Call |  | GPT4-API | 43.2827 |  |  |  | raster | 0.8 |
| LangChain |  | GPT3-API | 39.9431 |  |  |  | raster | 0.8 |
| LangChain |  | GPT4-API | 39.9431 |  |  |  | raster | 0.8 |

## Chart 2: b (forest, horizontal)

x axis "Accuracy (%)" linear 38 to 52; y axis "Temperature" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Default (temp=1) |  | best prompt | 48.0194 |  |  |  | raster | 0.7 |
| Default (temp=1) |  | raw prompt | 51.5595 |  |  |  | raster | 0.7 |
| Default - 10% |  | best prompt | 44* |  |  |  | vlm | 0.5 |
| Default - 10% |  | raw prompt | 51.5595 |  |  |  | raster | 0.7 |
| Default - 40% |  | best prompt | 42.6053 |  |  |  | raster | 0.7 |
| Default - 40% |  | raw prompt | 46* |  |  |  | vlm | 0.5 |
| Default - 60% |  | best prompt | 45.9995 |  |  |  | raster | 0.7 |
| Default - 60% |  | raw prompt | 48.0194 |  |  |  | raster | 0.7 |
| Default - 90% |  | best prompt | 44* |  |  |  | vlm | 0.5 |
| Default - 90% |  | raw prompt | 46* |  |  |  | vlm | 0.5 |
| temp=0 |  | best prompt | 45.9995 |  |  |  | raster | 0.7 |
| temp=0 |  | raw prompt | 45.9995 |  |  |  | raster | 0.7 |

- Note: pointed position and read value disagree, read value kept: Default - 10%, Default - 40%, Default - 90%, Default - 90%

## Chart 3 (bar, horizontal)

x axis "Accuracy (%)" linear 0 to 50; y axis "Experiment Setting" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Best Prompt (candidate 4) |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Best Prompt (candidate 4) |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Best Prompt (candidate 4) |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Give Model Time to Think |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Give Model Time to Think |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Give Model Time to Think |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Consensus Technique |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Consensus Technique |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Consensus Technique |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Expert Mimicry |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Expert Mimicry |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Expert Mimicry |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Confidence Scoring |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Confidence Scoring |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Confidence Scoring |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Contextual Embedding |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Contextual Embedding |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Contextual Embedding |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Comparative Analysis |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Comparative Analysis |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Comparative Analysis |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Elimination Method |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Elimination Method |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Elimination Method |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Answer Justification |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Answer Justification |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Answer Justification |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Chain of Thought |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Chain of Thought |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Chain of Thought |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Option Analysis |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Option Analysis |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Option Analysis |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Direct Question |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Direct Question |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Direct Question |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |
| Raw |  | MT: 512 | 19.9052 |  |  |  | raster | 0.8 |
| Raw |  | MT: 1024 | 19.9052 |  |  |  | raster | 0.8 |
| Raw |  | MT: 512plus | 19.9052 |  |  |  | raster | 0.8 |

## Chart 4: d (forest, horizontal)

x axis "Accuracy (%)" linear 35 to 52.5; y axis "Function" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Candidate 6 |  |  | 47.7795 |  |  |  | raster | 0.7 |
| Candidate 5 |  |  | 47.7795 | 45.4138 | 50.1452 |  | raster | 0.7 |
| Candidate 4 |  |  | 48.7148 | 45.4138 | 52.5109 |  | raster | 0.7 |
| Candidate 3 |  |  | 44.0384 | 43.0756 | 44.9737 |  | raster | 0.7 |
| Candidate 2 |  |  | 47.7795 |  |  |  | raster | 0.7 |
| Candidate 1 |  |  | 37.1613 | 35.3182 | 38.9768 |  | raster | 0.7 |
| Give Model Time to Think |  |  | 44.0384 | 40.3523 | 46.129 |  | raster | 0.7 |
| Consensus Technique |  |  | 39.4995 | 37.6839 | 41.3426 |  | raster | 0.7 |
| Expert Mimicry |  |  | 45.4138 | 44.1209 | 46.6792 |  | raster | 0.7 |
| Confidence Scoring |  |  | 45.4138 | 44.1209 | 46.6792 |  | raster | 0.7 |
| Contextual Embedding |  |  | 46.129 | 43.1856 | 49.0724 |  | raster | 0.7 |
| Comparative Analysis |  |  | 43.0756 | 42.1678 | 44.0384 |  | raster | 0.7 |
| Elimination Method |  |  | 44.0384 | 40.3523 | 46.129 |  | raster | 0.7 |
| Answer Justification |  |  | 47.0643 |  |  |  | raster | 0.7 |
| Chain of Thought |  |  | 47.0643 | 44.1209 | 50.7229 |  | raster | 0.7 |
| Option Analysis |  |  | 44.0384 | 43.1856 | 44.9186 |  | raster | 0.7 |
| Direct Question |  |  | 47.0643 |  |  |  | raster | 0.7 |
| Raw |  |  | 44.0384 | 43.1856 | 44.9186 |  | raster | 0.7 |

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Checks

- 4 charts found by their tick labels

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-181423_ollama_gemma4-26b-a4b-it-qat.json`.
