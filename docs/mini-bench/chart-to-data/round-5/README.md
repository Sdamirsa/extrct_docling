# Round 5: the chart list, built and run through the pipeline

19 November 2026. The split check
([`../round-4-plus-splitter/README.md`](../round-4-plus-splitter/README.md))
decided what should cut a figure into its charts. This round builds that
into the step and runs the pipeline command on three papers with both
recommended configurations.

## Answer

- **The rule is in the engine and gives the cuts the check measured.**
  `panels.cut_from_list` on the 51 figures with the stored chart lists: 37
  figures cut right with Gemma 4 26B, 46 with Sonnet 5.5 and with Gemini
  3.8 Flash, the numbers of the check.
- **Three papers end to end, both methods: every command exits 0, every
  bundle check is OK, and the readings are in every export.** 23 chart
  candidates in 98 pages.
- **The cut is right on 14 (local) and 15 (cloud) of the 18 figures that
  have a truth, against 6 with the rules alone.** On the showcase paper:
  10 and 11 of 11, against 5 in round 4.
- **Values on the showcase paper, local method:** 148 of 573 right on the
  six main figures, against 96 in round 4.
- **Values on the showcase paper, cloud method:** mixed. The dense
  supplementary figures improve (46 of 60 sampled bars right, against 38):
  the five-panel figure round 4 declined is now read. The six main figures
  come out lower (378 of 573, against 421), all of it on one figure
  (below).
- **The runs and an independent review found defects, all fixed** (below).
  The most costly: a reply that wraps its JSON in a sentence was thrown
  away whole.

## What was built

- **`panels.cut_from_list`**: the rule splitter's cut stands when it has as
  many charts as the model lists; else the figure is cut between the
  listed boxes along the ink-free bands and each cell trimmed to its ink;
  else the listed boxes are kept as they are.
- **Local engine** (`pipeline.py`): the overview call it always made now
  decides the cut that way. A figure whose listed charts no straight cut
  separates is not read, as before.
- **Cloud method** (`methods/cloud.py`): one extra call lists the charts
  (low reasoning effort), the prepared figure is cut again by the list
  (`prepare.relist`), then the read as before. `panel_split = "rules"`
  leaves the list out.
- **Gone:** the local engine's special cases for a model and rules that
  disagree, the splitter's unused box-reader hook and its `expect`
  parameter (weak tick-label evidence when a model counts as many charts:
  tried against the rule on the 51 figures, 36, 45 and 46, so not kept).
- **Sonnet's list call at low effort** was measured before it became the
  default: 46 of 51 figures cut right, as at high, in the same 3 seconds.

## The three papers

`amir-batch <three PDFs> --figure-data ollama` and `--figure-data cloud`
on the showcase paper (68 pages), AgentMD (11) and Zodiac (19), each
method on its own copy of one conversion.

| | Local: Gemma 4 26B | Cloud: Sonnet 5.5 |
|---|---|---|
| Command exit, bundle checks | 0, all OK | 0, all OK |
| Chart candidates read / no data / not read / failed | 17 / 4 / 2 / 0 | 18 / 5 / 0 / 0 |
| Charts, values returned | 66, 2,193 | 73, 1,874 |
| Cut right, of 18 figures with a truth (rules alone: 6) | 14 | 15 |
| Reading the 23 figures | 2,543 s | 782 s |
| Cost | local | 1.97 USD |
| Readings at the figure in markdown, chunks and page viewer | 17 of 17 | 18 of 18 |

Per paper:

| Paper | Method | Read / no data / not read | Charts | Values | Seconds | USD |
|---|---|---|---|---|---|---|
| Showcase | local | 11 / 0 / 1 | 37 | 1,523 | 2,023 | |
| Showcase | cloud | 11 / 1 / 0 | 39 | 891 | 421 | 1.06 |
| AgentMD | local | 4 / 2 / 0 | 22 | 498 | 381 | |
| AgentMD | cloud | 4 / 2 / 0 | 23 | 415 | 181 | 0.47 |
| Zodiac | local | 2 / 2 / 1 | 7 | 172 | 139 | |
| Zodiac | cloud | 3 / 2 / 0 | 11 | 568 | 180 | 0.44 |

The cuts that are still wrong: W10 (14 small charts, the number right and
boxes off) with both methods; S11 (Gemma lists 8 of 11 panels) and W09
locally; W07 (a hard call in the truth) with the cloud model; W30, whose
listed charts no straight cut separates: the local engine does not read
it, the cloud model reads it from its own boxes.

## The showcase paper against round 4

Values right within 5 % of the axis under the right printed name
(`scripts/compare_bundles.py`, the truth of round 4). Round 4's column is
its run with Figure 6 read again after the capture fix, which this round's
conversion has from the start.

