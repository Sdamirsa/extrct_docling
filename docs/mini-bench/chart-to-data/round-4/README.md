# Round 4: one paper through the whole pipeline, four ways

2026-11-19. Rounds 1 to 3 measured the reading of prepared figures. This
round runs the command a user types, `amir-batch <pdf> --figure-data
<method>`, four times on one 68-page paper (the showcase paper), and looks
at what each run takes, costs and leaves in its bundle. What was found and
changed on the way is in [`LOG.md`](LOG.md).

## Answer

**The step works inside the pipeline with all four setups**: one command
per run, exit code 0, and each bundle carries the readings at its figures,
in its chunks and in its page viewer. Getting there took four changes to
the pipeline and showed one defect in how a figure is captured, which is
fixed.

**No method reads this paper's figures completely, and the order of the
methods is not that of round 3.** On the six main figures (573 values):

| | `ollama`, Gemma 4 26B | `cloud`, Sonnet 5.5 | `cloud`, Gemini 3.8 Flash | `agent`, Sonnet 5.5 |
|---|---|---|---|---|
| The whole command | 39 min | **18 min** | 42 min | 27 min |
| of it, reading the 12 figures | 1,609 s | **358 s** | 1,809 s | 854 s |
| Cost | local | **0.91 USD** | 1.42 USD | 2.97 USD |
| Values returned, all 12 figures | 1,061 | 867 | 1,529 | **1,970** |
| Main six: values right under the right name, of 573 | 83 | 408 | **554** | 251 |
| Judges: figures correct / partial, of 6 | 0 / 6 | 4 / 2 | 4 / 2 | 3 / 3 |
| Judges: usable as it is / would mislead | 0 / 3 | **5** / 0 | 4 / 0 | **5** / 0 |
| Five dense figures: sampled bars right, of 60 | 8 | 38 | 55 | **60** |

- **`cloud` with Sonnet 5.5** is the fastest and cheapest way out of the
  machine, and nothing it returned is further than 3.1 % of the axis from
  the truth. It left out most small segments of the largest stacked-bar
  chart and most of two dense supplementary figures, and said so.
- **`cloud` with Gemini 3.8 Flash** returned the most on the main figures,
  every value of both stacked-bar charts included. It put small segments
  under the wrong class there, which a count within 5 % of the axis does
  not see and its judge did: two of six figures not usable as they are. It
  is the slowest of the four.
- **`agent`** returned the most overall, and what it returned is right:
  its judge found each of its 268 values on the main figures within 1.6 %
  of the axis, and all 60 sampled bars of the dense figures are right. On
  the two stacked-bar charts it recorded the printed numbers only and left
  305 values out. It costs more than three times the Sonnet call.
- **`ollama`** reads printed numbers and names well and mismeasures bars
  and segments: none of the six figures usable, three would mislead.

On Figure 6 every run had the printed numbers right and none could know
which point is which: its axis labels had been lost on the way to the
reader (see below). That figure counts as wrong by name in the table.

One paper does not settle which cloud model to prefer: in round 3, on 15
figures of 11 papers, Sonnet's single call returned every value and
Gemini's misread a stacked chart. The default stays Sonnet 5.5.

## The paper

`showcase/Public-test-manuscript.pdf`: 68 pages, 15 pictures, of which the
step takes 12 as chart candidates ([`testset.json`](testset.json)).

- **Six main figures** (S02 to S08): bars, interval plots, two stacked-bar
  charts of 37 and 24 bars, points with printed labels, four line panels, a
  confusion matrix. 573 values in 13 charts, with a truth file each
  ([`truth/`](truth/)).
- **Five dense supplementary figures** (S10 to S14): 26 panels of 37
  stacked bars, 5,772 segment values, of which 955 are printed, in three of
  the figures too small to read. A sample of 60 bars fixed by rule stands
  in for a truth ([`truth-sample/`](truth-sample/)).
- **One strip figure** (S09): a coloured cell per model and question. All
  four runs declined it.

Two of the main figures (S04, S06) are in the five-figure smoke set the
local engine was first built on. No figure of this paper is in the bench
of rounds 1 to 3, on which the cloud and agent methods were built.

## What each run leaves in its bundle

| | `ollama` | `cloud`, Sonnet | `cloud`, Gemini | `agent` |
|---|---|---|---|---|
| Figures read / no data / not read | 10 / 0 / 2 | 10 / 1 / 1 | 11 / 1 / 0 | 11 / 1 / 0 |
| A table at the figure | 7 | 9 | 11 | 9 |
| A pointer only (values under the confidence threshold) | 3 | 1 | 0 | 2 |
| Chunks, of them with figure data | 164, 10 | 171, 10 | 189, 11 | 172, 11 |
| Bundle check | OK | OK | OK | OK |

Every bundle has `figure-to-data/` with one folder per figure (what the
reader was given, what it read, how) and the run's record; the note that a
model read the numbers and the table at the figure in the markdown, the
HTML and the chunks; a `figure_to_data` block in `run.json`; the counts in
`check.json`; and, new in this round, the reading in the page viewer.

