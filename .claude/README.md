# `.claude/` — Navigation Index

This directory configures Claude Code for **docling-slim** (the extrct_docling
fork hosting the **Amir Engine** build). The structure mirrors the official
taxonomy.

## Project-specific entry points

- [AMIR_TODO.md](AMIR_TODO.md) — phased build plan for the Amir Engine.
- [AMIR_STAGE.md](AMIR_STAGE.md) — current phase, next action, blockers.
- [REPO_CONTEXT.md](REPO_CONTEXT.md) — condensed Docling architecture + where to plug Amir Engine in.

## What lives here

| Path | Purpose | When loaded |
|---|---|---|
| `ROUTER.md` | The triggering decision table. Injected at SessionStart. | Every session |
| `settings.json` | Permissions, hooks, env (team-shared). | Every session |
| `settings.local.json` | Personal overrides (gitignored). | Every session |
| `rules/00-global.md` | Global conventions. | Every session |
| `rules/*.md` | Path-scoped conventions (frontmatter `paths:`). | When matching files are touched |
| `skills/<name>/SKILL.md` | Workflows. Auto-trigger on description; also `/skill-name`. | On invocation |
| `agents/<name>.md` | Delegatable subagents. Auto-delegate on description. | On delegation |
| `hooks/*.py` | Deterministic enforcement (deny, log, inject context). | Per event |
| `reference/INDEX.md` | Catalog of reference docs. | On demand only |
| `reference/<topic>/...` | Persistent reference material. | On demand only |
| `.meta/version` | Template version installed. | Read by upgrade |
| `.meta/hooks.lock` | sha256 of every hook. | Verified by SessionStart |
| `.meta/packs.json` | Which packs are installed. | Read by audit |

## How to extend

- New workflow → `claude-folder-handler install-pack <name>` (or ask Claude "install the X pack").
- Custom skill → create `.claude/skills/<name>/SKILL.md` with the triggering convention.
- Custom rule → create `.claude/rules/<topic>.md` with frontmatter `paths: ...`.
- Audit drift → `claude-folder-handler audit` (or ask Claude "audit my .claude folder").

## How to upgrade

Re-run `claude-folder-handler upgrade --apply` (or ask Claude "upgrade my claude setup"). Only content inside `<!-- managed:* -->` blocks is replaced; your edits outside those blocks are preserved.
