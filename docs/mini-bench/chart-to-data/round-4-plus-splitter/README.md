# Round 4 plus: the splitter, checked on its own

19 November 2026. A side check to round 4, not a round of readings.

Before any method reads a figure, the prepare phase cuts it into its charts
("split"). Round 4 found that cut wrong on 6 of the 11 chart figures of the
showcase paper ([`../round-4/LOG.md`](../round-4/LOG.md), finding F38). This
check asks one question: **what should decide the cut?** It measures the cut
alone, on 51 figures, for nine ways of making it, each also with a second
splitter as judge.

## The decision

A final test followed the check ([`final-test/README.md`](final-test/README.md))
and settled what the step should do. One rule, for one local and one cloud
configuration:

- **The model that reads the figure lists its charts.** Locally that is
  Gemma 4 26B in the overview call the local engine already makes. In the
  cloud it is one extra call to the reading model, Sonnet 5.5 by default.
- **The rule splitter's cut is taken when it has that many charts.** When
  it has not, the rules' cutter is started from the model's boxes.
- **Figures cut right, of 51:** 37 locally and 46 with a cloud model,
  against 24 today.
- **Tested and left out:** the figure's caption in the list call, and a
  second call that rules between the two cuts. Neither moved a result by
  more than one or two figures.
- **Out by the maintainer's decision:** Heron and FigEx2.

Per configuration and step:

| Step | Fully local | Cloud | What was measured |
|---|---|---|---|
| Listing the charts | Gemma 4 26B, no extra call | the reading model, one extra call | number of charts right on 42 of 51 figures (Gemma), 51 (Sonnet), 50 (Gemini); the rules: 26 |
| Drawing the edges | the rules' cut on the same count, else the rules' cutter from the list | the same | charts whole in their crop: 138 of 236 locally, 193 (Sonnet), 213 (Gemini); today 135 |
| Figures cut right | 37 of 51 | 46 of 51 | today 24 |
| One figure takes | 5.5 s | 3.3 s and 1.0 cent (Sonnet); 5.3 s and 0.3 cent (Gemini) | |

What we learnt:

1. **A vision model knows what is in a figure, not where its edges are.**
   Its number of charts is right on 42 to 51 of 51 figures; its own boxes
   hold the whole chart for 53 to 145 of 236.
2. **The rules know where the edges are, once told what to look for.**
   Started from a model's boxes, their cutter leaves up to 220 of 236
   charts whole. Alone they have the number of charts right on 26 figures.
3. **Where the two disagree on the number, the model is right.** Sonnet on
   25 of 25 such figures, Gemini on 24 of 25, Gemma on 20 of 29; the rules
   on 0, 0 and 4.
4. **A detector trained for something else does not carry over.** Heron
   cuts 10 of 11 figures of one paper right, and 5 of 10 and 9 of 30
   elsewhere. FigEx2 goes by printed panel letters, which most chart grids
   lack.
5. **A second opinion can flag doubt; it should not overrule.** As judges,
   Heron and FigEx2 make the good splitters worse. With the model's count
   in hand, a ruling call between two cuts has one to three figures left
   to win.
6. **A caption names panels, not charts.** Added to the list call it does
   not improve the count.
7. **What stays open:** grids of 14 to 18 small charts, and the values
   inside one dense chart, which no cut helps.

Three figures of the showcase paper with their cuts drawn as diagrams are
in [`examples/README.md`](examples/README.md). The private page of the
check shows every figure with every cut.

Nothing of this is built yet. The sections below are the check as it was
run, in order.

## The answer

- **A vision model's own list of charts is by far the best cut.** Asked once
  per figure with the step's existing overview prompt, Sonnet 5.5 and Gemini
  3.8 Flash each cut 49 of 51 figures right. The call takes 3 to 5 seconds
  and costs 0.3 to 1 cent.
- **A model's boxes are not crops yet.** They sit on the right charts but
  clip titles and tick labels: only 134 of Gemini's 236 charts are whole in
  their box. Used as seeds for the rule splitter's own cutter, 220 of 236
  are whole, for 2 fewer figures cut right.
- **No detector decides the cut by itself.** The rule splitter, Docling's
  layout detector (Heron) and FigEx2 each cut 24 of 51 right. Heron's 10 of
  11 on the showcase paper does not carry over: 5 of 10 on the bench, 9 of
  30 on other papers.