## What changed in the pipeline

- **The page viewer shows the readings.** `preview.html` and
  `preview.embedded.html` are rebuilt by the step from the bundle's files:
  a `data` tag on the figure's box, in its side panel the note, the table
  and a link to the full reading, a count in the header.
- **The batch summary is read again after the step**, so its `check`
  column (`charts 9/10/12`: shown, read, candidates) and the exit code
  reflect what the step did.
- **`--figure-data-ollama-url`** on `amir-batch`.
- **An end-to-end test** of `amir-batch --figure-data` for the four setups
  (`tests/test_engines/test_figure_data_batch.py`): a real conversion of a
  synthetic chart PDF, the models replaced at the process boundary by a
  local HTTP server and a stand-in `claude` executable that drives the
  agent's real tool server.
- **A figure's embedded image is taken with its transparency mask.**
  Figure 6 reached every reader with black where the page is white, its
  axis labels gone. Fixed after the runs; read again from the corrected
  image, all four methods have all 13 of its valued points right under the
  right year or date ([`after-fix/`](after-fix/)). The four bundles hold
  that figure as first read.
- **Ticks that lie on a line in value are a linear axis** (the years 2021
  to 2023 had been fitted as a log scale).

## What the paper showed about the step

- **The chart splitter was wrong on six of the eleven chart figures**: one
  chart of 37 bars cut in two, four panels cut in six, a grid of eleven
  panels found as seven. The cloud models and the agent saw the whole
  figure and said so; the local engine read what it was given.
- **Stacked bars with small unlabelled segments got four different
  answers**: every segment with some under the wrong class (Gemini), every
  segment of one chart and two classes of the other (Sonnet), the printed
  share only (agent), the bar's end for the last class (local).
- **Every method named what it left out**, with one exception the local
  run's judge found.
- **The bench's scorer undercounts on this paper**: it pairs charts by
  their boxes and names that are almost alike. The numbers above pair by
  printed name with the charts put where the truth has them; the scorer's
  own count is in [`metrics/pipeline.md`](metrics/pipeline.md) beside
  them, and the four judges came to the by-name count on their own.

## Limits

- One paper, by the maintainer, with unusually dense figures.
- The truth and the judges are a frontier model's work, as in rounds 1 to
  3; two of the six truth files could be checked against an independent
  earlier one and agree.
- "Within 5 % of the axis" is lenient for segments a point or two wide.
- Figure 6 was judged as first read, under the defect, and the judges read
  that rule differently; the reading after the fix is the better evidence.
- The agent's cost is what the Claude Code CLI reports for the login it
  ran under.
- Not run: a second pass of the four commands with the fixed capture
  (about 2 hours and 5 USD).

## Files

| | |
|---|---|
| [`LOG.md`](LOG.md) | what was found and changed, in order (F28 to F44) |
| [`config.json`](config.json) | commands, models, versions, limits, costs |
| [`testset.json`](testset.json) | the 12 chart candidates |
| [`truth/`](truth/), [`truth-sample/`](truth-sample/) | the truth of six figures, the sample of five, their prompts |
| `runs/<label>/` | each run's readings and run records (no figure images); `timing.json`; the agent's tool audit |
| [`after-fix/`](after-fix/) | Figure 6 read again after the fix |
| [`metrics/pipeline.md`](metrics/pipeline.md), `pipeline.json` | time, cost, what reached the bundle, the three counts, the sample, agreement between runs |
| `metrics/summary.md`, `per_figure.csv` | the same runs through the analysis of rounds 1 to 3 |
| [`judge/`](judge/) | the judges' prompt, files and summary |
| `report-page/` | builds the two private pages of the round: the results (`build.py`) and the defects found, fixed and open (`build_defects.py`) |

Not in the repository: the four bundles and the comparison page built
beside them (`samples/round-4-showcase/`), and the figure images.

## Repeat it

```bash
# the four runs, one after the other (about 2 hours; the cloud runs need
# OPENROUTER_API_KEY, the agent run the Claude Code CLI)
OUT=samples/round-4-showcase docs/mini-bench/chart-to-data/scripts/run_round4.sh

# bring the readings into this folder, score and compare
for label in ollama-gemma4-26b-qat cloud-sonnet-5-5 cloud-gemini-3-8-flash agent-sonnet-5-5; do
  BENCH_ROUND=round-4 uv run --no-sync python \
    docs/mini-bench/chart-to-data/scripts/collect_round3.py samples/round-4-showcase/$label $label --audit
done
cd docs/mini-bench/chart-to-data/scripts
BENCH_ROUND=round-4 uv run --no-sync python analyze.py
BENCH_ROUND=round-4 uv run --no-sync python judge_inputs.py     # then the judges, judge/PROMPT.md
BENCH_ROUND=round-4 uv run --no-sync python judge_summary.py
BENCH_ROUND=round-4 uv run --no-sync python compare_bundles.py ../../../../samples/round-4-showcase
```

The last command also writes `samples/round-4-showcase/comparison.html`:
each figure beside what the four runs read from it.
