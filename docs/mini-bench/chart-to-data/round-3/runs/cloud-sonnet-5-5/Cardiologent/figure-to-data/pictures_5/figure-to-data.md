# Figure data: pictures_5 of Cardiologent (page 18)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 6: Grounding on ECG window 4925_w0099 (ground-truth PAC). Each row is one model's localized abnormalspanonthesametrace;thetoprowisthegroundtruth. Cardiologent localizes a tight span on the PAC, whereas the baselines mark almost the entire window, inflating IoU while collapsing MCC toward zero.

**What the figure shows (model):** ECG traces of window 4925_w0099 (ground-truth PAC) with each model's highlighted abnormal span: ground truth and Cardiologent mark a short span at the end of the trace, while the baseline models shade almost the whole window.

**No data read:** not a data chart: ECG traces of window 4925_w0099 (ground-truth PAC) with each model's highlighted abnormal span: ground truth and Cardiologent mark a short span at the end of the trace, while the baseline models shade almost the whole window.

## Not read, or uncertain

- The figure shows raw ECG signal traces with shaded localization spans. It has no axes, tick values or printed numbers, so no values were extracted.
- Seven traces were left unread: GT, Cardiologent, GPT-4o, Gemini-2.5-Pro, Qwen2.5-VL, MedGemma and Llama-3.2-Vision.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153217_cloud_anthropic-claude-sonnet-5.5.json`.
