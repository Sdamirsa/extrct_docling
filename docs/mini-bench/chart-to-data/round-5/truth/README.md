# Truth, round 4

What six figures of the showcase paper really show, as `extrct.figure-data/1`
JSON. Made on 2026-11-19 by three fresh `claude-fable-5-2` sub-agents, one
per part, with the prompt in [`PROMPT.md`](PROMPT.md), while the four
pipeline runs of the round were under way. The rules are those of the
earlier rounds ([`../../truth/README.md`](../../truth/README.md)): no
access to any model output or to a figure's VLM description; printed
numbers are `printed`, everything else is measured on the figure's bitmap
with the axis calibrated on its ticks; the paper's text and tables are a
cross-check, never a source.

The other six chart candidates of the paper (S09 to S14) hold thousands of
values each and have no truth here; five of them have a sample of printed
labels in [`../truth-sample/`](../truth-sample/).

## The files

| id | file | charts | kind | values | source | check |
|---|---|---|---|---|---|---|
| S02 | `Public-test-manuscript__pictures_2.json` | 4 | grouped bars (a, c), intervals (b, d) | 75 centres, 56 interval ends | raster | tick-fit residual at most 0.07; b and d reproduce the paper's Tables S5 and S3 within 0.013 and 0.003, a and c Tables S2 and S4 within 0.07 |
| S03 | `Public-test-manuscript__pictures_3.json` | 1 | stacked bars, 37 bars of 6 classes | 222 (78 are zero) | 37 printed, 185 raster | residual 0.012 points; 36 bars sit on the 1/300 grid within 0.046; every bar ends at 100; redrawing the bars from the file reproduces the bitmap pixel for pixel |
| S04 | `Public-test-manuscript__pictures_4.json` | 1 | stacked bars, 24 bars of 6 classes | 144 (55 are zero) | 24 printed, 120 raster | residual 0.002 points; measured Correct within 0.10 of the printed share; every bar ends at 100 ± 0.09 |
| S05 | `Public-test-manuscript__pictures_5.json` | 2 | line (a), scatter (b) | 13 printed, 4 without a value | printed | markers confirm the labels within 0.08 |
| S06 | `Public-test-manuscript__pictures_6.json` | 4 | line with a shaded range | 52 averages, 104 range ends | raster | nine-tick fit residual at most 0.09 points; averages within 0.07 of k/108 |
| S08 | `Public-test-manuscript__pictures_8.json` | 1 | heatmap (confusion matrix 9 × 7) | 63 (51 are zero) | printed | counts sum to 100; the colours reproduce every count within 0.1; the text states 100 answers, 83 extracted |

573 values in 13 charts.

**Two truths of the same figure agree.** S04 and S06 are also in the
five-figure smoke set of the engine's tests (`tests/data/figure_data/truth/`
F1 and F2, made on 2026-11-09 by another agent from an older conversion).
The agent of this round did not read those values. Scored against each
other, all 144 values of S04 pair and agree within 2 % of the axis (mean
difference 0.0002 of the range); of S06, 40 of 52 pair (the older file
keys the temperature as a tick label, so "0", "1" and "2" do not pair with
0.0, 1.0 and 2.0) and all 40 agree within 2 %.

## Conventions that affect scoring

- **Keying.** A point is keyed as the readers are told to key it
  (`docling/engines/figure_data/reading.py`, `CONVENTIONS`): category = the
  tick label as printed, series = the legend entry, x on a numeric axis.
- **S03 and S04 are one chart each.** One axes frame, one x axis, one
  legend; the blocks of bars are separated by an empty row only. A reading
  that splits the figure into blocks pairs with the truth only where its
  box overlaps the whole chart by more than half.
- **Category names as printed**, the figure's own misspelling included
  ("Claude3-Hiaku Web" in S03, "GeminiAdvanced Web- direct image" in S04).
- **Names that collide.** The scorer treats two names as the same when they
  differ by less than a fifth of their length. Many bar labels of S03, S04
  and S02 do ("Claude3-Sonnet Web" / "Claude3-Sonnet API", the six
  "Candidate N", most "... Poe" labels), so pairing then follows row order.
  The truth lists rows in figure order; a correct reading in another order
  loses pairs (S03 shuffled: 188 of 222 within 2 %).
- **EOP is drawn in the plot's background grey** in S03 and S04: an EOP
  segment shows as a gap in the bar. The truth records the gap as EOP.
- **Intervals** (S02 b, d): centre in `value`, ends in `err_lo` / `err_hi`.
  The scorer compares `value` only.
- **S06**: x is the temperature as a number, category null, one series
  "Average"; the range's edges are in `err_lo` / `err_hi`. A reading that
  writes the tick label as category pairs 40 of 52 for the reason above.
- **S05 a** is keyed by x = 2021, 2022, 2023; a reading that writes the
  year as a category does not pair.
- **S08**: category = the row label (human validation), series = the
  column label (extracted option); normalised by the data span 0 to 25.

## Known limits

- **S05 b has four rows without a value.** The figure and the paper do not
  say which of 12.35 and 9.26 is babbage-002 or davinci-002, nor which of
  43.83 and 39.51 is GPT3.5-Instruct or GPT3.5-0613 (same colour, same
  date). The rows are kept with a null value, so a perfect reading pairs 13
  of 17.
- **S05 a, legend.** As printed, blue (71.59, 63.58, 70.35) is "GPT-3.5
  Turbo 0125" and orange "GPT-4 0613"; the paper's text and panel b say the
  opposite. The truth follows the figure.
- **S02 c**: the "MT: 512plus" bars are drawn as copies of the "MT: 1024"
  bars in 12 of 13 groups and differ from the paper's Table S4 in 9 rows.
  **S02 d**: two rows are plotted at other values than Table S3 states, and
  two rows show no error bar. The truth keeps what is drawn.
- **S03**: "Llama2-13b-Q5 Local" is off the 1/300 grid (33.4 printed; it
  fits 100 and 101 of 299). Recorded as measured, confidence 0.9.
- **S04**: two bars fit denominators of 134 and 128 instead of 138; kept as
  measured.
- **S06**: two upper range ends lie under a legend box and are extrapolated
  (confidence 0.9). The y tick labels are truncated integers of multiples
  of 8.333.
- The markers beside some bars of S03 (quantized, fine-tuned) and the
  significance column of S04 are not data values and are in the notes only.
