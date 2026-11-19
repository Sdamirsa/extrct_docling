# The final test: the caption, both cuts, a ruling call

19 November 2026. The last part of the split check
([`../README.md`](../README.md)), run to decide what the step should do.

## What was tested

The check left one rule standing ("the one rule"): the reading model lists
the charts of a figure; the rule splitter's cut is taken when it has that
many charts, and when it has not, the rules' cutter is started from the
model's boxes. The maintainer asked for two additions to be tried against
it, with one local and one cloud configuration to come out:

1. **The figure's caption.** The prepare phase has the caption of every
   figure the conversion found one for, and the readers get it when they
   read values. The call that lists the charts has never been given it.
   Here it is added to that call.
2. **Both cuts, and a ruling.** The raw rule split is kept beside the cut
   made from the model's list. Where the two are the same cut, it is
   taken. Where they differ, a second call shows the model both, drawn on
   the figure, and asks for a number and a boolean: how many charts the
   figure has, and whether the first drawing is the right cut.

Docling's layout detector (Heron) and FigEx2 are out, by the maintainer's
decision after the first part.

Three models: Gemma 4 26B through Ollama (fully local), Sonnet 5.5 and
Gemini 3.8 Flash through OpenRouter (Gemini at low reasoning effort).
Truth: that of the check, unchanged.

**The sample.** A figure is tricky when the rule splitter cuts it wrong, or
the rules' cutter started from the list of any of the three models does
([`sample.json`](sample.json)): 34 of the 51 figures. The local model ran
on all 51. The two cloud models ran on the 34; their recommended
configuration needs no new run on the other 17, which the first part
already has.

## The answer

- **Neither addition earns its place.** No result moved by more than one
  or two figures, in either direction.
- **The caption does not improve the count.** 47 of the 51 figures have
  one. With it in the list call, the number of charts is right on 41
  figures instead of 42 for Gemma, on 32 of 34 instead of all 34 for
  Sonnet, and on 33 either way for Gemini. Captions name panels, and a
  panel is often several charts.
- **The ruling call has almost nothing left to win.** One of the two cuts
  is right on 39 of 51 figures locally and on 47 with a cloud model, as
  the maintainer saw. The number of charts already picks the right one on
  37 and 46.
- **The cloud models rule well, Gemma's boolean does not.** Where exactly
  one cut is right, Sonnet picks it on 20 of 22 figures and Gemini on 22
  of 23, for a second call on three figures in four. Gemma picks it on 20
  of 22 without the caption and on 17 of 25 with it.
- **The ruling does not flag the figures nobody cuts right.** Where both
  cuts are wrong, its number fits one of the two wrong cuts nearly always
  (it fits neither on 1 of 5 for Sonnet, 0 of 3 for Gemini, 2 of 10 and 3
  of 12 for Gemma).

## Recommended

| | Fully local | Cloud |
|---|---|---|
| Model that lists the charts | Gemma 4 26B, in the overview call the local engine already makes | the reading model, in one extra call: Sonnet 5.5 by default |
| Then | the one rule | the one rule |
| Caption in the list call | no | no |
| Ruling call | no | no |
| Figures cut right, of 51 | 37 (24 today) | 46 (24 today) |
| On the 34 tricky figures | 20 (7 today) | 29 (7 today) |
| Charts whole in their crop, of 236 | 138 (135 today) | 193 |
| One figure takes | 5.5 s | 3.3 s and 1.0 cent |

Gemini 3.8 Flash at low reasoning effort is the alternative for the cloud
list call: the same 46 of 51, more charts whole (213 of 236), 5.3 s and
0.3 cent. At high effort it does not answer in useful time, so it needs
its own effort setting.

## Results

Figures cut right. "By its number": the same ruling call, read by the
number of charts it answers instead of its boolean. "Ceiling": the figures
on which one of the two cuts is right, which no ruling can exceed.

### Local: Gemma 4 26B

| Cut from | All 51 | Tricky (34) | Easy (17) | Charts whole, of 236 |
|---|---|---|---|---|
| Rule splitter alone (today) | 24 | 7 | 17 | 135 |
| **No caption: the one rule** | **37** | **20** | **17** | **138** |
| No caption: both cuts, a ruling where they differ | 37 | 20 | 17 | 168 |
| No caption: the ruling read by its number | 38 | 21 | 17 | 168 |
| Caption: the one rule | 38 | 21 | 17 | 115 |
| Caption: both cuts, a ruling where they differ | 33 | 17 | 16 | 149 |
| Caption: the ruling read by its number | 37 | 21 | 16 | 155 |
| Ceiling, no caption | 39 | 22 | 17 | |
| Ceiling, caption | 41 | 24 | 17 | |