- **As judges, Heron and FigEx2 flag doubt; they do not fix cuts.** Letting
  either overrule a splitter makes the good splitters worse. Agreement is
  the useful signal: where the rules and FigEx2 find the same number of
  charts (20 figures), the rules' cut is right on all 20.
- **For the local method the best cut combines three witnesses:** Gemma's
  chart count picks the rules' cut when it has that many charts, else
  Heron's, else Gemma's own boxes: 35 of 51, against 28 for Gemma's boxes
  and 24 for the rules or Heron alone.
- **FigEx2 is not a fit for this step.** As designed it cuts 24 of 51 right;
  its detector alone, 16. It needs a 17 GB base model, its repositories
  state no licence, and its detector knows panels by their printed letter,
  which most chart grids do not have.

## The set and the truth

51 data figures with 236 charts ([`figures.json`](figures.json)):

| Group | Figures | Charts | Where they come from |
|---|---|---|---|
| Bench | 10 | 33 | the data figures of the 15-figure bench of rounds 1 to 3 |
| Showcase paper | 11 | 39 | the chart figures of round 4 (Figure 6 as captured after the fix) |
| Other papers | 30 | 164 | figures of 12 other papers that round 3 looked at by eye |

Every figure was prepared again with today's code (`amir-figdata prepare`),
so the rule splitter's cut and the figure images are the current ones.

The truth was drawn anew for all 51, blind, by four agents
([`truth/PROMPT.md`](truth/PROMPT.md)). Each got 12 or 13 images under
neutral names in a shuffled order, the brief and a drawing script, and
nothing else: no splitter's output, no earlier truth, no paper names. An
agent writes its boxes, draws them on the figure, looks at each box
enlarged, and corrects until each box holds its whole chart (plot, tick
labels, axis titles, own title and legend) and nothing of a neighbour.

Checks on the truth:

- 21 figures had a chart count from earlier truth (rounds 1 to 4). The
  blind agents gave the same count on all 21.
- The overlays of two hard figures (a grid of 15 charts; two charts whose
  legends overlap) were looked at afterwards: boxes as the brief asks.
- The agents named their hard calls, kept in each file's `note`. The ones
  that could change a score: W07 (two panels, each a tile grid with a bar
  plot on shared rows, counted as 2; could be read as 8), W26 (two panels of
  four blocks on one axis, counted as one chart each), W22 (a bar plot
  inside a chat screenshot, counted), W29 and W30 (a colour bar shared by
  several heatmaps, left out of every box). On seven figures two boxes
  overlap because a legend or label of one chart reaches into its
  neighbour.

## What was compared

| Name | What it is | Model call per figure |
|---|---|---|
| Rule splitter | `panels.py` as it is: tick-label axes, then gutters and letters | none |
| Heron | Docling's layout detector, run on the figure image; its `picture` boxes over 2 % of the figure that hold no other box | 0.05 s, local, 164 MB |
| Heron, then the rules' cut | Heron's boxes as seeds of the splitter's cutter (below) | same |
| FigEx2 as designed | its captioning model lists the panels by letter, its detector draws one box per listed letter | 8 s, local, 17 GB + 2.6 GB |
| FigEx2 detector, guided | the detector with the captioning model's features, boxes scored 0.5 or more | same |
| FigEx2 detector alone | the 93 MB detector without the captioning model, boxes scored 0.5 or more | 0.2 s, local |
| Gemma 4 26B | the step's overview call through Ollama | 5.5 s, local |
| Sonnet 5.5 | the same call through OpenRouter, reasoning effort high | 3.3 s, 1.0 cent |
| Gemini 3.8 Flash | the same call through OpenRouter, reasoning effort low | 5.3 s, 0.3 cent |
| Model, then the rules' cut | a model's boxes as seeds of the splitter's cutter | same as the model |

**The overview call** is not new. It is `overview_prompt` of the local
engine (`readers/vlm.py`): the figure image, the words printed in it with
their positions, and the request for one entry per chart with its box on a
0-1000 grid. All three models got it word for word.

**The rules' cut** is the splitter's own `_cut_between`: given one seed box
per chart, it cuts the figure along the widest ink-free band between two
seeds and trims each cell to its ink ([`scripts/cutter.py`](scripts/cutter.py)).

