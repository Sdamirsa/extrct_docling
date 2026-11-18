# Chart-to-data mini bench, round 2

Round 1 ([`../README.md`](../README.md)) ended with every model failing the
same ways. Round 2 asks how much of that was the model and how much the
way our engine calls it.

Run on 2026-11-17: the same 15 figures, the same truth, the same scorer
and the same judge prompt, with a reworked engine around three of the
round-1 models, and one cloud model reading the images blind as a
reference. How the round got here, step by step, is in [`LOG.md`](LOG.md).

## Answer

Most of it was the call path. With it fixed, the recommended model reads
6 of the 10 data charts usably instead of 3, in two thirds of the time,
and no model returns values for a figure without data any more. It is
still not good enough to publish chart numbers unreviewed.

| | usable data charts (of 10) | figures that would mislead | no-data figures left alone (of 5) | values within 5 %, names ignored (of 560) | time for the 15 figures | one paper ¹ | GPU memory |
|---|---|---|---|---|---|---|---|
| Gemma 4 26B-A4B, 4-bit (QAT) | 3 → **6** | 4 → 2 | 5 → 5 | 55 → 188 | 535 s → **343 s** | 164 s → 24 s | 16 GB |
| Gemma 4 26B-A4B, 8-bit | 3 → 5 | 4 → 2 | 4 → 5 | 75 → 130 | 819 s → 533 s | 273 s → 32 s | 28 GB |
| Gemma 4 31B, 8-bit | 4 → 3 | 2 → 3 | 4 → 5 | 57 → 123 | 2,777 s → 2,461 s | 370 s → 148 s | 37 GB |
| Claude Sonnet 5.5, blind, by eye ² | 9 | 0 | 5 | 284 | 134 s | | cloud |