### Cloud: Sonnet 5.5, the 34 tricky figures

| Cut from | Figures cut right | Charts whole, of 195 |
|---|---|---|
| Rule splitter alone (today) | 7 | 99 |
| **No caption: the one rule** | **29** | **157** |
| Caption: the one rule | 28 | 165 |
| Caption: both cuts, a ruling where they differ | 27 | 163 |
| Caption: the ruling read by its number | 27 | 162 |
| Ceiling, no caption / caption | 30 / 29 | |

### Cloud: Gemini 3.8 Flash, the 34 tricky figures

| Cut from | Figures cut right | Charts whole, of 195 |
|---|---|---|
| Rule splitter alone (today) | 7 | 99 |
| **No caption: the one rule** | **29** | **177** |
| Caption: the one rule | 29 | 169 |
| Caption: both cuts, a ruling where they differ | 29 | 171 |
| Caption: the ruling read by its number | 30 | 172 |
| Ceiling, no caption / caption | 30 / 30 | |

### What the caption does to the chart list

| The chart list of | Figures | Count right, no caption | with caption | Own boxes cut right, no caption | with caption |
|---|---|---|---|---|---|
| Gemma 4 26B | 51 | 42 | 41 | 28 | 25 |
| Sonnet 5.5 | 34 | 34 | 32 | 32 | 29 |
| Gemini 3.8 Flash | 34 | 33 | 33 | 32 | 29 |

### The ruling call

| The ruling of | List | Asked | One cut right: picked it | by its number | Neither right: its number fits neither | Seconds a call | USD |
|---|---|---|---|---|---|---|---|
| Gemma 4 26B | no caption | 35 of 51 | 20 of 22 | 21 of 22 | 3 of 12 | 2.0 | local |
| Gemma 4 26B | caption | 36 of 51 | 17 of 25 | 21 of 25 | 2 of 10 | 2.0 | local |
| Sonnet 5.5 | caption | 27 of 34 | 20 of 22 | 20 of 22 | 1 of 5 | 4.6 | 0.28 |
| Gemini 3.8 Flash | caption | 26 of 34 | 22 of 23 | 23 of 23 | 0 of 3 | 6.0 | 0.07 |

The numbers of every table, with a row per figure, are in
[`results.json`](results.json); [`results.md`](results.md) is what the
scorer prints.

## What stays wrong

With the recommended cloud configuration five figures of the 51 are cut
wrong: W05, W10 and W16 (grids of 14 to 18 small charts) and W02 with
either model, W06 (15 charts) with Sonnet, W07 (a hard call in the truth)
with Gemini. With the local one, 14: these and other figures on which
Gemma lists too few or too many charts.

One example of what a ruling can cost: on W09 Sonnet listed the two
charts, and its cut was right. Shown the rule splitter's five boxes, three
of them on the blocks of a workflow drawing, it answered five charts and
took that cut.

## Limits

- **One run per model and variant.** The six local variants lie between 33
  and 38 of 51; a difference of one or two figures between two rows says
  nothing. What the test supports is that neither addition is a clear
  gain, not that either is a loss.
- **The same 51 figures as the first part,** on which the one rule was
  written. The tricky sample is the set of figures today's splitters fail
  on, so it says little about figures of another kind.
- **The cloud models did not run the 17 easy figures** with the caption or
  the ruling. Locally the caption broke none of them; the ruling broke one,
  in the run with the caption.
- **Two cuts count as different** when they have another number of boxes
  or a box of one overlaps its partner in the other by less than half.
  That asks the ruling on 26 to 36 figures; a looser rule would ask less.
- **The ruling prompt was written once** and not tuned.

## Files

| Path | What |
|---|---|
| `sample.json` | the 34 tricky and 17 easy figures, and which splitter fails on each |
| `rulings/` | every ruling call: what was drawn first, the number and the boolean |
| `results.json`, `results.md` | the tables, and a row per figure and variant |
| `../candidates/<model>-caption.json`, `-caption-cut.json` | the chart lists with the caption, and the cutter started from them |
| `../candidates/<model>-recommended.json` | the cut of the recommended configuration, all 51 figures |
| `../candidates/<model>-final.json` | the cut of the tested design (caption, both cuts, ruling) |
| `../scripts/final_sample.py`, `run_vlm.py --caption`, `run_ruling.py`, `score_final.py` | how each was made |

To score again: `uv run --no-sync python
docs/mini-bench/chart-to-data/round-4-plus-splitter/scripts/score_final.py`.

## Spend

0.86 USD on OpenRouter: Sonnet 0.67 (34 list calls 0.39, 27 rulings 0.28),
Gemini 0.19 (0.12 and 0.07). The local runs took about ten minutes.
