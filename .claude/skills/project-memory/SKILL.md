---
name: project-memory
description: The session-end ritual for extrct_docling - CHECK, POLISH, PUBLISH, EVOLVE, report, ROUTE. Only the user opens it, by typing /project-memory at the end of a working session or after a milestone. When the user says "update memory", "update memory and log", "log this session", "update status", "wrap up" or "run the ritual", ask them to type /project-memory. NOT for planning or resuming work, NOT for a cold "where were we" (read .claude/STATUS.md), NOT for cutting a release (the release-tag skill).
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
---

# /project-memory

Adopted from dot-claude-iff's ritual and scaled to this repo (no console or
cards). Two locks keep it the user's: `disable-model-invocation`, and the
ritual ticket — `.claude/hooks/30-ritual-ticket.py` writes
`.claude/.cache/ritual-ticket.json` when the user's own prompt starts with
`/project-memory`; CHECK fails without a fresh one and `--complete` consumes
it. Never write, copy or touch the ticket yourself; if CHECK refuses for want
of one, stop and ask the user to type `/project-memory`. If their prompt
hook did not fire (hooks not yet accepted in `/hooks`), the USER runs
`! uv run --no-sync python .claude/skills/project-memory/check.py --grant`
themselves, then types `/project-memory`; settings.json denies `--grant` to
your Bash tool, so never try it. If the user asks for
"memory" in other words, ask them to type it.

Run it in the MAIN session, never as a sub-agent: you are the only agent who
saw the whole conversation, and curation is the part that can't be rebuilt
from disk.

Phases in order: **CHECK, POLISH, PUBLISH, EVOLVE**, the report, **ROUTE**.

## Phase 1 - CHECK

```bash
uv run --no-sync python .claude/skills/project-memory/check.py --gates
```

One line per step. `--gates` adds the engine tests and `make validate`.
- **FAIL** stops the ritual: fix what can be fixed and rerun. If it can't be
  fixed now, say so and stop before PUBLISH. Never report a clean wrap-up over
  a failed check.
- **WARN** informs. Most WARNs are stale facts POLISH is about to fix (a
  handoff test count, a module missing from the tree, commits newer than the
  last log entry). Mention the rest in the report.

Then check what no script can: does `.claude/STATUS.md` still describe
reality, does `.claude/HANDOFF.md` §9 (known issues) and §12 (next steps)?
Where they disagree, reality wins.

Never `uv sync`, plain `uv run` or `make check` here: they re-sync the env and
can replace the manually installed CUDA torch.

## Phase 2 - POLISH

**2a. Reconstruct the session**: decisions and why, deliverables, analyses,
mistakes on both sides, open questions, next steps. Signal over asides.

**2b. Append to `.claude/Project-log.jsonl`**, one line per real thing:

```json
{"date":"YYYY-MM-DD","type":"decision|deliverable|milestone|analysis|note|mistake|tooling","title":"grep-skimmable","summary":"1-2 sentences: what and why","artifacts":["relative/path"],"tags":["..."],"source":"session|artifacts|git"}
```

`source` is epistemic: `session` = you witnessed it, `artifacts`/`git` =
inferred from files afterwards. Append only, never edit past lines. No
volatile numbers without their source (a coverage % names its check). Paths
are repo-relative; machine paths and sample PDF names of private batches stay
out (the log is pushed).

**2c. Curate `.claude/LESSONS.jsonl`**, one row per mistake that cost
something (rework, a wrong output, lost GPU time, a misleading report):

```json
{"id":"L-<n>","date":"YYYY-MM-DD","who":"agent|developer|both","what":"...","root_cause":"...","prevention":"mechanical and checkable","active":true}
```

