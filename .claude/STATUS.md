# STATUS

_Rewritten from scratch by `/project-memory`. Read this first, every session. Last: 2026-11-25._

## Current focus

- Release `extrct_docling-v2.131.0-r8` (Docling 2.131.0, docling-parse 7.20) is tagged and pushed. It carries a temporary repair of docling-parse 7.20's fused words and look-alike characters (`docling/utils/parser_repair.py`); the upgrade plan is `.claude/reference/quality/2026-11-25-parser-faults-and-upgrade-plan.md` (read it first).

## Active work

- None running. The three sample sets are final for now (the nirct and aca output folders under `samples/`, r7 plus the r8 reconversion of the bundles r8 changes); the 127-trial set is zipped for transfer; its figure-to-data step runs on another device.

## Next steps

1. Upgrade docling-parse 7.20 -> 7.28 in a branch (needs docling-core >= 2.99 and a `uv sync`: ask the user first). Run the HTML-completeness test, then the suite (plan §7 step 2).
2. Measure on the five sample documents of plan §7 step 3, three ways (r8 on 7.20; 7.28 repair on; 7.28 repair off): is the repair still needed, does it still work; then remove or keep it and release r9.
3. Engine fix: `public_source_path` keeps a linked path under the current directory (worktree batches recorded bare file names, plan §8).
4. Next fix after the upgrade: decode fonts whose codes are the embedded font's glyph numbers through its `cmap` (`check.json` -> `text_quality.unmapped_pages`, plan §1).

## Blockers / open decisions

- The docling-parse upgrade changes the environment: the user's go-ahead before `uv add` / `uv sync`.
- Disk is nearly full (about 14 GB free): the r7/r8 worktrees under `.claude/worktrees/`, `samples/archived/r7_before_r8/` and the old `samples/nirct_validation22_out.zip` are the user's to clear.

## Watch-outs

- A repair that replaces characters: dry-run it over every set and print the (old -> new) pairs first; Greek letters from a Symbol font read as ASCII in pdfium (L-6).
- After any batch: every `run.json` -> `source.input` must exist from the repository root (L-7). Exit 3 is a finished batch with check issues; 139 a segfault, run it again.
- Write-capable scripts run on scratch copies unless the user asked for that folder (L-3).