**Gemini's effort.** At effort high, as in round 4, Gemini took 232 seconds
and 9.8 cents for one single-chart figure (25,732 output tokens). That run
was stopped after six figures
([`extra/gemini-3-8-flash-effort-high.json`](extra/gemini-3-8-flash-effort-high.json))
and Gemini was run at effort low.

## Results

A figure is **cut right** when the splitter returns as many charts as the
figure has and every chart is found (its box overlaps the chart by half or
more, intersection over union). A chart is **whole in its box** when the
box also covers nine tenths of the chart as the truth drew it: the crop can
be read. A figure that is one chart is cut right by leaving it whole.

| Splitter | Figures cut right | Bench | Showcase | Other papers | Right chart count | Charts found | Whole in its box | USD |
|---|---|---|---|---|---|---|---|---|
| Rule splitter (today) | **24 of 51** | 9 of 10 | 5 of 11 | 10 of 30 | 26 | 165 of 236 | 135 | |
| Heron, boxes as they are | **24 of 51** | 5 of 10 | 10 of 11 | 9 of 30 | 26 | 126 | 92 | |
| Heron, then the rules' cut | **24 of 51** | 5 of 10 | 10 of 11 | 9 of 30 | 26 | 114 | 106 | |
| FigEx2 detector alone | **16 of 51** | 3 of 10 | 5 of 11 | 8 of 30 | 16 | 61 | 58 | |
| FigEx2 detector, guided | **18 of 51** | 3 of 10 | 6 of 11 | 9 of 30 | 18 | 64 | 61 | |
| FigEx2 as designed | **24 of 51** | 5 of 10 | 7 of 11 | 12 of 30 | 37 | 95 | 89 | |
| Gemma 4 26B (local) | **28 of 51** | 7 of 10 | 8 of 11 | 13 of 30 | 42 | 124 | 53 | |
| Sonnet 5.5 (cloud) | **49 of 51** | 10 of 10 | 11 of 11 | 28 of 30 | 51 | 218 | 145 | 0.53 |
| Gemini 3.8 Flash (cloud) | **49 of 51** | 10 of 10 | 11 of 11 | 28 of 30 | 50 | 234 | 134 | 0.16 |
| Gemma, then the rules' cut | **32 of 51** | 8 of 10 | 8 of 11 | 16 of 30 | 42 | 152 | 119 | |
| Sonnet, then the rules' cut | **47 of 51** | 10 of 10 | 11 of 11 | 26 of 30 | 51 | 214 | 188 | 0.53 |
| Gemini, then the rules' cut | **47 of 51** | 10 of 10 | 11 of 11 | 26 of 30 | 50 | 230 | 220 | 0.16 |

Reading it:

- Sonnet has the chart count right on all 51 figures and Gemini on 50. The
  one Gemini miss is W07, a hard call in the truth.
- Their misses are box misses on grids of 15 to 18 small charts (W05, W06).
- Gemma counts well (42) and places badly: 103 of its boxes pair with no
  chart.
- Round 3 graded the rule splitter by eye on the 30 other-paper figures: 7
  clean, 4 minor, 19 wrong. Measured here: 10 of 30 cut right.

The full tables, with a row per figure, are in [`results.md`](results.md).

### With a judge

"With a judge" is read here as: a splitter's cut is kept when the judge
finds the same number of charts, and the judge's cut is taken when it does
not. No truth is used in that choice.

| Splitter | Alone | With Heron | Agree with Heron (right) | With FigEx2 | Agree with FigEx2 (right) |
|---|---|---|---|---|---|
| Rule splitter | 24 | 24 | 20 (16) | 31 | 20 (20) |
| Heron | 24 | | | 26 | 22 (19) |
| FigEx2 as designed | 24 | 22 | 22 (17) | | |
| Gemma 4 26B | 28 | 20 | 25 (18) | 25 | 39 (24) |
| Sonnet 5.5 | 49 | 26 | 26 (26) | 37 | 37 (37) |
| Gemini 3.8 Flash | 49 | 26 | 26 (26) | 37 | 36 (36) |

- Overruling helps the two weak splitters with FigEx2 as judge (the rules
  24 to 31, Heron 24 to 26). It costs Gemma, and it costs the cloud models
  a quarter to a half of their figures, because the judge is then the weaker
  splitter of the two.
- Agreement is worth more than the overrule. Rules and FigEx2 agree on 20
  figures and the rules are right on all 20. Whenever a cloud model and a
  judge agree on the count, the cloud model's cut is right.
