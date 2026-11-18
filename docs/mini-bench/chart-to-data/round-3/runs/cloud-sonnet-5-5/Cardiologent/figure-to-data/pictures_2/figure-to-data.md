# Figure data: pictures_2 of Cardiologent (page 4)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (one call to a cloud model's API), model `anthropic/claude-sonnet-5.5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3: Cardiologent. Window level: an agent per signal reads the waveform through its tools-seven on the ECG, nine on the PPG-and returns a grounded class, and window fusion reconciles the ECG and PPG readings by debate into one verdict. Patient level: the verdicts are aggregated into a rhythm profile, reconciled across signals by the same debate, and only then read against the patient's metadata through guideline retrieval, a reasoning stage, and a critic, yielding the integrated diagnosis, its significance, and the urgency and management.

**What the figure shows (model):** Architecture diagram of the Cardiologent multi-agent framework, in which ECG and PPG specialist agents, debate fusion with a devil's advocate and referee, PubMed guideline retrieval and a patient-level diagnosis stage are shown; it plots no quantitative data.

**No data read:** not a data chart: Architecture diagram of the Cardiologent multi-agent framework, in which ECG and PPG specialist agents, debate fusion with a devil's advocate and referee, PubMed guideline retrieval and a patient-level diagnosis stage are shown; it plots no quantitative data.

## Not read, or uncertain

- The figure is a workflow diagram. Its labels (agent names, ECG/PPG, debate stages) are not data values, so no chart was extracted.
- The green ECG trace with the highlighted PVC beat is a raw signal illustration and was not digitised.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-153217_cloud_anthropic-claude-sonnet-5.5.json`.
