# Judge summary

Verdicts per model (15 figures: 10 data charts, 5 without data).

| model | correct | partial | wrong | missed | true_negative | false_positive | usable figures | dominant failure |
|---|---|---|---|---|---|---|---|---|
| agent-sonnet-5-5 | 8 | 2 | 0 | 0 | 5 | 0 | 15 | MISSING_VALUES |
| cloud-gemini-3-8-flash | 7 | 3 | 0 | 0 | 5 | 0 | 14 | INTERVAL_BOUNDS |
| cloud-sonnet-5-5 | 10 | 0 | 0 | 0 | 5 | 0 | 15 | CATEGORY_LABELS |
| ollama-gemma4-26b-qat | 6 | 3 | 1 | 0 | 5 | 0 | 11 | GEOMETRY_MISMEASURED |

Figures on which each error type was assigned.

| error type | agent-sonnet-5-5 | cloud-gemini-3-8-flash | cloud-sonnet-5-5 | ollama-gemma4-26b-qat |
|---|---|---|---|---|
| AXIS_CALIBRATION | 0 | 0 | 0 | 1 |
| CATEGORY_LABELS | 0 | 0 | 3 | 2 |
| GEOMETRY_MISMEASURED | 2 | 1 | 1 | 4 |
| INTERVAL_BOUNDS | 0 | 3 | 1 | 3 |
| INVENTED_VALUES | 0 | 0 | 0 | 1 |
| MISSING_VALUES | 2 | 1 | 0 | 3 |
| OTHER | 0 | 0 | 0 | 4 |
| PANEL_STRUCTURE | 1 | 1 | 1 | 1 |
| SERIES_NAMES | 1 | 0 | 2 | 2 |
| VALUE_ASSIGNMENT | 0 | 1 | 1 | 0 |
| WRONG_KIND | 0 | 0 | 0 | 1 |

## Assessments

**agent-sonnet-5-5.** This run returned no wrong number of consequence: all 5 figures without data were declined with a stated reason, all 42 printed values (B1, B3, C5) are exact, and every value read from geometry that it returned is within 2.7 % of its axis range, most far closer (B2's 90 line points average 0.2 %, C3's 264 stacked segments 0.15 points, C1's bars 0.3 %). Its typical failure is omission, not misreading, and it says so in `uncertain`: it skipped the 90 raw dots behind B2's lines and nulled 4 of B5's 30 medians where the median line lies on a box edge. The remaining measurement error is small and local: the boundary between the two hatched classes of C3's stacked bars (up to 2.7 points, with 0.1-1.1 point slivers in classes that are empty) and a constant +0.05 on C4's bars. The two large penalties in the automatic score are not value errors: B2's series are named 'Smoothed ...' instead of the panel title, and the saved box of C4's panel (a) spans the whole figure, so correct values count as missing plus extra. It can be trusted on every chart kind in this set (printed-label bars and pies, plain bars, interval and forest plots, lines, box plots, stacked bars), provided a consumer reads `uncertain` for what was left out and treats sub-point stacked slivers and edge-coincident box medians as approximate.

**cloud-gemini-3-8-flash.** The run never returns values for a figure without data (5 of 5 true negatives, each with a 'not a data chart' reason) and reads printed numbers without one error (B1, B3, C5 and the CI labels of A3: 48 of 48), with legend, category and panel names verbatim. Bar heights and point estimates read from mark positions are within about 1 % of the axis range (A3, B4, C1, C4), and no figure is wrong, missed or hallucinated. Its recurring weakness is the secondary statistics of a mark: a box median taken at the wrong box edge when no median line is visible (B5, one value 10 % of the range off), a CI widened by 2.8 % (B4), a whisker put at the quartile (C4). Its most damaging single failure is different and silent: in the 264-segment stacked chart C3 one segment boundary is shifted 6-10 points in 12 of 44 bars while every bar still sums to 100 and nothing is declared. The two automatic zeros are not reading errors: B2 traces the line within 0.7 % but leaves the series unnamed, drops 2 of 30 vertices per panel (shifting the later points) and omits the raw dots, and C4 has correct numbers under mislocated panel boxes; axis ranges and panel boxes are the weak part of the record, not the values. It can be trusted on printed-value charts, simple bars, forest plots and pies; dense stacked bars, box-plot medians and the point count of long unlabelled lines need a check.

**cloud-sonnet-5-5.** All ten data charts came back with every one of the 560 truth values within 5 % of the axis range (556 within 2 %), and all five diagrams and ECG figures were declined with a stated 'not a data chart' reason, so the run neither hallucinates nor misses a chart. Printed numbers (B1, B3, C5) are exact and values measured from marks are tight even on dense figures: 180 line and dot points in B2 within 0.8 %, 264 stacked segments in C3 within 1.3 %, forest centres and CI bounds in B4 within 0.3 %. The only values beyond 2 % are four box-plot medians in B5 that the figure does not draw as a separate line (up to 4.8 %), and in C3 hatched slivers of about one point are split between neighbouring rating classes. What goes wrong is labelling and structure metadata, at cosmetic level: categorical axis tick lists taken over from the layout/OCR pre-pass disagree with the correct row categories in three figures (the most frequent defect, hence the dominant code), and the run's own series names on a legend-less figure (B2) and a full-figure box for both panels (C4) defeat the scorer's pairing, so the automatic score reports 188 missing values that are in fact right. For the values themselves the run can be trusted on bar, grouped-bar, line, forest, pie, stacked-bar and box charts; medians of boxes whose median coincides with an edge and sub-1.5 % slivers should be treated as approximate, and a consumer should key on the row categories, not on the axis tick lists or the panel boxes.

**ollama-gemma4-26b-qat.** The run never invents data for a non-chart (all five diagrams and ECG traces declined with a one-line reason) and it transcribes printed numbers without a single error (B1 12 of 12, B3 15 of 15, C5 15 of 15); simple charts with a handful of marks per panel are also read well (C1 12 bars within 0.3 % of the axis, A3 and B4 within tolerance). It fails where many values must be located on the marks: box medians snap to whole numbers or tick values and the whiskers are lost (B5: 7 of 30 medians beyond 5 %, whisker ends null or collapsed to one value in 26 of 30 boxes), a dense line chart comes back as an unkeyed, miscounted sequence of the raw dots without the smoothed line (B2), and the stacked bars of C3 yield 58 numbers of which 45 exceed 100 % and none is a segment share. The vector path of C4, used without a model reading, is geometrically exact but structurally wrong: box outline vertices returned as a 'line' series under truncated labels, colour codes for series names, and the white-filled series dropped. Labels and metadata are weak even on correct figures (panel titles missing or scrambled in B3 and C5; the axis range taken from the tick labels that were read, so correct values beyond the last tick are flagged in B1 and C1), and its own checks expose C3 (61 issues, all confidences <= 0.55) but not C4's box panel (confidence 0.9) or B2, with no partial reading declared in `uncertain`. Trust it on figures with printed values, pies, and simple bar or interval charts; do not take its numbers from box plots, stacked or multi-series bars or dense line charts. The 11 usable figures are the 6 correct data charts plus the 5 true negatives, and the 4 OTHER codes are cosmetic label or metadata defects.

