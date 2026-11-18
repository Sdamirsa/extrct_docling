# Figure data: pictures_2 of Eunjung_Lee_ssrn-7427517_2 (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3. Paired physician-rating differences for overall quality and secondary quality domains. Points show model-estimated mean differences, and bars show 95% CIs. Positive values favor AI-generated summaries; negative values favor clinician-authored summaries.

**What the figure shows (model):** Forest plot of paired physician-rating mean differences (AI-generated minus clinician-authored summaries) with 95% CIs for five rating domains.

## Chart 1: Paired physician-rating differences for overall quality and secondary quality domains (forest, horizontal)

x axis "Mean difference (positive favors AI-generated summaries)" linear -1.5 to 1.5; y axis "Rating domain" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Overall quality |  |  | -0.15 | -0.87 | 0.56 |  | agent | 0.8 |
| Clarity |  |  | 0.36 | 0.07 | 0.65 |  | agent | 0.8 |
| Completeness |  |  | -0.84 | -1.36 | -0.33 |  | agent | 0.8 |
| Accuracy |  |  | -0.35 | -0.66 | -0.05 |  | agent | 0.8 |
| Readability |  |  | 0.72 | 0.2 | 1.24 |  | agent | 0.8 |

- Note: Values read from pixel positions against axis ticks; no numbers printed. Bars are 95% CIs. Dashed line at 0 = no difference.

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-115013_agent_claude-sonnet-5-5.json`.
