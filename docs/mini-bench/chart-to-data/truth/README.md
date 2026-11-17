# Frontier truth

What each of the 15 figures really shows, as `extrct.figure-data/1` JSON (the
schema the engine writes, so truth and prediction are scored by the same
code). Made on 2026-11-17 by three fresh `claude-fable-5-2` sub-agents, one
per part (A, B, C), with the prompts in `PROMPT-A-cardiologent.md`,
`PROMPT-B-others.md` and `PROMPT-C-more.md`.

Rules the agents worked under:

- no access to any model output, and not to the VLM description of a figure;
- numbers printed in a figure are `source: "printed"` (confidence 1.0);
  values read from vector geometry are `"vector"`; values measured on the
  figure's embedded bitmap at native resolution are `"raster"`, with the axis
  calibrated on at least three ticks and the residual reported;
- the paper's own text and tables are used as a cross-check, never as the
  source of a value the figure does not show;
- a figure without plotted or printed data values gets `"panels": []`;
- every file validates against `tools/figure-labeler/validate.py` and the
  engine's `ChartData` model.

## The files

| id | file | panels | kind | values | source | check |
|---|---|---|---|---|---|---|
| A1 | `Cardiologent__pictures_0.json` | 0 | no data (deployment schematic) | 0 | | |
| A2 | `Cardiologent__pictures_2.json` | 0 | no data (pipeline diagram) | 0 | | |
| A3 | `Cardiologent__pictures_3.json` | 1 | other (vertical interval plot) | 3 centres + 6 printed bounds | raster | axis fit residual ≤ 0.00014; centres ±0.001; paper text states 0.67, 0.74, 0.66 |
| A4 | `Cardiologent__pictures_4.json` | 0 | no data (architecture schematic) | 0 | | |
| A5 | `Cardiologent__pictures_5.json` | 0 | no data (ECG traces with shaded spans) | 0 | | |
| B1 | `Dynamic-Specialist-MAS__pictures_1.json` | 1 | grouped_bar | 12 | printed | bar tops measured within 0.38 cases of the labels; each group sums to 420 |
| B2 | `Med-RwR__pictures_6.json` | 3 | line | 180 (30 line points + 30 raw dots per panel) | raster | residual ≤ 0.0013 / 0 / 0.07; line point = mean of two dots within 1 px |
| B3 | `EchoAgent-EHM__pictures_4.json` | 5 | line (printed AUROC per curve) | 15 | printed | the text states EchoAgent's three values |
| B4 | `Eunjung_Lee_ssrn-7427517_2__pictures_2.json` | 1 | forest | 5 centres + 10 bounds | raster | residual ≤ 0.0006; the paper's table states the same 15 numbers within 0.005 |
| B5 | `RiskAgent_Synergizing_Language_Models_with_Validated_Tools_for__pictures_7.json` | 10 | box | 30 medians + whisker ends | raster | per-panel residual ≤ 0.008; reproduces the paper's table means within 0.043 |
| C1 | `HeartAgent__pictures_5.json` | 4 | bar | 12 | raster | residual ≤ 0.0003; three accuracies in the text reproduced within 0.0005 |
| C2 | `AgentMD__pictures_4.json` | 0 | no data (inference flow schematic) | 0 | | |
| C3 | `AMIE-Mx__pictures_14.json` | 3 | stacked_bar | 264 (58 are zero) | raster | residual ≤ 0.006 %; every bar sums to 100 %; segments are multiples of 1/300 |
| C4 | `Zodiac__pictures_5.json` | 2 | box, grouped_bar | 24 | vector | residual ≤ 0.0003; the bars equal the paper's results table |
| C5 | `AMIE-Cardiology__pictures_3.json` | 3 | pie | 15 | printed | wedge areas equal the labels within 0.05 points; identical to the 2026-11-09 truth |

560 values in 33 panels of 10 data figures; 5 figures hold no data.

## Conventions that affect scoring

- **Intervals** (A3, B4): centre in `value`, bounds in `err_lo` / `err_hi` as
  absolute axis values. The scorer compares `value` only.
- **Box plots** (B5, C4): `value` is the median, `err_lo` / `err_hi` the
  whisker ends; quartiles and outliers are in the panel notes.
- **A3** is `other`, not `forest`: the scorer reads a forest plot's values on
  the x axis, and this one is vertical. A prediction of `forest` or `scatter`
  counts as a kind mismatch, not a data error.
- **B2** prints no x ticks: x is the point's ordinal position 1..30, the line
  is named after the panel title and the dots `<title> (raw points)`. A
  prediction keyed otherwise does not pair.
- **B3** records each curve's printed AUROC (category = EF class as printed,
  one series `AUROC`); the curves are not traced.
- **C3** has one category per bar (`<item> - AMIE`, `<item> - PCP`) and the
  rating level as series.
- **C5** pies have no series.

## Known limits

- **B5:** in 11 of 30 boxes the median coincides with a box edge and is not
  drawn separately. Those rows were settled with the paper's table (8) or are
  within 0.25 units either way (3); they carry confidence 0.75 and are listed
  under `uncertain`. A model reading the figure alone can be off by up to
  10 % of the axis range there.
- **A3:** the text says 0.66 for one point that is plotted at 0.666; the
  truth keeps the plotted value.
- **C4:** the bundle's crop of this figure draws three rasterised patches of
  the box-plot panel upside-down (a rendering defect of the conversion, not
  of the paper), which shows a bar at about 0.04 that the PDF does not have.
  The truth follows the PDF, so a model that reads the crop faithfully is
  marked wrong on that box by 0.09 of the axis range.
- **Scorer name matching:** names within a normalised edit distance of 0.2
  count as equal and matching is first-fit. Distinct labels collide in C3
  ("Very favorable" / "Very unfavorable"), in one pie of C5 and among B1's
  legend entries, so the automatic numbers for these figures depend on row
  order. The judge pass separates naming mismatches from wrong numbers.
