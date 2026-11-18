# Figure data: pictures_2 of Cardiologent (page 4)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `claude-sonnet-5-5`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 3: Cardiologent. Window level: an agent per signal reads the waveform through its tools-seven on the ECG, nine on the PPG-and returns a grounded class, and window fusion reconciles the ECG and PPG readings by debate into one verdict. Patient level: the verdicts are aggregated into a rhythm profile, reconciled across signals by the same debate, and only then read against the patient's metadata through guideline retrieval, a reasoning stage, and a critic, yielding the integrated diagnosis, its significance, and the urgency and management.

**What the figure shows (model):** A schematic of the Cardiologent framework showing ECG and PPG specialist agents, a debate among agents (devil's advocate and referee), PubMed guideline retrieval, and patient-level outputs, with an example ECG trace showing a premature ventricular contraction.

**No data read:** not a data chart: A schematic of the Cardiologent framework showing ECG and PPG specialist agents, a debate among agents (devil's advocate and referee), PubMed guideline retrieval, and patient-level outputs, with an example ECG trace showing a premature ventricular contraction.

## Not read, or uncertain

- The example ECG waveform trace: a raw signal illustration with no axes or data values, so nothing was tabulated.
- Agent, tool and stage labels (ECG/PPG specialists, debate stages, PubMed): diagram text, not data values.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113551_agent_claude-sonnet-5-5.json`.
