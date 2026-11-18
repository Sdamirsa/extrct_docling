# Figure data: pictures_3 of Cardiologent (page 7)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 4: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) on the 20 -patient subset. The judge's agreement with each cardiologist ( 0 . 74 , 0 . 66 ) is comparable to the two cardiologists' agreement with each other ( 0 . 67 ): the judge agrees with a cardiologist about as closely as the two cardiologists agree with each other.

**What the figure shows (model):** The figure shows the Rater agreement (ICC(2,1), absolute agreement, with 95% CI) on a 20-patient subset for three comparisons: R1 ↔ R2 (human-human), Judge ↔ R1, and Judge ↔ R2.

## Chart 1: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) (forest)

y axis linear 0.4 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| R1 ↔ R2 (human-human) |  |  | 0.67* | 0.52 | 0.79 |  | agent | 0.5 |
| Judge ↔ R1 |  |  | 0.74* | 0.6 | 0.84 |  | agent | 0.5 |
| Judge ↔ R2 |  |  | 0.66* | 0.51 | 0.78 |  | agent | 0.5 |

- Note: Center values for the intervals are taken from the figure caption.

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-115854_agent_gemma4-26b-a4b-it-qat.json`.
