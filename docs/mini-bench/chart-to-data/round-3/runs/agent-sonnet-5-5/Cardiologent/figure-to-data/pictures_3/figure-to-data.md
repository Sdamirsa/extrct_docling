# Figure data: pictures_3 of Cardiologent (page 7)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 4: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) on the 20 -patient subset. The judge's agreement with each cardiologist ( 0 . 74 , 0 . 66 ) is comparable to the two cardiologists' agreement with each other ( 0 . 67 ): the judge agrees with a cardiologist about as closely as the two cardiologists agree with each other.

**What the figure shows (model):** Point estimates with 95% CIs of ICC(2,1) absolute agreement for human–human (R1↔R2) and judge–cardiologist (Judge↔R1, Judge↔R2) pairs on a 20-patient subset.

## Chart 1: Rater agreement (ICC(2,1), absolute agreement, with 95% CI) (other, vertical)

x axis "Rater pair" categorical; y axis "ICC(2,1), absolute agreement" linear 0.35 to 0.95.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| R1 ↔ R2 (human–human) |  |  | 0.67 | 0.52 | 0.79 |  | agent | 0.8 |
| Judge ↔ R1 |  |  | 0.74 | 0.6 | 0.84 |  | agent | 0.8 |
| Judge ↔ R2 |  |  | 0.66 | 0.51 | 0.78 |  | agent | 0.8 |

- Note: Point estimates read against axis and consistent with caption (0.67, 0.74, 0.66); CI ends are the printed labels (axis suggests ~0.605 and ~0.775/0.513 before rounding).

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-114841_agent_claude-sonnet-5-5.json`.