The prevention must be executable by a future session ("print
`module.__file__` before trusting a worktree test"), never "be careful". Keep
1 to 3 rows `active`; retire what's internalized by setting `active` false in
a NEW row superseding the old id (append only).

**2d. Rewrite `.claude/STATUS.md` from scratch**, 15-25 lines, five sections:
Current focus, Active work, Next steps (concrete enough to start cold),
Blockers and open decisions, Watch-outs (mirroring the active lessons).

**2e. Refresh `.claude/HANDOFF.md`**: fix every stale fact CHECK flagged
(test counts, the module tree, the current release) and §9 / §12 if the
session changed them. `.claude/AMIR_STAGE.md` keeps its phase tables and its
log history up to 2026-11-04; touch it only if a phase's state changed.

**2f. Auto-memory** (`~/.claude/projects/<repo>/memory/`): only durable user
preferences or corrections that apply beyond this repo's files; update an
existing memory rather than adding a near-duplicate.

**2g. `CLAUDE.md` / `.claude/ROUTER.md`** only if locations or conventions
changed this session. They are maps, not dumps.

## Phase 3 - PUBLISH

1. Re-run `check.py` (no `--gates` needed if nothing but docs changed since).
2. Commit: `git add` the ritual's files (and anything else the session
   finished), then `git commit -m "docs: project memory <YYYY-MM-DD>"` with
   hooks on, never `--no-verify`.
3. Scan what a push would publish:
   `bash .claude/skills/release-tag/check_sensitive.sh` (defaults to the
   branch's upstream). Every FAIL is fixed before pushing; show REVIEW lines.
4. Push per `push` in `.claude/config/memory.json`: `ask` (default) asks once
   with AskUserQuestion naming branch and remote; `always` pushes; `never`
   commits only. Push to `origin` (the user's fork), never to `upstream`
   (docling-project), never `--force`, never when CHECK failed.

Releases are the maintainer's call: when they name one, hand over to the
`release-tag` skill. Root `CHANGELOG.md` is upstream Docling's: never edit it.

## Phase 4 - EVOLVE

**4a. Session digest**, 15-30 lines: goals and outcome; instructions you
needed more than once (with counts); failures and root causes; human
corrections; gates asked and answered; friction; skills and agents used and
whether they fit.

**4b. Dispatch the `retro-analyst` agent** (read-only, Sonnet) with the digest
and `ls -R .claude/skills .claude/agents .claude/rules`. It returns at most
three proposals in its format, or `NO-CHANGES: <reason>`.

**4c. Filter**: it saw a lossy digest, you saw the session. Drop proposals
whose evidence doesn't hold. NO-CHANGES is a good outcome.

**4d. Confirm - BLOCKING.** AskUserQuestion, multi-select, one option per
surviving proposal plus "None of these". Never change `.claude/` without it.

**4e. Implement** the confirmed ones with the smallest primitive that holds
(a CLAUDE.md line beats a rule beats a skill beats an agent), log each as a
`tooling` row in Project-log.jsonl, and commit it with the ritual's files
(back to PUBLISH steps 2-4 if PUBLISH already ran).

**4f. Close the ritual** (the last check.py call; it consumes the ticket):

```bash
uv run --no-sync python .claude/skills/project-memory/check.py --complete
```

## The report

One block, in order: CHECK result (with warnings), what was logged and what
changed in STATUS / HANDOFF / LESSONS, PUBLISH (commit hash, scan result,
pushed or not), retro outcome (confirmed, dropped, or NO-CHANGES), open
questions for the maintainer. Report skipped and failed steps as such.

## Phase 5 - ROUTE

Set up the next session with ONE AskUserQuestion, up to two questions:

1. **Focus of the next session**: the top two or three Next steps from the
   new STATUS.md as options (recommend one).
2. **Maturation pass now?** Default no. It suits a session meant to improve
   the system itself. If yes, run it now: audit `.claude/` (skills, agents,
   rules — this repo carries many pack skills, e.g. data-science, that may
   never fire here), usage evidence from Project-log.jsonl and git log, and
   turn surviving demote/archive/fix proposals into a decision list for the
   maintainer, each through the same user gate.
