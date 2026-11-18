# Figure data: pictures_5 of Cardiologent (page 18)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6: Grounding on ECG window 4925_w0099 (ground-truth PAC). Each row is one model's localized abnormalspanonthesametrace;thetoprowisthegroundtruth. Cardiologent localizes a tight span on the PAC, whereas the baselines mark almost the entire window, inflating IoU while collapsing MCC toward zero.

**What the figure shows (model):** Seven stacked ECG traces of the same window (ground truth and six models) with shaded spans marking each model's localized abnormal region (a PAC), shown qualitatively with no numeric values.

**No data read:** not a data chart: Seven stacked ECG traces of the same window (ground truth and six models) with shaded spans marking each model's localized abnormal region (a PAC), shown qualitatively with no numeric values.

## Not read, or uncertain

- ECG waveforms: raw signal traces with no axes or values, not tabulated.
- Shaded spans (ground truth, Cardiologent, and baselines): positions are shown only visually, with no printed numbers, so no span boundaries or IoU/MCC values were recorded.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113551_agent_claude-sonnet-5-5.json`.
