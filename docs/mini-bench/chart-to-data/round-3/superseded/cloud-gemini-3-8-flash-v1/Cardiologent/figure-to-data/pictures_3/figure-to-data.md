# Figure data: pictures_3 of Cardiologent (page 7)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `google/gemini-3.8-flash`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 4: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) on the 20 -patient subset. The judge's agreement with each cardiologist ( 0 . 74 , 0 . 66 ) is comparable to the two cardiologists' agreement with each other ( 0 . 67 ): the judge agrees with a cardiologist about as closely as the two cardiologists agree with each other.

**What the figure shows (model):** Rater agreement (ICC(2,1), absolute agreement) with 95% confidence intervals comparing human-to-human raters and judge-to-rater agreements.

## Chart 1 (other, vertical)

x axis categorical; y axis "ICC(2,1), absolute agreement" linear 0.35 to 0.95.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| R1 ↔ R2 (human-human) |  |  | 0.67 | 0.52 | 0.79 |  | vlm | 0.8 |
| Judge ↔ R1 |  |  | 0.74 | 0.6 | 0.84 |  | vlm | 0.8 |
| Judge ↔ R2 |  |  | 0.66 | 0.51 | 0.78 |  | vlm | 0.8 |

- Note: Point estimate values are given in the paper caption (0.67, 0.74, and 0.66).
- Note: Error bars represent 95% confidence intervals, with values printed directly beside each whisker.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153843_cloud_google-gemini-3.8-flash.json`.