- So a detector's place in this step is to say "these two disagree, do not
  trust this cut", which today nothing says.

### A model's count as arbiter

The model only says how many charts there are. The rules' cut is taken
when it has that many charts, else Heron's, else the model's own boxes.

| Count from | Count right | Figures cut right | Bench | Showcase | Other papers | Rules' cut taken (right) | Heron's taken (right) | Own boxes (right) |
|---|---|---|---|---|---|---|---|---|
| Gemma 4 26B (local) | 42 | **35 of 51** | 10 of 10 | 10 of 11 | 15 of 30 | 22 (22) | 10 (7) | 19 (6) |
| FigEx2 captioning model | 38 | **31 of 51** | 8 of 10 | 9 of 11 | 14 of 30 | 20 (20) | 9 (6) | 22 (5) |
| Sonnet 5.5 (cloud) | 51 | **46 of 51** | 10 of 10 | 11 of 11 | 25 of 30 | 26 (24) | 10 (8) | 15 (14) |
| Gemini 3.8 Flash (cloud) | 50 | **46 of 51** | 10 of 10 | 11 of 11 | 25 of 30 | 26 (24) | 10 (8) | 15 (14) |

- This is the best cut that needs no cloud call: 35 of 51 with Gemma.
- Whenever the rules' cut has the count Gemma gives, it is right (22 of
  22). The losses are the 19 figures where neither the rules nor Heron has
  Gemma's count and its own boxes are used.
- For the cloud models the arbiter is a step back from their own boxes (46
  against 49).

### One rule for every method, scored afterwards

Written after the tables above were read, on the same 51 figures: a
reading of these results, not a test of them
([`scripts/score_one_rule.py`](scripts/score_one_rule.py), no model runs).
The reading model lists the charts. The rules' cut is taken when it has
that many charts; when it has not, the model's boxes are the seeds of the
rules' cutter.

| Chart list from | Crops from | Figures cut right | Whole in its box |
|---|---|---|---|
| Gemma 4 26B (local) | its own boxes | 28 of 51 | 53 |
| | measured arbiter (rules, Heron, own boxes) | 35 | 102 |
| | **the one rule** | **37** | **138** |
| | the one rule with Heron's cut between its steps | 37 | 140 |
| Sonnet 5.5 (cloud) | its own boxes | 49 | 145 |
| | its boxes as seeds, on every figure | 47 | 188 |
| | **the one rule** | **46** | **193** |
| | the one rule with Heron's cut between its steps | 45 | 187 |
| Gemini 3.8 Flash (cloud) | its own boxes | 49 | 134 |
| | its boxes as seeds, on every figure | 47 | 220 |
| | **the one rule** | **46** | **213** |
| | the one rule with Heron's cut between its steps | 45 | 206 |

- With a model's count in hand, Heron adds no figure for any of the three.
- Where the rule splitter and the model find a different number of charts,
  the model has the number right far more often:

| Model | Different count | Model's count right | Rules' count right |
|---|---|---|---|
| Gemma 4 26B (local) | 29 figures | 20 | 4 |
| Sonnet 5.5 (cloud) | 25 | 25 | 0 |
| Gemini 3.8 Flash (cloud) | 25 | 24 | 0 |

- Where the two find the same number, the rules' cut is right on 22 of 22
  figures with Gemma and on 24 of 26 with either cloud model.
- The local engine does the opposite today: charts the rules find by their
  tick labels stand whatever the model counts (`pipeline.py`, `_agree`).

## FigEx2

