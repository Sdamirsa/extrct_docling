# Judge summary

Verdicts per model (15 figures: 10 data charts, 5 without data).

| model | correct | partial | wrong | missed | true_negative | false_positive | usable figures | dominant failure |
|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5-blind | 7 | 3 | 0 | 0 | 5 | 0 | 14 | MISSING_VALUES |
| gemma4_26b-a4b-it-q8_0 | 5 | 3 | 2 | 0 | 5 | 0 | 10 | MISSING_VALUES |
| gemma4_26b-a4b-it-qat | 6 | 3 | 1 | 0 | 5 | 0 | 11 | GEOMETRY_MISMEASURED |
| gemma4_31b-it-q8_0 | 3 | 5 | 2 | 0 | 5 | 0 | 8 | MISSING_VALUES |

Figures on which each error type was assigned.

| error type | claude-sonnet-5-5-blind | gemma4_26b-a4b-it-q8_0 | gemma4_26b-a4b-it-qat | gemma4_31b-it-q8_0 |
|---|---|---|---|---|
| AXIS_CALIBRATION | 0 | 1 | 1 | 0 |
| CATEGORY_LABELS | 1 | 4 | 1 | 1 |
| GEOMETRY_MISMEASURED | 1 | 2 | 4 | 5 |
| INTERVAL_BOUNDS | 1 | 3 | 2 | 2 |
| INVENTED_VALUES | 0 | 1 | 1 | 1 |
| MISSING_VALUES | 2 | 3 | 3 | 4 |
| OTHER | 0 | 3 | 2 | 2 |
| PANEL_STRUCTURE | 1 | 0 | 1 | 0 |
| SERIES_NAMES | 2 | 3 | 2 | 3 |
| VALUE_ASSIGNMENT | 0 | 0 | 0 | 1 |
| WRONG_KIND | 0 | 1 | 1 | 1 |

## Assessments

**claude-sonnet-5-5-blind.** The run rejects all five figures without data and returns nothing invented: paired by meaning, 290 of the 560 truth values come back, 289 within 5 % and 286 within 2 % of the axis range, with every printed number (B1, B3, C5, the A3 bounds) exact and unlabelled marks (C1 bars, B4 forest, C4 boxes, B2 line) typically within 0.5 %. Its typical failure is leaving out part of a dense figure and saying so: the 90 raw dots of B2 and four of the six rating levels in C3 (180 values) account for all 270 values not returned, and only C3 is unusable as it stands. The one real misreading is in B5, where the median of boxes without a separately drawn median line was put on the wrong box edge (76.0 for 73.25), a case the truth itself calls undecidable from the pixels. The automatic scorer understates this run badly (0 matches on B2, B3 and C3, 10 of 15 on C5) because of layout choices only: series named 'smoothed', the EF class or the arm placed in the series field, pie boxes without legend. It can be trusted on printed-label charts, single-series bars, forest and interval plots and for the decision chart versus diagram; multi-series stacked bars and overlaid raw points need a completeness check. One caveat for whoever compares runs: the agreement on unlabelled marks is finer than one pixel of the supplied crops (B2 about 0.25 px, C4 whiskers about 0.3 px) although the notes say 'by eye', so the values were evidently measured rather than estimated; the B5 edge choices show they were not copied from the truth.

**gemma4_26b-a4b-it-q8_0.** The run is reliable at the two ends of the set: it declined all five figures without data with a sensible reason and never produced values for a diagram, and it returned every number exactly where the figure prints it (B1 counts, B3 AUROCs, C5 pie percentages, A3 CI bounds) or where a simple bar or point sits on a clean axis (C1 within 0.3 % of the range). It fails on dense figures by returning a fraction of the data in a shape that cannot be keyed: 24 of 180 line points without x positions in B2, one number per item instead of 264 stacked segments in C3 (with 137-175 % on a 0-100 axis), and in the vector figure C4 correct geometry under hex-colour series names and truncated tick labels, with a box plot typed as a line and a legend swatch read as a bar. Measured marks without printed labels are approximately right but not precise: forest centres off by up to 0.10 on a 3.1 range (B4) and 4 of 30 box medians beyond 5 % (B5), and interval or whisker bounds are missing, collapsed or wrong in every figure that needs them measured. A recurring cosmetic defect is an axis range that drops the lowest tick (B1, B4, C3), which triggers false 'outside the axis range' warnings on correct values. Its numbers can be taken as they are for figures with printed values and for simple single-series bar panels; line traces, stacked bars, box plots and measured confidence intervals need another reader or a check.

**gemma4_26b-a4b-it-qat.** This run is reliable at deciding what is a chart and at copying printed numbers: all five no-data figures were declined with a sensible reason and no data chart was declined, and every figure whose values are printed (B1 counts, B3 AUROCs, C5 pie percentages, A3 CI bounds) is exact, as are the plain bar heights of C1 (within 0.002). It fails where values must be measured from marks on a raster without printed labels: positions scatter rather than shift (B4 Overall quality -0.275 for -0.152, B5 seven of 30 medians off by more than 5 % of the axis), box whiskers are missing or collapsed to one number (B5), and a dense line chart comes back as an unkeyed list with the wrong number of points (B2). The two severe cases are structural: the stacked bars of C3 are read on a mis-calibrated axis with no rating-level series, giving values up to 182 on a 0-100 % scale, and the vector figure C4 has accurate geometry but returns a box plot as a 'line', drops one of two bar series and names the other by its hex colour. Panel splitting itself was right on every multi-panel figure except C3's third panel, which swallowed the legend. Trust it on charts with printed values, simple bar charts and pies; treat box plots, stacked bars and unlabelled line or interval plots as needing a check, and note that two of the six 'correct' figures (B3, C5) lose or scramble panel titles.

**gemma4_31b-it-q8_0.** The run is reliable on what it refuses and on what is printed: all five figures without data were declined with a correct one-line reason and nothing invented, and every printed number it returned is exact (the three pies, the 15 AUROC values, the 7 bar counts it got to, the CI bounds of the ICC plot). The most damaging failure is data lost to replies cut at the time or length limit: B1 stops after 7 of 12 bars, B2 keeps 15 of 180 points and C3 9 of 264, so the dense figures (long line series, stacked bars with many segments) come back as fragments, and the fragments of B2 and C3 are also wrong or unlabelled. The most frequent failure is mark positions read with scatter rather than a systematic shift: clean single-series bars are within 0.3 % of the range (C1), but forest and box plots land within 2-5 % for the centres with some outliers up to 10 % and with unreliable or missing interval bounds (B4, B5), and traced ROC points fall on the wrong curve (B3). On the vector figure C4 the measured numbers are right but arrive under colour codes, truncated categories and the wrong kind, with one of two bar series missing. It can be trusted for diagrams (as a filter), for charts whose values are printed, and for simple bar panels; it should not be used as is for interval plots, box plots, multi-series vector charts or any figure with more than a dozen marks per panel.

