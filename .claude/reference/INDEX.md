# Reference catalog — docling-slim (extrct_docling / Amir Engine)

> Read on demand. Do NOT load all of this at session start.
> Consult before designing new schemas, prompts, extractors, charts, or pipelines.

<!-- managed:reference-catalog -->
| Topic | Path | Consult when |
|---|---|---|
| (none in baseline) | | Subdirectories materialize as packs install or you create them. |
| Structure pass | `reference/structure/RULES.md` | Before changing a labelling rule, heading-level inference, a `data-*` attribute of `<stem>.html`, or a quality warning code (bump `STRUCTURE_VERSION`). |
| Figure-to-data | `reference/figure-data/STANDALONE-STEP.md` (the figure-to-data step as built: prepare / read / embed, the folder, the three methods `ollama` / `cloud` / `agent`, the agent's policy and confinement, reasons), `DESIGN.md` (the measured engine behind the local method: config, schema, round-2 rules), `RESULTS-2026-11-09.md` | Before changing a method's prompt, the agent's tools or policy, the reply format, the panel splitter, the embed or the budgets (rerun `docs/mini-bench/chart-to-data` after; results per round in its `round-N/` folders). |
| Quality findings | `reference/quality/2026-11-20-r5-bundles-tables-and-text.md` (what r5 bundles lost: tables, footnotes, in-figure text), `2026-11-25-parser-faults-and-upgrade-plan.md` (docling-parse 7.20's look-alike letters and fused words, the temporary r8 repair, and the plan for the docling-parse upgrade) | Before upgrading docling-parse or docling-core, changing `text_layer.py` / `parser_repair.py`, table routing, or the check's thresholds. |
<!-- /managed:reference-catalog -->

## Subdirectories (populated by packs or by you)

- `datasets/` — dataset cards: schema, location, provenance, license (`+data-science`)
- `schemas/` — JSON schemas / pydantic models / dataframe contracts (`+llm-extraction`)
- `prompts/` — reusable system prompts + few-shot templates (`+llm-extraction`)
- `apis/` — external API/SDK quick references (`+llm-app`)
- `charts/` — chart pattern gallery (`+visualization`)
- `adr/` — architecture decision records (numbered, immutable once accepted)
- `experiments/` — dated eval results, ablations, baselines
- `glossary.md` — domain terms

## Authoring conventions

- Every file in `reference/` must start with `<!-- last-reviewed: YYYY-MM-DD -->`
- Files >300 lines should be split.
- Don't duplicate CLAUDE.md content — reference is for *what to consult*, CLAUDE.md is for *what to always do*.
- New entries should be added to the table above (inside `<!-- managed:reference-catalog -->` so `upgrade` won't clobber).