Round 1 on the left of each arrow, round 2 on the right. "Usable" and
"would mislead" (severity 3) are the judges' verdicts; the value count is
the automatic scorer with names ignored, an upper bound (see
[Limits](#limits)).
¹ The five chart candidates of one paper (four of them are not charts), on
top of a 379 s conversion.
² A reference, not a candidate: see [The cloud reference](#the-cloud-reference).

**Recommendation.** Gemma 4 26B-A4B, 4-bit QAT: the most usable charts of
the three, the fastest, 16 GB. Ship it as the fourth config with review,
not as an unattended source of numbers.

**The 31B is too slow for this job, not too weak.** It generates about six
tokens a second, so its replies run into the 120 s cut per call that round
2 introduced: it lost the printed-count bar chart it had right in round 1
(7 of 12 bars written when the cut came). See
[The 31B and the cut](#the-31b-and-the-cut).

## What was changed

Twelve findings, each confirmed with a probe before anything was changed,
and eleven changes to `docling/engines/figure_data/`. The full tables are
in [`LOG.md`](LOG.md); the six that matter most:

| What was wrong in round 1 | Now |
|---|---|
| The panel split is our code and cut only at white gaps at least 1 % of the image wide. Papers pack panels 4 px apart. Five ROC panels went to the model as one image under a prompt that said "one chart panel". | Charts are found by their tick labels and cut apart along the free band between them. 33 of 33 panels found (round 1: 20). |
| If the PDF held any text inside the figure box (a watermark, a panel letter), the engine used those few words and dropped the OCR. The ROC figure went in with 5 words; its 15 printed AUROC values sat unused. | OCR runs on the high-resolution image and is merged with the PDF text. Every panel with tick labels gets a calibrated axis. |
| A reply that reached the token limit was cut mid-JSON and thrown away whole. | Replies are streamed, cut at 120 s or when they repeat themselves, and their complete points are kept. |
| Twelve keys per point with every null spelled out: 133 tokens a point. | Rare fields are left out when they do not apply. |
| The model could not say "this is not a chart". One ECG figure cost 11 minutes and came back as invented series. | One short call first asks what the figure is. All five figures without data are declined, in 2 to 8 s each by the recommended model. |
| A point placed inside a bar stayed inside it: bars read up to 0.24 low. | A point on a bar's fill is followed to where the fill ends. |

One thing could not be changed from the engine: through this Ollama
(0.32.14) Gemma 4 spends at most about 270 tokens on an image of any size
(`scripts/probe_image_tokens.py`). A larger image buys the model nothing;
a smaller piece does, which is why the split matters so much.

## Which change did what

Gemma 4 26B-A4B (4-bit QAT) through three engines
([`ablation/no-split/`](ablation/no-split)):

| Engine | values within 5 %, names matched | names ignored | panels found (of 33) | time for the 15 figures |
|---|---|---|---|---|
| Round 1 | 55 | 55 | 20 | 535 s |
| Round 2 without the new splitter (prompt, context, reply format, checks) | 69 | 69 | 20 | 250 s |
| Round 2 | 85 | 188 | 33 ³ | 343 s |

³ Correction, 2026-11-18: 33 of 33 is the engine with the chart count from
the model's first call. The splitter on its own finds 32 of 33 (the vector
figure C4 stays one box), and on figures of other papers it does much
worse: [`../round-3/README.md`](../round-3/README.md#the-panel-splitter-checked-on-its-own).

The prompt, context and reply-format changes halve the time and fix the
single charts. The splitter is what brings the multi-panel figures in; it
also adds time back, because panels that were never read are now read.

## Results

### Judge verdicts per figure

C correct, p partial, w wrong, m missed, tn nothing returned for a figure
without data, FP values returned for one. `*` usable, `!` would mislead.

| | A1 | A2 | A3 | A4 | A5 | B1 | B2 | B3 | B4 | B5 | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 26B 4-bit, round 2 | tn* | tn* | C* | tn* | tn* | C* | p | C* | C* | p | C* | tn* | w! | p! | C* |
| 26B 4-bit, round 1 | tn* | tn* | w! | tn* | tn* | C* | m | C* | p | p! | p! | tn* | w! | w | C* |
| 26B 8-bit, round 2 | tn* | tn* | C* | tn* | tn* | C* | w | C* | p | p | C* | tn* | w! | p! | C* |
| 26B 8-bit, round 1 | tn* | tn* | p | tn* | FP | C* | m | w! | C* | p! | p! | tn* | w! | p | C* |
| 31B 8-bit, round 2 | tn* | tn* | C* | tn* | tn* | p | w! | p | p | p | C* | tn* | w! | p! | C* |
| 31B 8-bit, round 1 | tn* | tn* | C* | tn* | FP | C* | m | w | C* | p | w! | tn* | w! | p | C* |
| Sonnet, blind | tn* | tn* | C* | tn* | tn* | C* | p* | C* | C* | p* | C* | tn* | p | C* | C* |

Verdict files: [`judge/`](judge), one per run; `judge/summary.md` has the
counts and each judge's assessment.

### What the judges found

- **Printed numbers are now safe.** All three models return every printed
  value exactly: the 12 bar counts (when the reply is not cut), the 15
  AUROC values, the pie percentages, the interval bounds.
- **Bars are right, thin marks scatter.** Bar heights are exact once the
  engine follows the fill to its end (C1: 12 of 12 for all three models;
  round 1: 4, 5 and 1). Box medians, interval centres and line points
  have nothing to snap to and come back approximately right.
- **Dense stacked bars are out of reach** (C3: 264 segments in three
  panels). Every local run is wrong here and returns values above 100 on a
  0 to 100 axis.
- **The vector chart keeps machine names** (C4). The bars are right to
  0.005 but the series is called by its hex colour, the other series is
  missing and tick labels are cut short. C3 and C4 are six of the seven
  "would mislead" verdicts of round 2.
- **Panels are no longer the failure.** PANEL_STRUCTURE was assigned on 4
  to 5 figures per model in round 1 and on 0 to 1 in round 2.

### The 31B and the cut

Round 1 let a call run as long as it liked (up to the 600 s request
timeout). Round 2 cuts every call at 120 s and keeps what it has. That is
right for a model that writes 50 tokens a second and wrong for one that
writes six.

| Gemma 4 31B, 8-bit | B1: 12 printed bar counts | B2: three line panels |
|---|---|---|
| Round 1, no cut | 12 of 12, 279 s | nothing (600 s timeout) |
| Round 2, 120 s cut | 7 of 12, 137 s | 15 points, 402 s |
| Round 2, 300 s cut ([`ablation/longer-cut/`](ablation/longer-cut)) | 12 of 12, 184 s | 19 points, 511 s |

So the model is able and slow. On the panels it does finish it is the
most accurate of the three (box plots B5: 27 of 30 medians within 5 %,
against 26 and 23). A budget that fits it costs minutes per figure:
148 s for the five candidates of one paper, of which four are not charts.

### Time

| | round 1 | round 2 | of which figures without data, round 1 → 2 |
|---|---|---|---|
| Gemma 4 26B-A4B, 4-bit | 535 s | 343 s | 157 s → 16 s |
| Gemma 4 26B-A4B, 8-bit | 819 s | 533 s | 264 s → 19 s |
| Gemma 4 31B, 8-bit | 2,777 s | 2,461 s | 283 s → 66 s |

Figures without data were a third of round 1's time for the recommended
model and are 5 % of round 2's. For one paper with five chart candidates
the step now adds 24 s to a 379 s conversion (6 %); in round 1 it added
164 s (43 %).

## The cloud reference

One `claude-sonnet-5-5` sub-agent was given the 15 images under neutral
names and nothing else, with the truth folders unreadable while it ran and
every tool call checked afterwards ([`sonnet/AUDIT.md`](sonnet/AUDIT.md),
[`sonnet/PROMPT.md`](sonnet/PROMPT.md)). It looked at each image once.

- 9 of 10 data charts usable, none misleading, all five figures without
  data declined, 134 s for all 15.
- It returned 290 of 560 values; 289 are within 5 % of the axis range.
  What it left out it said it left out: the raw dots of the line chart and
  four of six rating levels of the stacked bars.
- Its values on unlabelled marks agree with the truth to about 0.2 % of
  the axis. That looked too good for a reading by eye, so it was checked:
  two charts drawn from random numbers that exist nowhere else, read by a
  fresh agent with nothing but Read and Write, came back with all 27
  values within 0.3 % of the axis. The precision is the model's reading.

It is not a candidate: the figures would leave the machine, which the
design rules out for unpublished or clinical papers. It marks how far a
look at the image can go, and so how much the local models still leave on
the table: at about 270 image tokens a panel, Gemma cannot see what
Sonnet sees.

## Limits

- **Tuned on the test set.** The engine was changed while looking at these
  15 figures and then scored on them. The causes fixed are general (they
  were found by probes, not by fitting scores), but the size of the gain
  will be smaller on papers the engine has not seen. The next round needs
  new figures.
- **Small set, one judge per run.** Ten data charts: one figure is ten
  points. Each run was judged once, by a fresh agent that saw neither the
  other runs nor round 1. Two verdicts were close calls by the judges' own
  account (B4 for the 26B 4-bit, B3 for the 31B).
- **Automatic scores still mislead.** The scorer pairs values by name, so
  right numbers under another label count as zero: it gives Sonnet 95 of
  560. The names-ignored count is an upper bound, since it lets chance
  matches through.
- **Round 1 and round 2 differ in one budget.** Round 1 had no cut per
  call. For the two 26B builds this does not matter; for the 31B it does
  (above).
- **Granite-Vision and Qwen were not rerun.** Round 2 covers three Gemma
  models by decision. Round 1 also gave Granite-Vision smaller images than
  the others (LOG.md, F12).

## What is still wrong

In the engine, found in this round and not fixed in it:

- Dense panels need to be cut into bands of rows before the model can read
  them (C3).
- Thin marks (medians, interval centres, line points) are not snapped to
  pixels; bars are.
- Values far outside the calibrated axis are flagged in the notes and
  still returned. They should be dropped.
- OCR often misses the lone "0" tick, so the axis range in the record
  starts at the next tick and correct small values are flagged as "outside
  the axis range".
- Vector charts: series named by their fill colour when the legend is not
  matched; tick labels cut short.
- The cut per call should follow the model's speed, or the slow model
  should not be offered.
- The splitter needs tick labels; pies and charts without numeric ticks
  fall back to the gutter method. A chart with a second y axis on the
  right would be cut in two.

## Next

1. Build figure-to-data as its own step of the conversion and the fourth
   config, `default-plusFigData`:
   [`.claude/reference/figure-data/STANDALONE-STEP.md`](../../../../.claude/reference/figure-data/STANDALONE-STEP.md)
   (design and open decisions).
2. Decide on the Ollama upgrade; after it, re-measure the image tokens and
   rerun one model.
3. A third round on figures from other papers.

## Reproduce

From the repository root, with the bundles under `samples/aca-papers_out`
and Ollama serving the three models of [`config.json`](config.json):

```bash
export BENCH_ROUND=round-2
MODELS="gemma4:26b-a4b-it-qat gemma4:26b-a4b-it-q8_0 gemma4:31b-it-q8_0" \
  bash docs/mini-bench/chart-to-data/scripts/run_ollama_models.sh           # about 55 GPU-minutes
uv run --no-sync python docs/mini-bench/chart-to-data/scripts/analyze.py     # round-2/metrics/
uv run --no-sync python docs/mini-bench/chart-to-data/scripts/judge_inputs.py
# one judge sub-agent per run with round-2/judge/PROMPT.md, then:
uv run --no-sync python docs/mini-bench/chart-to-data/scripts/judge_summary.py
uv run --no-sync python docs/mini-bench/chart-to-data/scripts/compare_runs.py \
  round1=docs/mini-bench/chart-to-data/runs/gemma4_26b-a4b-it-qat \
  round2=docs/mini-bench/chart-to-data/round-2/runs/gemma4_26b-a4b-it-qat
```

The blind run: an agent with [`sonnet/PROMPT.md`](sonnet/PROMPT.md) and a
folder of the 15 work images, then
`scripts/import_agent_answers.py <answers> <images> round-2/runs/<name> "<label>"`.

## Files

| path | content |
|---|---|
| `LOG.md` | findings, changes, iterations, what was tried and dropped |
| `config.json` | models, engine options, hardware, judge and reference-run setup |
| `runs/<model>/all/` | figure-data JSON per figure, `timing.json` with the engine's notes per figure, the options of the run |
| `runs/claude-sonnet-5-5-blind/` | the blind run in the same layout |
| `ablation/no-split/`, `ablation/longer-cut/` | the two side runs |
| `metrics/` | per-figure CSV, metrics JSON, summary table |
| `judge/` | prompt, one verdict file per run, summary |
| `sonnet/` | prompt, isolation and tool log, raw answers, the control charts |
| `../scripts/` | shared with round 1; `BENCH_ROUND=round-2` points them here |
| `report-page/` | builds the interactive report page (summary, and every figure with the truth and each run's values); the figures are embedded, so the built page is not kept here |

The figure crops, overlays and work images are not in the repository
(they are the papers' artwork); [`../FIGURES.md`](../FIGURES.md) says where
each figure is in its paper.
