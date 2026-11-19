# Figure data: pictures_1 of Zodiac (page 4)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `ollama` (a local model through the measured engine), model `gemma4:26b-a4b-it-qat`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 2: ZODIAC aligns with cardiological practice through a multi-agent framework that integrates patient data across various modalities: ➀ Patient data is collected in two modalities: tabular metrics and ECG tracings (images). ➁ A metrics-to-findings LLM agent processes the tabular metrics and generates text-based clinical findings. ➂ An tracings-to-findings LLM agent analyzes the ECG tracings to produce additional text-based clinical findings. ➃ The clinical findings from both agents are then combined. ➄ A findings-to-interpretation LLM agent synthesizes these findings with clinical guidelines into comprehensive diagnostic interpretation. ➅ ZODIAC generates a patient-specific report by integrating the metrics, tracings, clinical findings, and diagnostic interpretation. ➆ Acardiologist validates the quality of the generated findings and interpretations (details in 5). For simplicity, we omit the biostatistics ( B ) in this figure, which is considered in steps ➀➁➂ by default.

**What the figure shows (model):** This figure illustrates the ZODIAC workflow, showing how patient data (metrics, tracings, and ectopics) is processed by M2F and T2F agents into findings, which are then interpreted by an F2I agent based on guidelines to produce a clinical report for a cardiologist.

**No data read:** not a data chart: This figure illustrates the ZODIAC workflow, showing how patient data (metrics, tracings, and ectopics) is processed by M2F and T2F agents into findings, which are then interpreted by an F2I agent based on guidelines to produce a clinical report for a cardiologist.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-181130_ollama_gemma4-26b-a4b-it-qat.json`.
