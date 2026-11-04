# Docling (extrct_docling fork — building the Amir Engine)

## Project Overview

@AGENTS.md

See [.claude/REPO_CONTEXT.md](.claude/REPO_CONTEXT.md) for the condensed architecture map and [.claude/AMIR_TODO.md](.claude/AMIR_TODO.md) for the active build plan.

## Stack
- Language: Python 3.10+
- Build: `uv build`
- Test: `uv run pytest` (or `make test`)
- Lint / validate: `make validate` (mutating hooks) · `make check` (read-only)

## Conventions (load-bearing rules)
- Prefer editing existing files to creating new ones.
- Run `make validate` before declaring a task done.
- Don't put secrets in code; use `.env` (already gitignored).

## Where things live
- `.claude/ROUTER.md` — task-routing decision table (read this first).
- `.claude/rules/` — path-scoped instructions.
- `.claude/skills/` — auto-triggered workflows.
- `.claude/agents/` — delegatable subagents.
- `.claude/reference/INDEX.md` — reference catalog (consult on demand).
- `.claude/README.md` — full navigation map.
- `.claude/REPO_CONTEXT.md` — Docling architecture cheat-sheet for this fork.
- `.claude/STATUS.md` — read first: current focus, next steps, watch-outs (rewritten by `/project-memory`).
- `.claude/Project-log.jsonl` / `LESSONS.jsonl` — append-only session log and mistakes-with-prevention, curated by `/project-memory`.
- `/project-memory` — the session-end ritual; only the user types it (`.claude/skills/project-memory/`).
- `.claude/AMIR_TODO.md` / `AMIR_STAGE.md` — Amir Engine plan + phase tables; log history up to 2026-11-04.
