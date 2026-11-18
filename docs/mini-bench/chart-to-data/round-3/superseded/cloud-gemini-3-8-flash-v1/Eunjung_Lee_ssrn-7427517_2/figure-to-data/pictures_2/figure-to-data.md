# Figure data: pictures_2 of Eunjung_Lee_ssrn-7427517_2 (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3. Paired physician-rating differences for overall quality and secondary quality domains. Points show model-estimated mean differences, and bars show 95% CIs. Positive values favor AI-generated summaries; negative values favor clinician-authored summaries.

**What the figure shows (model):** Forest plot of paired physician-rating differences showing model-estimated mean differences and 95% confidence intervals comparing AI-generated and clinician-authored summaries across five rating domains.

## Chart chart_1 (forest, horizontal)

x axis linear -1.5 to 1.5; y axis "Rating domain" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Overall quality |  |  | -0.12 | -0.89 | 0.65 |  | vlm | 0.8 |
| Clarity |  |  | 0.36 | 0.07 | 0.65 |  | vlm | 0.8 |
| Completeness |  |  | -0.84 | -1.35 | -0.33 |  | vlm | 0.8 |
| Accuracy |  |  | -0.35 | -0.66 | -0.04 |  | vlm | 0.8 |
| Readability |  |  | 0.73 | 0.22 | 1.24 |  | vlm | 0.8 |

- Note: Points show model-estimated mean differences, and bars show 95% CIs.
- Note: Positive values favor AI-generated summaries; negative values favor clinician-authored summaries.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-154055_cloud_google-gemini-3.8-flash.json`.