[FigEx2](https://arxiv.org/abs/2601.08026) (Song et al., EMNLP 2026) is two
models that work as one. A captioning model (Qwen3-VL-8B with the authors'
adapters) lists the panels of a compound figure by their printed letters
and writes a caption for each. A detector (DAB-DETR, 26 classes, the letters
A to Z) draws at most one box per letter, guided by the captioning model's
hidden states. It was trained on biomedical figures.

It was run the authors' way: their `inference.py` functions, their prompt,
greedy decoding, their pinned `transformers` 5.7.0 and `peft` in a separate
environment, images scaled to 1,024 px.

- **The captioning model counts panels fairly well:** right on 38 of 51
  figures, behind Gemma (42), Gemini (50) and Sonnet (51). It listed 15
  panels for the 15-chart grid, and three for a single forest plot.
- **The detector is unsure on charts.** Over 236 charts it scores 70 boxes
  at 0.5 or more. It can give one box per letter, so two panels it both
  takes for "A" get one box.
- **As designed** (a box for each listed letter) it has the right count on
  37 figures and cuts 24 right: the boxes it draws for unlettered panels
  are often not on a panel.
- **What it would cost to use:** a 17.5 GB base model beside the 2.6 GB of
  FigEx2, 8 seconds per figure, a second Python environment, and no licence
  stated in either repository.

### Its captioning model beside the readers of round 4

The readers of round 4 return the values of a chart. FigEx2's captioning
model was trained to write captions, but asked in plain words for a table
of values it answers with one. It was asked once per figure for the six
main figures of the showcase paper, and its tables were counted with round
4's own count (values paired by printed name, right within 5 % of the axis;
[`scripts/score_figex2_reader.py`](scripts/score_figex2_reader.py)).

| Figure | Values | FigEx2 captioning model: returned | right | `ollama`, Gemma 4 26B | `cloud`, Sonnet 5.5 | `cloud`, Gemini 3.8 Flash | `agent`, Sonnet 5.5 |
|---|---|---|---|---|---|---|---|
| S02, Figure 3 | 75 | 44 | 0 | 23 | 69 | 75 | 75 |
| S03, Figure 4 | 222 | 97 | 96 | 10 | 80 | 222 | 37 |
| S04, Figure 5 | 144 | 98 | 98 | 24 | 144 | 142 | 24 |
| S05, Figure 6 | 17 | 18 | 0 | 13 | 13 | 13 | 13 |
| S06, Figure 7 | 52 | 96 | 28 | 26 | 52 | 52 | 52 |
| S08, Figure S2 | 63 | 63 | 63 | 0 | 63 | 63 | 63 |
| All six | 573 | 416 | **285** | 96 | 421 | 567 | 264 |

The 285 overstates it. What it read and what it filled in:

- **Printed numbers, read:** 117. The 37 and 17 printed shares of Correct
  in Figures 4 and 5, and all 63 cells of the confusion matrix.
- **Filled in, not read:** 140. In the two stacked-bar figures it wrote 0.0
  for every small class (124 values) and 100 minus Correct for Incorrect
  (16). The true segments of Figure 5 are 0.6 to 2.8 points on average, so the count's
  5 % tolerance takes the zeros as right. Round 4 noted the same blind
  spot of that count for Gemini.
- **Estimated:** 28 of 52 points of the line charts in Figure 7, in round
  numbers.
- **Nothing right** on Figure 3 (repeated values such as 46, 46, 46) and
  Figure 6 (values under the wrong names).

So it copies printed numbers from a regular grid well and does not measure.
On that reading it stands between the local method (96) and the agent
(264), below both cloud calls.

This is not a run of the step: one plain question per figure, no prepared
context, no crops, no checks. Its answers are cut at 2,048 tokens, about 90
rows, because the authors' code generates without a cache and a longer
answer takes hours; Figures 4 and 5 are therefore read in part. The
answers are in
[`extra/figex2-captioner-as-reader.json`](extra/figex2-captioner-as-reader.json).

### Was its code safe to run

FigEx2 is third-party code and weights, run here on a machine that holds
unpublished papers and API keys. After the first runs a separate agent
reviewed everything, reading only, running nothing. Its verdict: **safe
with caveats, nothing malicious found.**

What was reviewed, and at which version:

| What | Version |
|---|---|
| The authors' code | commit `d95df2078060702486285af80fb30c79d2842bd8` |
| FigEx2-8B on Hugging Face | revision `65a135a0aa69164591c2ee4cbba886672fcc71b2` |
| Qwen3-VL-8B-Instruct | revision `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` |

- **Code:** `inference.py` and the captioning-model file were read in full.
  The detector file is a changed copy of the library's own DAB-DETR file;
  every changed hunk was read against `transformers` 5.7.0. The changes are
  the layers that feed the captioning model's features to the detector, and
  one loader that reads the detector's weights again from its own folder.
  No network call, no process or shell, no reading of the environment or
  of files outside the folders it is given, no hidden or encoded content.
- **Model files:** all seven weight files are plain `safetensors` tables
  (the format cannot carry code); no pickle file, no Python file, no
  `auto_map` in any config. All 30 files hash to what the hub recorded.
