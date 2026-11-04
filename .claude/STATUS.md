# STATUS

_Rewritten from scratch by `/project-memory`. Read this first, every session. Last: 2026-11-04._

## Current focus

- Release `extrct_docling-v2.131.0-r2` (on Docling 2.131.0) is tagged and pushed; the 23 sample PDFs were converted from r1 with HTML written by r2, all verified complete.

## Active work

- None open. The `/project-memory` ritual and its ticket hook went live this session.

## Next steps

1. Fold the export checks into `amir-batch`: per bundle, item coverage (every `document.json` item tagged once in `<stem>.html`) and PDF text-layer word recall, in the end-of-run summary; one module in `docling/engines/`, a test, release `-r3`.
2. Measure Granite-Vision vs TableFormer tables on the converted batches (23 of 115 tables needed the PDF-text fallback) before choosing the default.
3. File the unbounded `max_new_tokens` bug in `table_structure_model_granite_vision.py` upstream (docling-project), with the cap as the fix.
4. Small `-r3` items: record torch's CUDA build in `run.json`; `amir-batch` skip-existing + crash retry.

## Blockers / open decisions

- Regenerate `showcase/` from the release (adds repo weight) - maintainer's call.
- GitHub Release page needs upstream's `pypi.yml` / `discord-release.yml` disabled on the fork first.

## Watch-outs

- Before tagging, convert the slowest/table-dense PDF from the working tree; climbing GPU memory with no paper finishing = runaway (L-1).
- After a text fix, check every export: html, md, embedded.md, chunks (L-2).
- Write-capable scripts run on scratch copies, never on the user's `samples/` folders (L-3).
