# Figure data: pictures_2 of Cardiologent (page 4)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3: Cardiologent. Window level: an agent per signal reads the waveform through its tools-seven on the ECG, nine on the PPG-and returns a grounded class, and window fusion reconciles the ECG and PPG readings by debate into one verdict. Patient level: the verdicts are aggregated into a rhythm profile, reconciled across signals by the same debate, and only then read against the patient's metadata through guideline retrieval, a reasoning stage, and a critic, yielding the integrated diagnosis, its significance, and the urgency and management.

**What the figure shows (model):** Schematic of the Cardiologent multi-agent framework (ECG and PPG specialist agents, debate-based fusion, PubMed guideline retrieval, patient-level diagnosis) with no plotted data values.

**No data read:** not a data chart: Schematic of the Cardiologent multi-agent framework (ECG and PPG specialist agents, debate-based fusion, PubMed guideline retrieval, patient-level diagnosis) with no plotted data values.

## Not read, or uncertain

- Whole figure is a workflow diagram; the layout-detected 'chart' is a set of agent labels and icons, not data, so nothing was recorded.
- The small green ECG trace with a highlighted PVC beat is a raw signal illustration with no axes or values.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-114841_agent_claude-sonnet-5-5.json`.
