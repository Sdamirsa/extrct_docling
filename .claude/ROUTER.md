# Claude Code router — docling-slim

The user's intent dictates which artifact handles a request. Consult this first.

## Local stack
- Language: python  •  Build: `uv build`  •  Test: `uv run pytest`  •  Lint: `ruff check .`
- See `.claude/rules/*` for path-scoped conventions.

## Workflows (skills auto-trigger; also explicit `/skill-name`)

<!-- managed:baseline -->
| User says | Skill | Notes |
|---|---|---|
| "commit", "save changes", "check in" | `skills/commit` | Chains to open-pr if pr-flow installed |
<!-- /managed:baseline -->

| User says | Skill | Notes |
|---|---|---|
| "tag a release", "cut a release", "make a release version", "tag this version" | `skills/release-tag` | `extrct_docling-v<docling version>-r<n>` tag + sensitive-content scan before push |

<!-- managed:pack-pr-flow -->
<!-- /managed:pack-pr-flow -->

<!-- managed:pack-test-tooling -->
<!-- /managed:pack-test-tooling -->

<!-- managed:pack-data-science -->
| "what's in this dataframe", "describe the data", "what columns does X have" | `skills/inspect-df` | Read-only profile |
| "clean this", "preprocess", "handle missing values", "tidy this dataframe" | `skills/clean-data` | Builds reviewable pipeline |
<!-- /managed:pack-data-science -->

<!-- managed:pack-visualization -->
| "plot X", "make a chart of Y", "visualize this", "graph the data", "show me a histogram of" | `skills/quick-chart` | Picks chart type; saves PNG |
| "is this chart good", "critique this viz", "review my plot" | `skills/chart-review` | Axes, encoding, accessibility |
<!-- /managed:pack-visualization -->

<!-- managed:pack-llm-app -->
| "set up anthropic client", "scaffold an agent", "init claude api" | `skills/anthropic-sdk-bootstrap` | Adds anthropic, prompt caching, .env, retries |
| "upgrade to claude X.Y", "migrate to a newer model", "swap the model version" | `skills/migrate-model-version` | Finds and updates model IDs across files |
<!-- /managed:pack-llm-app -->

<!-- managed:pack-llm-extraction -->
| "extract X from these documents", "parse this into JSON", "pull structured data from" | `skills/extract-structured` | Tool-use + JSON schema validation |
| "evaluate the extractor", "score this extraction", "build an eval for extraction" | `skills/build-extractor-eval` | Eval harness scaffold |
| "run this on all my files", "batch extract", "extract everything in this folder" | `skills/batch-extract` | Async fan-out + checkpointing |
<!-- /managed:pack-llm-extraction -->

## Delegations (subagents)

<!-- managed:agents-baseline -->
(none in baseline — install +pr-flow or +test-tooling for subagents)
<!-- /managed:agents-baseline -->

<!-- managed:pack-pr-flow-agents -->
<!-- /managed:pack-pr-flow-agents -->

<!-- managed:pack-test-tooling-agents -->
<!-- /managed:pack-test-tooling-agents -->

<!-- managed:pack-data-science-agents -->
| "explore this dataset", "profile this data", "what's in <file>.csv" | `agents/data-explorer` | One-shot profile in fresh context |
<!-- /managed:pack-data-science-agents -->

<!-- managed:pack-llm-extraction-agents -->
| "design a JSON schema for X", "draft a pydantic model for", "what's a good schema for this data" | `agents/schema-designer` | Returns schema + example + edge cases |
<!-- /managed:pack-llm-extraction-agents -->

## Reference (read on demand — consult INDEX first; do NOT load everything)

`.claude/reference/INDEX.md` — catalog of reference docs in this repo.
Consult before designing schemas, prompts, extractors, charts, or pipelines.

<!-- managed:reference-baseline -->
| Topic | Path | Consult when |
|---|---|---|
| (none in baseline) | | Subdirs materialize as packs install |
<!-- /managed:reference-baseline -->

<!-- managed:pack-data-science-reference -->
| Dataset cards | `reference/datasets/` | Before analyzing a dataset, check its card for schema, source, gotchas |
<!-- /managed:pack-data-science-reference -->

<!-- managed:pack-visualization-reference -->
| Chart pattern gallery | `reference/charts/_examples.md` | Before designing a new chart, check for an approved pattern |
<!-- /managed:pack-visualization-reference -->

<!-- managed:pack-llm-app-reference -->
| Anthropic SDK quick-ref | `reference/apis/anthropic-sdk.md` | Current model IDs, prompt caching, streaming patterns |
<!-- /managed:pack-llm-app-reference -->

<!-- managed:pack-llm-extraction-reference -->
| JSON schemas / pydantic models library | `reference/schemas/` | Re-use before designing a new one |
| System-prompt + few-shot templates | `reference/prompts/` | Re-use before drafting a new prompt |
| Extractor design checklist | `reference/extraction-checklist.md` | Run through before shipping a new extractor |
<!-- /managed:pack-llm-extraction-reference -->

## Hard constraints (enforced by hooks — cannot be bypassed)

- Reads of `**/.env*`, `**/credentials*`, `**/.ssh/**`, `**/.aws/**`, `**/.gnupg/**` → DENIED
- `git push --force/-f/--force-with-lease/+ref` to protected branches → DENIED
- `rm -rf /`, `rm -rf ~`, `rm -rf $HOME` → DENIED
- `curl ... | sh`, `wget ... | bash`, `sudo *` → DENIED
- Edits to `.git/**` or `.claude/hooks/**` → DENIED (require explicit unlock)

## Extension policy

- New workflow → add a skill; append a row to the appropriate `managed:*` block.
- New deny → edit `settings.json` AND the corresponding hook script, then run `approve_hooks`.
- This file is REGENERATED in managed blocks by `upgrade_claude_folder`. Edit OUTSIDE managed blocks only.


<!-- managed:pack-security-hardening -->
| (hardening enforcement) | `hooks/05-verify-hooks-lock.py` | Verifies hooks.lock at SessionStart; run `approve-hooks` after legit edits |
<!-- /managed:pack-security-hardening -->
