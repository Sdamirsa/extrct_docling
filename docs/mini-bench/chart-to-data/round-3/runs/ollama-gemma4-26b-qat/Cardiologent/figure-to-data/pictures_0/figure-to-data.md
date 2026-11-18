# Figure data: pictures_0 of Cardiologent (page 1)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 1: Deployment scenario. Stage 1, wearable: the pulse is monitored on its own, and the PPG agent reads it as far as the pulse allows-an irregular rhythm it calls atrial fibrillation, flagged as needing an ECG to confirm. Stage 2, monitored: the ECG is added, and Cardiologent reads it together with the pulse and the patient's own data to reach the decision-the therapy indicated, and how urgent. Excerpts are verbatim.

**What the figure shows (model):** This figure is a workflow diagram illustrating a two-stage medical monitoring process: Stage 1 involves daily PPG monitoring via a wearable device by a patient, where a PPG Agent detects an irregular rhythm suggesting atrial fibrillation; Stage 2 involves hospital-based ECG and PPG monitoring, where a cardiologist confirms sustained atrial fibrillation and recommends anticoagulation therapy.

**No data read:** not a data chart: This figure is a workflow diagram illustrating a two-stage medical monitoring process: Stage 1 involves daily PPG monitoring via a wearable device by a patient, where a PPG Agent detects an irregular rhythm suggesting atrial fibrillation; Stage 2 involves hospital-based ECG and PPG monitoring, where a cardiologist confirms sustained atrial fibrillation and recommends anticoagulation therapy.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-113512_ollama_gemma4-26b-a4b-it-qat.json`.