- **Caveats, and what was done about them.** The authors' loaders pass
  `trust_remote_code=True`. With these folders there is nothing for it to
  run, but it would run code if a model folder ever carried some, and one
  fallback in their detector loader could have asked the hub for a third
  repository. Our two wrapper scripts now refuse anything that is not a
  local folder, give the fallback the same local folder, and switch the
  hub libraries to offline mode before loading.
- **Not covered:** the libraries themselves (`transformers`, `peft`,
  `torch`), the state of the two repositories after these versions, and any
  run-time watching of the process. The process runs as the user, without
  a sandbox; a new download or a newer commit needs a new review.

## What this says for the step

As read when the check was done, before the final test:

1. **Cloud and agent methods:** take the charts from one overview call to
   the reading model and make the crops with the rules' cut from its boxes.
   On this set that is 47 of 51 figures cut right with 220 of 236 charts
   whole, against 24 and 135 today.
2. **Local method:** keep the overview call it already makes, and let its
   count choose between the rules' cut and Heron's: 35 of 51 against 24.
3. **Heron** as a second witness, not as the splitter.
4. **FigEx2:** leave it out.

Points 2 and 3 did not stand. The one rule above reaches 37 of 51 locally
without Heron, and the maintainer took Heron out. What holds is in "The
decision" at the top and in [`final-test/README.md`](final-test/README.md).

None of this is built. The check changes no engine code.

## Limits

- **One run per model.** Round 3 saw the same model return different
  counts for one figure in two runs.
- **Tuned on part of the set.** Heron's two rules were fixed on the 11
  showcase figures before the other 40 were run. The judge and arbiter
  rules were written before they were scored, and every combination that
  was tried is in the tables.
- **The truth is drawn by a model.** Blind, checked against 21 earlier
  counts and looked at, but a person has not drawn it. "Whole in its box"
  leans on the truth's edges more than "found" does.
- **Medical-AI papers only,** and 51 figures. The showcase paper's grey
  plot backgrounds are what makes Heron see its panels as pictures.
- **Gemini ran at low effort,** Sonnet at high. Sonnet at high barely
  thinks on this call (3 s); Gemini at high does not return in useful time.
- **FigEx2 off its ground.** It was trained on lettered biomedical panels.
  The image size and the 0.5 score cut are our choices; the authors score
  it by average precision, which needs neither.

## Files

| Path | What |
|---|---|
| `figures.json` | the 51 figures, where each comes from, the earlier chart count |
| `truth/` | the brief and one file per figure: the charts and their boxes |
| `candidates/` | what each splitter returned per figure (boxes on a 0-1000 grid) |
| `results.md`, `results.json` | every table, with a row per figure |
| `extra/` | the stopped Gemini run at effort high; FigEx2's captioning model asked for values; the one rule (`one-rule.json`) |
| `scripts/` | `build_set.py`, `truth_parts.py`, `draw_boxes.py`, `run_heron.py`, `run_vlm.py`, `run_figex2.py`, `cutter.py`, `score.py`, `score_one_rule.py`, the two FigEx2 reader scripts, and for the final test `final_sample.py`, `run_ruling.py`, `score_final.py` |
| `examples/` | three figures of the showcase paper, each with its cuts as box diagrams (`scripts/make_examples.py`) |
| `final-test/` | the final test: the caption in the list call, both cuts, a ruling call; its own README |
| `report-page/` | builds the private page of the check: every splitter on every figure, with the truth and each splitter's boxes drawn on the figure (`build.py`) |
| `figures/` | the figure images: the papers' artwork, git-ignored |

To score again: `uv run --no-sync python
docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/score.py`.
Each script's first lines say how to run it.

## Spend

- OpenRouter: 0.87 USD (Sonnet 0.53, Gemini at low effort 0.16, the
  stopped Gemini run at high effort 0.18).
- The final test: another 0.86 USD (Sonnet 0.67, Gemini 0.19).
- Five agents: four for the truth, one for the safety review of FigEx2's
  code.
- The FigEx2 downloads (17.5 GB for Qwen3-VL-8B-Instruct, 2.6 GB for
  FigEx2-8B) were outside the repository and are not needed again: FigEx2
  is out of the design. Its results stay in this report. To repeat its
  runs, fetch the three versions listed under "Was its code safe to run".
