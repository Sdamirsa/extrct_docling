# Figure data: pictures_3 of Cardiologent (page 7)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 4: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) on the 20 -patient subset. The judge's agreement with each cardiologist ( 0 . 74 , 0 . 66 ) is comparable to the two cardiologists' agreement with each other ( 0 . 67 ): the judge agrees with a cardiologist about as closely as the two cardiologists agree with each other.

**What the figure shows (model):** This figure shows the Intraclass Correlation Coefficient (ICC) for absolute agreement between different pairs of raters: human-human (R1 ↔ R2), Judge ↔ R1, and Judge ↔ R2.

## Chart 1 (forest, vertical)

y axis "ICC(2,1), absolute agreement" linear 0.4 to 0.9.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| R1 ↔ R2 (human–human) |  |  | 0.67* | 0.52 | 0.79 |  | vlm | 0.5 |
| Judge ↔ R1 |  |  | 0.73* | 0.6 | 0.84 |  | vlm | 0.5 |
| Judge ↔ R2 |  |  | 0.67* | 0.51 | 0.78 |  | vlm | 0.5 |

- Note: no axis calibrated from tick labels; values are the model's

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113512_ollama_gemma4-26b-a4b-it-qat.json`.
