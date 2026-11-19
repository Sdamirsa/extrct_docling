# Round 4 log: one paper through the whole pipeline, four ways

2026-11-19. Findings are numbered on from round 3 (F28 onward). Results and
the short version are in [`README.md`](README.md).

## 1. What was asked

The maintainer, 2026-11-19: run all four methods (two cloud models, one
Ollama model, the agent) on the showcase paper, save the output and open
its folder. The converted outputs are not meant to be pushed; the point is
to know the actual difference on one paper. "Also this needs
implementation within the pipeline we have and also test this new
component fully end to end with four methods."

So this round is not a bench of prepared figures, as rounds 1 to 3 were. It
is the pipeline command a user types, `amir-batch <pdf> --figure-data
<method>`, run four times on one 68-page paper, and what each run leaves in
its bundle.

## 2. What the step still lacked inside the pipeline

`amir-batch --figure-data` was wired in round 3, and round 3 only ever ran
the standalone `amir-figdata` commands end to end. Running the batch
command showed what was missing.

**F28. The page viewer showed nothing of the step.** A person who opens a
bundle opens `preview.embedded.html` first. The embed rewrote the markdown,
the HTML, the chunks and the JSON files and left the viewer as the
conversion wrote it, because the viewer could only be built from a
conversion in memory.

- `visualizer.rebuild_html_preview(bundle)` builds the same page from the
  bundle's files (`document.json`, the page renders, `figures.jsonl`,
  `chunks.jsonl`). Checked on the showcase bundle of release r3: 394 boxes
  on 68 pages, none shifted, page sizes equal; on a bundle converted with
  this code the rebuilt file is identical to the one the conversion wrote.
- A figure with a reading carries a `data` tag on its box; its side panel
  shows the note that a model read it, the table of values, what was left
  unread and a link to `figure-to-data/<figure>/figure-to-data.md`; a chip
  in the header counts the figures with data.
- The embed rebuilds `preview.html`, and `preview.embedded.html` when the
  bundle has one.

**F29. The batch summary was made before the step ran.** Its `check` column
and chunk count showed the bundle as it was before the readings went in,
and the exit code did not see a check the step had changed. The rows of the
bundles the step ran on are now read again from disk.

**F30. `amir-batch` had no way to say where Ollama listens.** The
standalone command had `--ollama-url`; the batch command now has
`--figure-data-ollama-url`.

**F31. An error message named the wrong method.** A missing `claude`
executable was reported as needed by "the cloud and agent methods"; since
round 3 the cloud method does not use it.

## 3. The end-to-end test, and what it found before any model ran

`tests/test_engines/test_figure_data_batch.py`: a synthetic chart PDF goes
through `amir-batch` with a real conversion, once per method setup
(`ollama`, `cloud`, `cloud` with another model, `agent`). No model runs:
the methods talk to stand-ins at the process boundary, a local HTTP server
that answers as an OpenAI-compatible endpoint and as Ollama, and a `claude`
executable that starts the agent's real tool server, as a session does, and
records a chart through it. The test then looks for the reading in every
export of the bundle, the viewer and the batch summary included, and runs
the command a second time to see that nothing is read twice.

Getting it to pass showed three things about the step that no bench of
prepared figures could show, because they come from the conversion:

**F32. The figure box of the layout model decides what a reader sees.** On
the first synthetic page the layout model's box ended under the top tick
label ("1.0" became the figure's caption). The axis then ran from 0 to 0.5
for every reader, bars above 0.5 failed the check "outside the axis range",
their confidence fell under the threshold, and the table was held back from
the exports. All of that is the step working as designed on a figure it was
handed without its axis. The test's chart now prints a label level with the
top tick, which the layout model boxes in.

**F33. A bar that fills 90 % of its chart's box is taken for a frame.** The
local engine's vector reader drops marks taller than 0.9 of the region
(`readers/vector.py`), a rule that keeps plot frames out. A bar reaching
the top tick of a tightly boxed chart is such a mark and was not read.
Open: not changed in this round.

**F34. A reading from an endpoint on this machine starts at the local
confidence.** The stand-in endpoint is on 127.0.0.1, so the cloud method
treats its model as a local one (0.5, under the 0.7 threshold): the
readings were held back from the table until the stand-in also returned
the labels printed over the bars, which the step confirms against the
figure's text (0.95). That is the rule of round 3 doing what it should.

## 4. The runs

Each run is one command, from the repository root
([`../scripts/run_round4.sh`](../scripts/run_round4.sh)):

```
amir-batch showcase/Public-test-manuscript.pdf -o samples/round-4-showcase/<label> \
    --figure-data <method> [--figure-data-model <model>]
```

One after the other, so that the conversion and the local model never
share the GPU with another run. The conversion uses the default options
(Granite-Vision for tables and figure descriptions) and is repeated in
every run: the four bundles have the same 15 pictures with the same boxes,
and the same 12 chart candidates.

The step's code was frozen from the first run's start to the last run's
end: a defect found on the way (section 7) was fixed afterwards and is
reported separately.

## 5. Truth

Six of the twelve candidates have a full truth, made by three fresh
sub-agents that never saw a model's output ([`truth/README.md`](truth/README.md)):
573 values in 13 charts. Two of these figures (S04, S06) had a truth of
2026-11-09 in the engine's test data, made by another agent from an older
conversion; the new files agree with it on every value the two key alike
(144 of 144, and 40 of 40, within 2 % of the axis).

The other six are of another size. S09 is a strip of 300 cells per model.
S10 to S14 hold 26 panels of 37 stacked bars with six classes each: 5,772
segment values, of which 955 are printed (the share of Correct). The
printed digits are 7 to 8 px high in the bitmaps of S10 and S14 and 4 to 6
px in S11 to S13, where a fourth agent could not read them at any
enlargement ([`truth-sample/STRUCTURE.md`](truth-sample/STRUCTURE.md)).
For these five figures there is a sample fixed by rule instead of a truth:
in the first and the last panel of each figure the share of Correct of
bars 1, 8, 15, 22, 29 and 36, 60 values, printed where the print can be
read (24) and measured against the y axis where it cannot (36, re-measured
once, largest shift 0.28 points).

**F35. Not every figure of this paper was new to every method.** S04 and
S06 (Figures 5 and 7) are two of the five figures of the smoke set the
local engine was first built and tested on (2026-11-09,
`tests/data/figure_data/testset-5.json`). The cloud and agent methods were
built in round 3 on the 15 figures of the bench, none of which is from
this paper. The other ten candidates are new to all three methods.

## 6. Scoring: why three counts

The scorer of rounds 1 to 3 pairs a predicted chart with the truth chart
whose box it overlaps by more than half, and a predicted value with a truth
value whose category and series are less than a fifth apart, first fit. On
the figures of the bench that was enough. On this paper it undercounts in
three ways, each seen in the first two runs:

- **A chart the step cut in two.** The prepare phase splits charts by
  their tick labels and made two of Figure 4 (37 bars in six blocks) and
  six of Figure 7 (four panels). The second part of a split chart overlaps
  no truth chart by half and its values count as invented.
- **Charts without a box of their own.** A model that does not take the
  chart ids it was given numbers the charts itself; the step then gives
  each the whole figure as its box, and none pairs (Figure 7 by the cloud
  call: 0 of 52 as scored, 52 of 52 right).
- **Names that are almost the same.** "Claude3-Sonnet Web", "Claude3-Sonnet
  API" and "Claude3.5-Sonnet API" are less than a fifth apart, as are most
  of the 37 bar names. First-fit pairing then follows row order, and a
  reading that leaves a row out pairs the next bar with its neighbour. The
  truth agents measured it: the truth of Figure 4 with its rows shuffled
  scores 188 of 222.

[`../scripts/compare_bundles.py`](../scripts/compare_bundles.py) therefore
reports three counts of values within 5 % of the axis range:

- **as scored**: the scorer as it was, for comparison with rounds 1 to 3;
- **by name**: charts are first put where the truth has them (by printed
  title, then by id, then a part of a split chart is merged into the truth
  chart that holds its box, then by place), and a value is paired with the
  value under the same printed name (exactly, then at 85 % similarity
  among what is left: a reading may correct the figure's own misspelling);
- **names ignored**: with the charts placed the same way, the sorted values
  of paired charts are compared whatever they are called. An upper bound
  that lets chance matches through.

The judges' verdicts and the by-name count agree figure by figure on the
runs judged so far; the judges were told how the scorer pairs and found the
same undercounts on their own.

## 7. A defect in the prepare phase, found on Figure 6

**F36. An embedded bitmap was taken without its soft mask.** Where a figure
is one image in the PDF, the prepare phase takes that image's own pixels
when they are sharper than a page render. The image of Figure 6 (S05)
carries a soft mask: 30 % of it is transparent, and the file stores black
there. pdfium hands out an image's pixels without its mask, so every reader
was given the figure with black where the page is white. The axis titles
and tick labels are printed in black on that part and were gone; the model
of the first run said so itself ("Axis tick labels and x-axis labels are
not visible in either chart"). The truth, made from the PDF, is keyed by
those labels (years, cut-off dates), so no value of S05 could be paired by
name in any of the four runs, and the runs gave sibling models (same
colour, releases a few months apart) each other's values.

- Fix (`evidence._image_bitmap`): the alpha is taken from pdfium's
  rendering of the image object, the pixels stay the file's own, and the
  figure is put on white. The share of near-black pixels of the prepared
  Figure 6 went from 31.7 % to 2.3 %; the chart list in `figure.txt` now
  names both axes with their ticks.
- Test: `tests/test_engines/test_figure_data_prepare.py` builds a PDF whose
  image has a soft mask and a black tick mark on the transparent part.
- The image of Figure 3 (S02) has a mask too (43 % transparent). It was
  captured by a page render, which applies the mask, and was not affected.
  No other figure of the paper has one.

**F37. Years a step apart were fitted as a log axis.** With the labels
visible, the first prepared `figure.txt` said "x ticks 2021 | 2022 | 2023
(log)". Three ticks that far from zero lie on a line in both scales and the
last pixel decided. `fit_axis` now keeps a linear fit that is off by less
than 0.5 % of the range; ticks of 1, 2, 4, 8 and of 1, 10, 100 are still
fitted as log.

The fix went in after the last of the four conversions had started, so no
run of the round used it: the four bundles hold Figure 6 as it was first
read. Each method then read the corrected figure once more, outside the
bundles ([`after-fix/`](after-fix/)):

| | first pass, by name | after the fix, by name | seconds | cost USD |
|---|---|---|---|---|
| `ollama` | 0 of 13 | 13 of 13 | 44 | local |
| `cloud`, Sonnet 5.5 | 0 of 13 | 13 of 13 | 13 | 0.03 |
| `cloud`, Gemini 3.8 Flash | 0 of 13 | 13 of 13 | 146 | 0.12 |
| `agent`, Sonnet 5.5 | 0 of 13 | 13 of 13 | 22 | 0.07 |

(13 of the 17 truth rows have a value, section 5.) In the first pass every
run had the 13 printed numbers themselves right; what it could not know was
which year or date a point stands at.

## 8. What the four runs did with this paper

One row per run; the conversion took 673 to 707 s in each.

| | `ollama`, Gemma 4 26B | `cloud`, Sonnet 5.5 | `cloud`, Gemini 3.8 Flash | `agent`, Sonnet 5.5 |
|---|---|---|---|---|
| whole command | 2,355 s | 1,093 s | 2,532 s | 1,614 s |
| reading the 12 figures | 1,609 s | 358 s | 1,809 s | 854 s |
| cost | local | 0.91 USD | 1.42 USD | 2.97 USD |
| calls, tool calls | 51 | 12 | 12 | 12 sessions, 102 tool calls |
| output tokens (of them thinking) | 58,061 | 70,622 (10,931) | 352,833 (265,088) | 144,494 |
| figures read / no data / not read | 10 / 0 / 2 | 10 / 1 / 1 | 11 / 1 / 0 | 11 / 1 / 0 |
| values returned | 1,061 | 867 | 1,529 | 1,970 |
| six main figures: within 5 % by name, of 573 | 83 | 408 | 554 | 251 |
| the same with Figure 6 read again | 96 | 421 | 567 | 264 |
| the scorer of rounds 1 to 3 | 67 | 331 | 526 | 213 |
| judges: correct / partial | 0 / 6 | 4 / 2 | 4 / 2 | 3 / 3 |
| judges: usable, would mislead | 0, 3 | 5, 0 | 4, 0 | 5, 0 |
| five dense figures: sampled bars right, of 60 | 8 | 38 | 55 | 60 |
| table at the figure / pointer only | 7 / 3 | 9 / 1 | 11 / 0 | 9 / 2 |

**F38. The chart splitter was wrong on six of the eleven chart figures.**
It cuts a figure into charts by their tick labels. Right: Figures 3, 5, 6
and two of the supplementary grids (S10, S13). Wrong: Figure 4, one chart
of 37 bars in six blocks, cut in two; Figure 7, four panels, cut in six;
the confusion matrix, cut in three; S11, eleven panels, seven found; S12,
five panels, taken as one chart; S14, three panels, eight found. What follows from
a wrong split depends on the method:

- the local engine reads one crop per chart it was given, so it read what
  the split gave it (107 values in six charts for Figure 7's 52 in four),
  and declined S12 ("the model sees 5 charts and the layout analysis
  separates 1");
- a cloud model sees the whole figure beside the crops and said what it
  saw ("the layout analysis split the figure into 8 crops; it holds only 3
  charts, and I read them as 3 panels");
- the agent looked for itself and recorded the charts the figure has.

**F39. A reading's charts take the boxes of a wrong split.** The step gives
a chart of a reading the box of the prepared chart with the same id. When
the model names its charts a to d and the split had six parts called a to
f, panel c gets the box of some other part. The values are untouched; the
box is wrong in the record (`bbox_px`), and the bench scorer, which pairs
charts by box, then compares panel c with panel d (Figure 7 by Gemini and
by the agent: 24 of 52 each as scored, 52 of 52 right). Open.

**F40. Stacked bars with many small segments: four different answers.**
Figures 4 and 5 are 37 and 24 bars of six classes; only the share of
Correct is printed, the other segments have to be measured, and three of
them are a point or two wide.

- Gemini 3.8 Flash returned all 366 values. The printed shares are exact;
  the judge found the small segments under the wrong class in Figure 4 (the
  EOP gap returned as 2OP, the grey NOP as EOP: NOP is non-zero in 2 bars
  where the figure has 17) and an orange Error segment of two bars set
  aside as "unlabelled" in Figure 5. A count within 5 % of the axis does
  not see that: a segment of 1.3 points under the wrong name is 1.3 points
  off. 554 of 573 is therefore kinder to this run than its judge, who
  called both figures not usable as they are.
- Sonnet 5.5 in one call returned all 144 values of Figure 5, every one
  within 5 %, and for Figure 4 the printed share and an estimate of
  Incorrect per bar (80 of 222), saying that the small segments were
  "mostly not read".
- The agent recorded the printed share alone on both figures (61 of 366)
  and wrote that the other segments "are small, so reading them would be
  estimates only". Its judge: Incorrect runs from 20 to 72 points, and one
  bar's Error segment is twice its Correct share. On the supplementary
  figure S13 the same agent recorded all 888 segments of four panels.
- The local engine returned the printed shares (60 of 61 right) and, for
  Incorrect, the bar's right end (99.8) on 34 bars: its judge called both
  figures misleading.

**F41. The dense supplementary figures.** S10 to S14 hold 5,772 segment
values in 26 panels. No run returned a third of them: the agent
1,702 (the printed share of every bar in all 26 panels, and every segment
of S13), Gemini 956 (the share of Correct of nearly every bar in every panel),
the local engine 717, Sonnet 436 (S12 declined: "the x tick labels are too
small and blurred to read reliably"; six bars per panel in S11). On the 60
sampled bars the agent was right on 60, Gemini on 55, Sonnet on 38 (all it
returned), the local engine on 8. The agent could enlarge a panel; the
single calls saw each panel once, at the size of its crop.

**F42. The strip figure S09** (one coloured cell per model and question,
about 11,000 cells) was declined by all four: three as "not a data chart",
the local engine without values. Nothing was invented for it.

**F43. Gemini 3.8 Flash thinks for three quarters of its output**, as in
round 3: 265,088 of 352,833 tokens, two to four minutes a figure. It is
the slowest of the four and its single call is not the cheapest.

**F44. Every method said what it left out.** Each reading of a figure that
is incomplete names the part not read in its `uncertain` list (quoted
above), with one exception the judge found: the local engine's dense
figures "come back incomplete without a word".

## 9. The judges

One fresh sub-agent per run, the six figures with a truth file
([`judge/PROMPT.md`](judge/PROMPT.md), [`judge/summary.md`](judge/summary.md)).

| | correct | partial | usable | would mislead | dominant failure |
|---|---|---|---|---|---|
| `ollama`, Gemma 4 26B | 0 | 6 | 0 | 3 | GEOMETRY_MISMEASURED |
| `cloud`, Sonnet 5.5 | 4 | 2 | 5 | 0 | MISSING_VALUES |
| `cloud`, Gemini 3.8 Flash | 4 | 2 | 4 | 0 | VALUE_ASSIGNMENT |
| `agent`, Sonnet 5.5 | 3 | 3 | 5 | 0 | MISSING_VALUES |

- All four judges found, without being told the numbers, that the scorer
  as it was undercounts on this paper (section 6), and counted the values
  by content instead.
- **S05 was judged under the defect of section 7**, and the judges read
  that rule differently: with the same four values given to the wrong
  sibling model, one called the figure correct and usable, one correct and
  not usable, two partial. S05 is the weakest part of the judges' table;
  the reading after the fix is the better evidence for that figure.
- On the six judged figures no printed number was misread by any of the
  three runs that send the figure out, and none of the three would
  mislead.

## 10. What a user of the pipeline gets

The four bundles are in `samples/round-4-showcase/<label>/` (not
published), with `comparison.html` beside them. In each bundle the step
left, for the 12 chart candidates: `figure-to-data/` (one folder per
figure with what the reader was given and what it read, and the run
record), the note and table at the figure in the markdown, the HTML and
the chunks, a `figure_to_data` block in `run.json`, the counts in
`check.json` (`charts 9/10/12` in the batch summary of the first run), and
the reading in the page viewer.

- The four bundles have 164 to 189 chunks, 10 or 11 of them carrying
  figure data.
- A reading whose values did not reach the confidence threshold is a
  pointer in the exports, not a table: 3 figures of the local run, 1 or 2
  of the Sonnet runs, none of Gemini's.
- The conversion is the larger part of the command for the cloud call
  (683 of 1,093 s) and the smaller for the local model (696 of 2,355 s).
- While the step ran, the batch process still held 8.7 GiB of GPU memory
  after it had let go of the conversion engine (seen during the Gemini
  run). The local model fitted beside it on this machine; on a 24 GB GPU
  it would not have much room. Open.

## 11. Open after this round

- The chart splitter on grids of bar charts and on one chart in blocks
  (F38), and the box a reading's chart is given after a wrong split (F39).
- The agent's policy on stacked bars: it records what is printed and
  leaves the measured segments out on some figures and not on others
  (F40). The conventions already say one point per segment.
- The vector reader's frame rule (F33).
- The scorer of the bench pairs names less than a fifth apart, first fit
  (section 6); `compare_bundles.py` pairs by exact name, the scorer in the
  package was not changed.
- GPU memory still held by the batch process during the step (section 10).
- The four bundles hold Figure 6 as read before the fix of section 7. A
  second pass of the four commands would give bundles made by the fixed
  code throughout; it was not run (about 2 hours and 5 USD).
- One paper. Round 3's order of the methods (Sonnet's single call ahead of
  Gemini's on 15 figures of 11 papers) is not the order here, and neither
  settles it.
