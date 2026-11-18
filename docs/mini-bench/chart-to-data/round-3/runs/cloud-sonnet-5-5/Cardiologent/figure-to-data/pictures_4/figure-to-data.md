# Figure data: pictures_4 of Cardiologent (page 13)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Stage 1: Time series encoder

**What the figure shows (model):** Architecture diagram of a time-series encoder-decoder (Stage 1) feeding patch embeddings, together with a text prompt and a CLIP vision encoder, into a Llama-7B model that outputs an ECG/PPG arrhythmia explanation; it contains no plotted data.

**No data read:** not a data chart: Architecture diagram of a time-series encoder-decoder (Stage 1) feeding patch embeddings, together with a text prompt and a CLIP vision encoder, into a Llama-7B model that outputs an ECG/PPG arrhythmia explanation; it contains no plotted data.

## Not read, or uncertain

- The diagram has no quantitative data. The only numbers are the quoted example text (R-R CV 0.183, AF threshold 0.15) and the prompt template, which are not chart values.
- The ECG waveform with red R-peak markers is a raw signal trace and was not tabulated.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153217_cloud_anthropic-claude-sonnet-5.5.json`.
