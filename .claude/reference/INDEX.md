# Reference catalog — docling-slim (extrct_docling / Amir Engine)

> Read on demand. Do NOT load all of this at session start.
> Consult before designing new schemas, prompts, extractors, charts, or pipelines.

<!-- managed:reference-catalog -->
| Topic | Path | Consult when |
|---|---|---|
| (none in baseline) | | Subdirectories materialize as packs install or you create them. |
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
