# Figure data: pictures_2 of Eunjung_Lee_ssrn-7427517_2 (page 10)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3. Paired physician-rating differences for overall quality and secondary quality domains. Points show model-estimated mean differences, and bars show 95% CIs. Positive values favor AI-generated summaries; negative values favor clinician-authored summaries.

**What the figure shows (model):** This figure is a forest plot comparing clinician-authored summaries and AI-generated summaries across five rating domains.

## Chart 1 (forest, horizontal)

x axis linear -1 to 1.5; y axis "Rating domain" categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Overall quality |  |  | -0.2752 | -0.88 | 0.42 |  | raster | 0.7 |
| Clarity |  |  | 0.3398 | 0.05 | 0.65 |  | raster | 0.7 |
| Completeness |  |  | -0.8119 | -1.38 | -0.32 |  | raster | 0.7 |
| Accuracy |  |  | -0.3653 | -0.68 | -0.02 |  | raster | 0.7 |
| Readability |  |  | 0.6532 | 0.15 | 1.25 |  | raster | 0.7 |

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113628_ollama_gemma4-26b-a4b-it-qat.json`.
