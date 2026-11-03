---
name: release-tag
description: |
  Cuts a release of this fork as an annotated git tag `extrct_docling-v<docling version>-r<n>` (Docling base version from pyproject.toml + the fork's revision on that base), with ENGINE_VERSION, README "Releases", HANDOFF and the stage log updated, tests + `make validate` green, and a sensitive-content scan (secrets, machine paths, usernames, never-push files) of everything about to be published. Use when the user says "tag a release", "cut a release", "make a release version", "tag this version", "new release", "release it so I can pin it". NOT for ordinary commits (use `commit`). NOT for creating a GitHub Release page — on this fork that fires upstream's PyPI-publish workflow (see step 8).
---

# release-tag

A release is a git tag other projects pin (submodule checkout or
`git+https://…@<tag>`), and every bundle's `run.json` → `engine` names it.
So the tag, `ENGINE_VERSION` and the docs must agree, and nothing private may
ride along.

## Workflow

1. **Preconditions.** On the release branch (`dgx`), not `main`. Working tree
   clean apart from the release edits (`git status`). `git fetch origin --tags`.

2. **Pick the version.**
   - Base = `version` in `pyproject.toml` (the upstream Docling version; that
     line says DO NOT EDIT — read it, never change it).
   - `n` = 1 + the highest `-r<n>` among `git tag -l "extrct_docling-v<base>-r*"`
     and `git ls-remote --tags origin`; `-r1` on a new Docling base.
   - Tag `extrct_docling-v<base>-r<n>`; `ENGINE_VERSION = "<base>-r<n>"`.

3. **Update, in one commit:**
   - `ENGINE_VERSION` in `docling/engines/run_snapshot.py`.
   - `README.md` § "Releases: pin a version": new row on top (date, base,
     what changed — from `git log --oneline <previous tag>..HEAD`) and the two
     pin commands.
   - `.claude/HANDOFF.md`: "Current release" line and the submodule pin in §11.
   - `.claude/AMIR_STAGE.md`: a Log row for the release.

4. **Gates.** `uv run --no-sync pytest tests/test_engines -q` and
   `make validate` (rerun until clean). Never `uv sync` / plain `uv run` /
   `make check` here: they re-sync the env and can replace the manually
   installed CUDA torch.

5. **Commit** `Release extrct_docling <base>-r<n>` (hooks on, no `--no-verify`).

6. **Sensitive-content check.** Write the tag notes to a scratch file (what
   changed, base Docling version, the two pin commands), then:

   ```bash
   bash .claude/skills/release-tag/check_sensitive.sh origin/dgx <notes-file>
   ```

   It scans the commits a push would publish plus the notes:
   - **FAIL** (must fix before pushing): never-push files (`.env`,
     `.mcp.json`, `settings.local.json`, `.claude/private-hand-off/`,
     `.claude/worktrees/`, `samples/` except its README, `*.log`, keys);
     token patterns (GitHub, Hugging Face, OpenAI/Anthropic, AWS, Slack,
     private keys, `api_key = "…"`); this machine's home path, username,
     hostname, `/tmp/claude…` scratch paths, private IPs.
   - **REVIEW** (show the user): email addresses (a paper's public author
     emails are fine, anything else is not), files over 5 MB, commit authors.

   Fix a FAIL by editing and committing again, or by dropping the file from
   history only with the user's say-so. Rerun until it prints `OK`.

7. **Tag and push** — only when the user asked for the push in this
   conversation; otherwise give them the commands.

   ```bash
   git tag -a extrct_docling-v<base>-r<n> -F <notes-file>
   git push origin dgx && git push origin extrct_docling-v<base>-r<n>
   git ls-remote --tags origin extrct_docling-v<base>-r<n>
   ```

   Never move or reuse a pushed tag: people may have pinned it. To replace
   one, ask, then delete it (`git tag -d …` and `git push origin --delete …`)
   and cut the next `-r<n>`.

8. **No GitHub Release page.** Actions are enabled on the fork, and
   upstream's `.github/workflows/pypi.yml` and `discord-release.yml` run on
   `release: published` with no fork guard (a PyPI trusted-publish attempt
   of the Docling packages, a Discord post). A tag push triggers nothing.
   If the user wants a release page: ask, `gh workflow disable pypi.yml` and
   `gh workflow disable discord-release.yml` on the fork, then
   `gh release create <tag> --notes-file <notes-file>`. After any push,
   `gh run list --limit 3` should show no new runs.

9. **Outputs that should carry the release.** Bundles converted from a clean
   checkout of the tag get `run.json` → `engine.version`, `git_commit`,
   `git_dirty: false` and the version in the `<stem>.html` header. Don't edit
   tracked files while a batch runs (that flips `git_dirty`); rebuild with
   `amir-batch` from the tag when outputs must be stamped with it.

## Report

Tag name and commit, what's in the release, the check's result (and every
REVIEW line), push status, and whether any workflow ran.
