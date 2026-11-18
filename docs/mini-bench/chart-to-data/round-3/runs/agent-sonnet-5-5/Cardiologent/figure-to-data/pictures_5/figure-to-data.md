# Figure data: pictures_5 of Cardiologent (page 18)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6: Grounding on ECG window 4925_w0099 (ground-truth PAC). Each row is one model's localized abnormalspanonthesametrace;thetoprowisthegroundtruth. Cardiologent localizes a tight span on the PAC, whereas the baselines mark almost the entire window, inflating IoU while collapsing MCC toward zero.

**What the figure shows (model):** Seven ECG traces of window 4925_w0099 (ground-truth PAC), one per row (GT, Cardiologent, and five baseline models), each with a shaded span marking the localized abnormal region. It has no numeric values.

**No data read:** not a data chart: Seven ECG traces of window 4925_w0099 (ground-truth PAC), one per row (GT, Cardiologent, and five baseline models), each with a shaded span marking the localized abnormal region. It has no numeric values.

## Not read, or uncertain

- Shaded span extents per row (GT and Cardiologent mark a short span at the right end, the baselines mark nearly the whole window): qualitative, not given as numbers, so not recorded.
- ECG waveform traces: raw signal traces, not tabulated.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-114841_agent_claude-sonnet-5-5.json`.
