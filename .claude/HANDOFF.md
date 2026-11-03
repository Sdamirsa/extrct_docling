# Hand-off — `extrct_docling` (Amir Engine on Docling)

> Use this as the first thing you read when you take over the repo. Cross-references: [REPO_CONTEXT.md](REPO_CONTEXT.md) (architecture map), [AMIR_STAGE.md](AMIR_STAGE.md) (live status), [AMIR_TODO.md](AMIR_TODO.md) (phase plan), [AMIR_cheatsheet.html](AMIR_cheatsheet.html) (commands).

## 1 · TL;DR

This is a fork of [`docling-project/docling`](https://github.com/docling-project/docling) (package name in this fork: `docling-slim`) that adds a small **Amir Engine** subpackage at `docling/engines/`. The engine wraps Docling's `DocumentConverter` and produces a fully-inspectable, agent-readable bundle for every PDF: linked + standalone markdown, full `DoclingDocument` JSON, per-node JSONL, chunked text JSONL, structured tables + figures JSONL, run metadata, page + figure + table images, and a clickable HTML preview. It also bundles a `amir-batch` CLI, a `run_comparison()` runner that A/Bs against a full-page VLM, and a noise filter that drops journal logos / repeated banners from the output. Phases 1+2+3 of the plan are done; phase 4 (LLM context enrichment) was deliberately dropped — downstream consumers run their own LLM over the chunks if they want.

Branch `dgx` is current. Current release: **`extrct_docling-v2.131.0-r1`** (https://github.com/Sdamirsa/extrct_docling/tree/extrct_docling-v2.131.0-r1); releases are `extrct_docling-v<docling version>-r<n>` tags, `ENGINE_VERSION` in `docling/engines/run_snapshot.py` must equal the part after `-v`; cut releases with the `release-tag` skill (`.claude/skills/release-tag/`, includes a sensitive-content scan), and every `run.json` records it under `engine` (README § Releases). Push protocol: maintainer pushes themselves; do **not** push to `main`/`master` without explicit ask.

## 2 · What's in the repo

```
extrct_docling/
├── docling/                          # upstream Docling — don't modify unless necessary
│   ├── backend/  pipeline/  models/  datamodel/  cli/  ...
│   ├── document_converter.py         # upstream entry point
│   └── engines/                      # ⭐ AMIR ENGINE (all the work lives here)
│       ├── pdf_engine.py             # main facade — PdfEngine.convert()
│       ├── schemas.py                # PdfConversionOutput (pydantic)
│       ├── validation.py             # classify_source / validate_pdf_source
│       ├── artifacts.py              # document.json + nodes.jsonl + figure/table crops
│       ├── chunker.py                # HybridChunker → chunks.jsonl
│       ├── structured_outputs.py     # tables.jsonl + figures.jsonl (flat schema for agents)
│       ├── picture_filter.py         # noise tagging (logos, repeated banners)
│       ├── figure_typing.py          # BiomedCLIP zero-shot figure type (ecg, ct, kaplan_meier, ...)
│       ├── vlm_specs.py              # picture-description VLM presets (Qwen2.5-VL-3B, Granite-Vision-4.1-4b)
│       ├── compare_pipelines.py      # standard vs full-page VLM A/B runner
│       ├── visualizer.py             # clickable bbox HTML viewer (preview.html)
│       ├── html_export.py            # standalone <stem>.html (provenance attrs + JSON manifest)
│       ├── run_snapshot.py           # run.json (env + timing + models)
│       └── cli.py                    # `amir-batch` typer CLI
├── tests/test_engines/               # test_pdf_engine.py + test_html_export.py; 18 pass, 1 skip
├── showcase/                         # demo bundles of the first author's paper — CC BY-NC-ND 4.0, NOT MIT (showcase/LICENSE)
├── samples/                          # gitignored except README — drop PDFs here
├── .claude/                          # project-local agent config
│   ├── REPO_CONTEXT.md               # architecture cheat-sheet
│   ├── AMIR_TODO.md                  # phase plan
│   ├── AMIR_STAGE.md                 # live status + log
│   ├── AMIR_cheatsheet.html          # commands reference
│   ├── HANDOFF.md                    # this file
│   ├── issues-with-docling/          # open upstream bugs we ship around
│   ├── private-hand-off/             # gitignored — sensitive notes (machine paths etc.)
│   ├── rules/                        # path-scoped agent instructions
│   ├── skills/                       # auto-triggered workflows
│   ├── agents/                       # delegatable subagents
│   └── reference/                    # reference docs (consult INDEX.md before adding new)
├── AGENTS.md                         # upstream Docling's agent guidance
├── CLAUDE.md                         # project guidance (points to .claude/)
├── tach.toml                         # module-coverage enforcement; `docling.engines` IS registered
├── pyproject.toml                    # `amir-batch` script entry; package = docling-slim
└── Makefile                          # `make validate`, `make check`, `make test`
```

**Important boundary rule**: keep new Amir-Engine code under `docling/engines/`. Don't add files under `docling/models/`, `docling/utils/`, `docling/datamodel/` — those are reserved for upstream model wrappers / utilities, and putting our schemas there creates merge friction. This is enforced by convention and called out in `AMIR_STAGE.md` under "Path deviations from the TODO".

## 3 · What the engine does (per PDF)

```python
from pathlib import Path
from docling.engines import PdfEngine

out = PdfEngine().convert(
    Path("samples/my.pdf"),
    output_dir=Path("samples/out"),
    make_html_preview=True,
)
```

Produces `samples/out/<my>/`:

| File | Content | When written |
|---|---|---|
| `<my>.md` | Linked markdown — `![](images/picture_NNN.png)` refs; noise pictures replaced by `<!-- noise picture: reason -->` | default |
| `<my>.embedded.md` | Standalone — base64-inlined images (same noise filtering); ~10–15× larger | when `embed_images=True` (default) |
| `<my>.html` | Standalone manuscript HTML — blocks tagged `data-self-ref`/`data-page`/`data-bbox`, JSON manifest (figures/tables/chunks/run) in `<script id="extrct-manifest">`; holds every `document.json` item (furniture, noise pictures, figure text, table footnotes marked, not dropped); `docling/engines/html_export.py` | when `embed_images=True` (default) |
| `document.json` | Full `DoclingDocument` (round-trippable) | `save_artifacts=True` (default) |
| `nodes.jsonl` | One JSON per `iterate_items()` node — label, prov/bbox, text, captions, table data, `_kind`, `_level`, `image_path` | `save_artifacts=True` |
| `chunks.jsonl` | HybridChunker output: `{index, text, token_count, headings, captions, page_nos, self_refs}` | `save_artifacts=True` |
| `tables.jsonl` | Per-table: `caption_text`, `markdown`, `html`, dims, flat cells (with row/col offsets and spans), `image_path` | `save_artifacts=True` |
| `figures.jsonl` | Per-figure: `caption_text`, `image_path`, `figure_type` (+ `_confidence`, `_model`; BiomedCLIP), `vlm_caption`, `generic_classifier_label` (noise filter only), `is_noise`, `noise_reason`, raw annotations | `save_artifacts=True` |
| `run.json` | schema_version, source, status, timing, full `engine_config`, full `pipeline_options` (incl. model spec), per-stage models summary, environment (python / platform / package versions) | `save_artifacts=True` |
| `images/page_NNNN.png` | Page renders | when image gen on (auto if `save_artifacts`) |
| `images/picture_NNN.png` | `PictureItem.get_image()` crops | same |
| `images/table_NNN.png` | `TableItem.get_image()` crops | same |
| `preview.html` | Clickable bbox viewer. Top: summary chips (pages / figures / tables / chunks / noise). Click: per-kind formatted side panel (picture: caption + VLM desc + classifier + thumbnail; table: dims + rendered HTML; text: body). Noise pictures rendered dashed-gray with "noise" badge. Raw JSON behind a "Show raw" toggle. | `make_html_preview=True` |

The comparison runner (`run_comparison(...)` or `amir-batch --compare`) writes two subfolders and a side-by-side summary:

```
samples/out/<my>/
├── standard/         # the bundle above, regular pipeline
├── full_page_vlm/    # the bundle above, produced via VlmPipeline (default GraniteDocling)
└── comparison.md     # status / duration / page / figure / table / chunk counts + first lines of each markdown
```

## 4 · Defaults & flags

Default `PdfEngine(...)` is intentionally heavy-and-good:

| Flag | Default | What it means |
|---|---|---|
| `save_artifacts` | `True` | Writes the full bundle |
| `link_images` | `True` | Primary `.md` references image files |
| `embed_images` | `True` | Additionally writes `.embedded.md` (base64) |
| `filter_noise_pictures` | `True` | Auto-enables `do_picture_classification`; tags + strips logos / repeated banners |
| `granite_vision_tables` | `True` | Swap TableFormer for **Granite-Vision 4.1-4B** (`GraniteVisionTableStructureOptions`) — better on messy tables |
| `picture_description` | `"granite_vision_4b"` | VLM captions on every figure via **Granite-Vision 4.1-4B** |
| `picture_description_engine` | `"default"` | `AUTO_INLINE` — uses vLLM if installed, else transformers (no crash on env mismatch) |
| `chunk_tokenizer` | `sentence-transformers/all-MiniLM-L6-v2` | HybridChunker tokenizer |
| `chunk_max_tokens` | `512` | Matches MiniLM `model_max_length` |

**Heavy-mode implications**: first run downloads Granite-Vision 4.1-4b (~13 GB on disk; one model serves both tables and figures). After cache, conversion time per PDF goes from ~12 s (fast mode) to ~60–120 s (default). The maintainer accepted this trade-off — agents that prefer speed pass `picture_description=None, granite_vision_tables=False`.

**Why we built our own `granite_vision_4b` preset**: Docling only registers a `granite_vision` picture-description preset pointing at 3.3-2B. The newer 4.1-4B exists in `vlm_model_specs.py` but only as a full-page-VLM convert spec. Our preset lives in `docling/engines/vlm_specs.py` so switching to Qwen3-VL or a newer Granite is a one-line edit (change `default_repo_id`).

## 5 · CLI

```bash
uv run amir-batch <pdf-or-folder>...                       # convert (rich progress + summary table)
uv run amir-batch samples/ -o samples/out                  # custom output root
uv run amir-batch samples/ --compare                       # standard + full-page VLM A/B
uv run amir-batch samples/ --no-preview                    # skip HTML
uv run amir-batch samples/ --picture-description off       # skip VLM captions (much faster)
uv run amir-batch samples/ --no-granite-vision-tables      # use TableFormer instead of Granite-Vision
uv run amir-batch --help                                   # all flags
```

The CLI is `docling/engines/cli.py` (typer + rich), wired via `pyproject.toml` `[project.scripts]` as `amir-batch`.

## 6 · Setup

```bash
# aarch64 / Jetson / DGX Spark — `make setup` and `uv sync --all-extras` are BROKEN
# (no onnxruntime-gpu wheel). Use this targeted install instead:
uv sync --frozen --no-group docs --extra standard --extra feat-ocr-rapidocr-onnx --extra models-vlm-inline   # onnx extra keeps RapidOCR working; models-vlm-inline brings open-clip-torch for figure types

# Reinstall the package whenever pyproject scripts/entries change:
uv pip install -e .
```

The `standard` extra includes `format-pdf`, `models-local` (torch), `feat-ocr-rapidocr`, office/web/latex backends, chunking, CLI, extract-core — enough for the full Amir Engine. The aarch64 install gotcha is documented in detail in `.claude/REPO_CONTEXT.md`; a permanent fix is hand-off'd under `.claude/private-hand-off/onnxruntime-gpu-aarch64.md` (gitignored).

## 7 · Gates

```bash
make validate                              # full pre-commit gate (ruff, ty, tach, etc.)
make check                                 # read-only checks
make test                                  # full pytest
uv run pytest tests/test_engines/ -q       # just engine tests (fast — 18 pass, 1 skip)
```

`tach.toml` enforces module coverage. `docling.engines` is registered as a module under the `entrypoints` layer.

## 8 · Phase status

- **Phase 1 — PDF → structured conversion** ✅ — `PdfEngine`, schemas, validation, artifacts, run snapshot, HTML preview.
- **Phase 2 — Chunking + structured JSON outputs** ✅ — HybridChunker, tables.jsonl, figures.jsonl.
- **Phase 3 — VLM integration** ✅ — Granite-Vision-4.1-4B picture description, Granite-Vision-4.1-4B tables, picture noise filter, full-page VLM comparison runner, extended HTML preview.
- **Phase 4 — LLM context enrichment** ❌ **DROPPED** (2026-05-21). Decision: keep the engine focused on clean structured JSON; LLM summarization / topic / metadata extraction belongs in a downstream consumer reading the `chunks.jsonl` + `figures.jsonl` + `tables.jsonl` bundle.
- **Phase 5 — FastAPI + batch CLI** — only the CLI is done (`amir-batch`). REST API not started; not currently planned.
- **Phase 6 — Docker / deploy** — not started.

## 9 · Known issues + non-obvious things to know

- **Reading-order column-flip on mixed-layout pages** — `samples/test-pdf-ai-manuscript.pdf` is the reproducer. Docling's layout post-processor emits the right column before the left when a full-width region (abstract spillover) sits above a two-column body. Documented in `.claude/issues-with-docling/reading-order-mixed-layout-page.md`. Not yet filed upstream. Workaround #1 (`force_backend_text=True`) is hypothesised, untested. We ship as-is; revisit when a downstream consumer's hierarchy depends on order.
- **OCR is rarely active** on born-digital PDFs — `pypdfium2` provides the text. RapidOCR fires only on figure-region crops and usually returns empty. The "RapidOCR returned empty result!" warning is normal. If you ever process scans, the right upgrade is `run_comparison(vlm_preset="nanonets_ocr2")`, not switching the OCR engine.
- **vLLM** is not installed in this env. The engine defaults to `picture_description_engine="default"` which uses `AUTO_INLINE` and gracefully falls back to transformers. Forcing `"vllm"` without `pip install vllm` crashes the pipeline at convert time, not at engine construction.
- **`run.json` uses `serialize_as_any=True`** on `pipeline_options.model_dump()` so subclass fields like `layout_options.model_spec` survive (otherwise pydantic strips them — see Docling commit history).
- **Picture noise classifier** uses `document_figure_classifier_v2` (downloaded on first use). Labels observed in the wild: `logo`, `signature`, `watermark`, `barcode`, `qr_code`, `page_header`, `page_footer`, `photograph`, `box_plot`, `scatter_plot`, `icon`, `full_page_image`. The noise set in `picture_filter.py::DEFAULT_NOISE_CLASSES` is configurable.
- **`.claude/hooks/lib/` must stay tracked.** Upstream's `.gitignore` ignores every `[Ll]ib` folder, so until 2026-11-02 the hooks' shared helpers were never committed and 5 of the 6 project hooks (secrets and destructive-command guards included) crashed on import in any fresh clone — silently, since a crashing hook doesn't block. `.gitignore` now re-includes it with `!.claude/hooks/lib/`. If a hook raises `ModuleNotFoundError` on a new machine, check this first.
- **`showcase/` is not MIT.** The paper (arXiv:2409.00084; published as npj Digit Med 8, 797, 2025) and every conversion of it are CC BY-NC-ND 4.0 — see `showcase/LICENSE`. Keep that file and the README citation when regenerating. The maintainer chose to keep the full paper (2026-11-02) over a page excerpt or a CC BY replacement: the license allows sharing it in whole or in part, and it has been public in history since `c6aacb06`.
- **Conversion weak spots** seen on a 4-paper batch (2026-11-02): a 20-page SSRN-formatted paper came out as 5 text blocks with no headings, and text printed inside figures (axis labels, panel text) leaks into the body text of `<stem>.md` / chunks. Not investigated.
- **Granite-Vision tables retype cell text from the image** (`<tables_otsl>` output carries the text) instead of reading the PDF, and its generation had no length limit (tokenizer `model_max_length` is unset, ~1e30): a supplement of 41 boxed prompts, which the layout model calls tables, generated for 75+ min with GPU memory climbing 17 → 57 GB. `_generation_budget` in `table_structure_model_granite_vision.py` now caps each page at max(2048, 3 × PDF-text tokens in the crops + 512) — no real table of 88 came near it. Tables whose cells hold < 95 % of the words printed in their box keep that text (`amir__pdf_text`, HTML `details.extrct-table-pdf-text`); 10 of 88 did.
- **Hostname / machine paths** must never be committed to repo docs — keep them in `.claude/private-hand-off/` (gitignored). The maintainer is sensitive to this; we had to relocate one hand-off doc after a previous leak.

## 10 · Conventions (load-bearing)

- `pathlib.Path` everywhere new; no `os.path`. No `hasattr` probing.
- Prefer Pydantic v2 models for any data that crosses module boundaries. Lean on `Field(default=None, exclude=True)` to keep raw upstream objects (e.g. `ConversionResult`) off serialised output.
- No comments unless the *why* is non-obvious. Don't reference the current task / fix / PR in code comments.
- New Amir code → `docling/engines/<name>.py`. New schemas → extend `docling/engines/schemas.py`, don't create new modules.
- Tests live in `tests/test_engines/`. Heavy-model tests (VLM, classifier) should pass `picture_description=None, granite_vision_tables=False` so CI doesn't try to download multi-GB models.
- Memory: persistent agent memory lives at `~/.claude/projects/.../memory/`. Don't write memories for things derivable from code or git log. Update stale memories instead of duplicating.
- Git: maintainer pushes themselves. Never `--force` push to main/master/develop/release. Never `--no-verify`.

## 11 · How to use this as a sub-module

```bash
# In the consumer repo:
git submodule add -b dgx https://github.com/Sdamirsa/extrct_docling.git vendor/extrct_docling
git submodule update --init --recursive
cd vendor/extrct_docling
uv sync --frozen --no-group docs --extra standard --extra feat-ocr-rapidocr-onnx --extra models-vlm-inline   # onnx extra keeps RapidOCR working; models-vlm-inline brings open-clip-torch for figure types

# Then use the package the same way as in this repo:
python -c "from docling.engines import PdfEngine; print(PdfEngine)"
```

To pin a release (so the consumer doesn't drift when `dgx` advances):

```bash
cd vendor/extrct_docling && git checkout extrct_docling-v2.131.0-r1 && cd ../..
git add vendor/extrct_docling && git commit -m "pin extrct_docling@extrct_docling-v2.131.0-r1"
```

## 12 · What to do next (if you take over)

Pick one of these based on the maintainer's ask:

1. **Conversion quality on hard layouts.** The SSRN paper and figure-text leaks under §9 "Conversion weak spots". (The old "real GPU validation pass" item is done — see the 2026-08-07 and 2026-10-01 rows in `AMIR_STAGE.md`.) Older bundles (`showcase/`, earlier sample runs) predate `<stem>.html`; `rebuild_document_html(pdf_dir)` backfills it without reconverting.
2. **Reading-order bug** — test workaround #1 (`force_backend_text=True`) on `test-pdf-ai-manuscript.pdf`. If it fixes the column flip, expose a `reading_order` knob on `PdfEngine`. Otherwise file upstream per the checklist in `issues-with-docling/reading-order-mixed-layout-page.md`.
3. **Tokenizer / VLM upgrades**, per "Future considerations" in `AMIR_TODO.md`: swap `sentence-transformers/all-MiniLM-L6-v2` → `Qwen/Qwen3-Embedding-4B` (bump `chunk_max_tokens` to 1024–2048) and `Qwen/Qwen2.5-VL-3B-Instruct` → Qwen3-VL once vLLM ships stable support. Both are one-line changes in `docling/engines/vlm_specs.py` / `pdf_engine.py`.
4. **onnxruntime-gpu on aarch64** — there's a separate hand-off at `.claude/private-hand-off/onnxruntime-gpu-aarch64.md` (gitignored) for getting GPU OCR working system-wide on the DGX Spark.

If the maintainer asks for "the full picture" again, point them at:
- `AMIR_cheatsheet.html` for commands
- `REPO_CONTEXT.md` for architecture
- `AMIR_STAGE.md` for current state
- this file for the hand-off context

Good luck.