| | Local, round 4 | Local, round 5 | Cloud, round 4 | Cloud, round 5 |
|---|---|---|---|---|
| Figures cut right, of 11 | 5 | 10 | 5 (the same prepared split) | 11 |
| Six main figures: values right, of 573 | 96 | **148** | 421 | **378** |
| Five dense figures: sampled bars right, of 60 | 8 | 9 | 38 | **46** |
| Values returned, all 12 figures | 1,061 | 1,523 | 867 | 891 |
| Reading the 12 figures | 1,609 s | 2,023 s | 358 s | 421 s |
| Cost | local | local | 0.91 USD | 1.06 USD |

Figure by figure, where a number moved:

| Figure | Truth | Local, round 4 | Local, round 5 | Cloud, round 4 | Cloud, round 5 |
|---|---|---|---|---|---|
| Figure 4 (S03), one chart of 37 bars | 222 | 10, in 2 charts | 37, in 1 chart | 80, in 2 charts | 37, in 1 chart |
| Figure 7 (S06), four panels | 52 | 26, in 6 charts | 51, in 4 charts | 52 | 52 |
| S12, five panels (sample of 12) | | not read | read, 0 right | not read | read, 8 right |
| S14, three panels (sample of 12) | | 3, in 8 charts | 5, in 3 charts | 12 | 12 |
| S11, eleven panels (sample of 12) | | 1, in 7 charts | 0, in 8 charts | 2, 66 values | 2, 13 values |

- **Local:** the two figures the wrong split had broken are read in their
  real charts. Figure 7 goes from 26 to 51 of 52.
- **Cloud, Figure 4:** in round 4 the figure was wrongly cut in two and the
  model got both halves as crops. It returned the 37 printed shares and an
  estimate of Incorrect for every bar, 80 values, all within 5 %. Cut
  right, the figure is one chart and has no crop: the model returned the
  printed shares alone. The wrong cut had given a single dense chart more
  pixels by accident. Reading the values inside one dense chart is what
  the split check said this change does not address.
- **Cloud, S11:** the cut is right (11 panels) and the model read 13 values
  of the first panel and said the labels of the others are too small. The
  first pass's reply for this figure was the one thrown away (below); it
  had opened with "I transcribed only the green Correct segment of each
  bar".

## What the review and the runs found

An independent reviewer read the change before the runs; the runs found
the rest. All fixed, each with a test.

| Found by | Defect | Fix |
|---|---|---|
| review | A figure folder cut by one model's list kept that cut for every later run (a failed list, another method, `panel_split = "rules"`) | every run starts from the rule splitter's cut (`prepare.unlist`) |
| review | A listed chart without width crashed the read after the old crops were deleted | such a box counts as a chart and is no seed for a cut; a box without area gets no crop |
| review | The cost of a list call was lost when its reply was not a list | the call is counted and the reply kept in the trace |
| review | A sliver could become a chart; a reply repeating one chart 300 times would be taken | cells and seeds under 2 % of the image's side are dropped; more than 64 listed charts are not taken |
| review | The local engine read the PDF's drawing paths twice per figure | read again only when the charts changed |
| review | Two chart ids could give one crop file name | ids are kept only as short plain words, else 1, 2, 3 |
| runs | **A reply that put a sentence before its fenced JSON was thrown away whole** (one figure, 153 seconds of reading) | the JSON object is looked for inside the reply |
| runs | With a crop per chart and high reasoning effort, the model twice wrote tool calls it does not have around or instead of its answer (53 and 279 seconds) | the system message says there are no tools; a reply without JSON fails the figure with its text kept and its cost counted |

The three figures of the last two rows were read again with the fixed
code: all three read.

## Limits

- **One run per method.** The cloud model's choice of what to estimate on
  a dense chart changes from run to run (Figure 4, S11).
- **The cloud column is two runs:** the first pass, and the three failed
  figures read again after the fix. The rest of the bundles is the first
  pass.
- **One conversion was shared** by both methods, so "reading" is the step
  alone; a whole command adds the conversion (610 s for the showcase
  paper).
- **The read call still runs at high reasoning effort**, as in rounds 3 and
  4. The list call runs at low.
- **No judges this round**, and the truth is that of round 4 and of the
  split check.

## Files

| Path | What |
|---|---|
| `testset.json`, `truth/`, `truth-sample/` | the showcase paper's test set and truth, as in round 4 |
| `runs/<label>/` | the readings and run records of the three papers (no figure images) |
| `metrics/pipeline.md`, `pipeline.json` | the showcase paper against the truth, as round 4 computed it |
| `metrics/e2e.json` | what both methods left in the three bundles, figure by figure |
| `../round-4-plus-splitter/final-test/engine-rule.json` | the engine's rule on the 51 figures |

## Spend

About 3.0 USD on OpenRouter: Sonnet's chart list at low effort on the 51
figures 0.53, the first cloud pass 1.54 as recorded (the three failed
reads were not counted by the code of that pass), the three figures read
again 0.48. One review agent.
