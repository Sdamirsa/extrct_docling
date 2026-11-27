# STATUS

_Rewritten from scratch by `/project-memory`. Read this first, every session. Last: 2026-11-27._

## Current focus

- Release `extrct_docling-v2.131.0-r9` (Docling 2.131.0, docling-parse 7.28) is tagged and pushed: 7.28 reads r8's look-alikes right, the fused words it still joins are spaced by the gaps between glyphs (`docling/utils/parser_repair.py`, temporary), and every bundle draws its steps (`provenance.html`, `methods.md`). Results: `.claude/reference/quality/2026-11-25-parser-faults-and-upgrade-plan.md` §9.

## Active work

- None running. The maintainer is moving the sample sets (the nirct and aca inputs, outputs and `samples/archived/`) to a repo of their own. Their 416 bundles are r7 and r8 conversions; since 2026-11-27 every `check.json` is r8's; each set has `pipeline_extrct_docling-<version>[_postfix-<date>].html` (HANDOFF §9).

## Next steps

1. Fonts whose codes are the embedded font's glyph numbers (`check.json` -> `text_quality.unmapped_pages`, one supplement page in the sets): decode them through the font's `cmap` in `docling/utils/text_layer.py`, measured on the pages the check names, before any OCR fallback (plan §1).
2. When the disk allows (about 25 GB free) and the maintainer wants it: reconvert the sample sets with r9 from the repository root at the tag (about 14 h), the bundles the check flags first; put the figure readings back only where no picture moved.
3. File the docling-parse fused-words report (draft: `.claude/issues-with-docling/docling-parse-fused-words-justified-text.md`); remove the repair when a release separates these words.

## Blockers / open decisions

- Disk: 18 GB free. The maintainer's to clear: `.claude/worktrees/` (`r7-release`, `r8-release`, `agent-a75a01f2844443a5c` on `gpu-docker-explore`) and the scratch conversions of this session.

## Watch-outs

- One-time fixes to sample bundles live in prose, not in the bundles: list them before describing or redoing a set's provenance (L-8).
- A repair that replaces characters (the `cmap` decoding next): dry-run it over every set and print the (old -> new) pairs first; a Symbol font's Greek letters read as ASCII in pdfium (L-6).
- Write-capable scripts run on scratch copies (hard links are fine) unless the user asked for that folder (L-3).
- An older release's code: a script file from the repository root with `PYTHONPATH=<worktree>`; assert `docling.__file__` (`python -c` imports the checkout's).
