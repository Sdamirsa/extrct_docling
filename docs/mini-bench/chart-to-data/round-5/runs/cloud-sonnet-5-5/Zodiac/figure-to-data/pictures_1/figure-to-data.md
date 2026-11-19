# Figure data: pictures_1 of Zodiac (page 4)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `cloud` (a cloud model's API, asked once for the figure), model `anthropic/claude-sonnet-5.5`, 2026-11-19, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Figure 2: ZODIAC aligns with cardiological practice through a multi-agent framework that integrates patient data across various modalities: ➀ Patient data is collected in two modalities: tabular metrics and ECG tracings (images). ➁ A metrics-to-findings LLM agent processes the tabular metrics and generates text-based clinical findings. ➂ An tracings-to-findings LLM agent analyzes the ECG tracings to produce additional text-based clinical findings. ➃ The clinical findings from both agents are then combined. ➄ A findings-to-interpretation LLM agent synthesizes these findings with clinical guidelines into comprehensive diagnostic interpretation. ➅ ZODIAC generates a patient-specific report by integrating the metrics, tracings, clinical findings, and diagnostic interpretation. ➆ Acardiologist validates the quality of the generated findings and interpretations (details in 5). For simplicity, we omit the biostatistics ( B ) in this figure, which is considered in steps ➀➁➂ by default.

**What the figure shows (model):** Workflow diagram of the ZODIAC multi-agent framework, in which patient metrics and ECG tracings pass through LLM agents (M2F, T2F, F2I) with guidelines to produce a clinical report validated by a cardiologist.

**No data read:** not a data chart: Workflow diagram of the ZODIAC multi-agent framework, in which patient metrics and ECG tracings pass through LLM agents (M2F, T2F, F2I) with guidelines to produce a clinical report validated by a cardiologist.

## Not read, or uncertain

- The figure is a diagram with no plotted or tabulated data values, so no charts were extracted. The layout analysis's 'chart' is only a set of diagram labels.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261119-180719_cloud_anthropic-claude-sonnet-5.5.json`.
