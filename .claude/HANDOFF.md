# Hand-off — `extrct_docling` (Amir Engine on Docling)

> Use this as the first thing you read when you take over the repo. Cross-references: [REPO_CONTEXT.md](REPO_CONTEXT.md) (architecture map), [AMIR_STAGE.md](AMIR_STAGE.md) (live status), [AMIR_TODO.md](AMIR_TODO.md) (phase plan), [AMIR_cheatsheet.html](AMIR_cheatsheet.html) (commands).

## 1 · TL;DR

This is a fork of [`docling-project/docling`](https://github.com/docling-project/docling) (package name in this fork: `docling-slim`) that adds a small **Amir Engine** subpackage at `docling/engines/`. The engine wraps Docling's `DocumentConverter` and produces a fully-inspectable, agent-readable bundle for every PDF: linked + standalone markdown, full `DoclingDocument` JSON, per-node JSONL, chunked text JSONL, structured tables + figures JSONL, run metadata, page + figure + table images, and a clickable HTML preview. It also bundles a `amir-batch` CLI, a `run_comparison()` runner that A/Bs against a full-page VLM, and a noise filter that drops journal logos / repeated banners from the output. Phases 1+2+3 of the plan are done; phase 4 (LLM context enrichment) was deliberately dropped — downstream consumers run their own LLM over the chunks if they want.

Branch `dgx` is current. Current release: **`extrct_docling-v2.131.0-r6`** (https://github.com/Sdamirsa/extrct_docling/tree/extrct_docling-v2.131.0-r6); releases are `extrct_docling-v<docling version>-r<n>` tags, `ENGINE_VERSION` in `docling/engines/run_snapshot.py` must equal the part after `-v`; cut releases with the `release-tag` skill (`.claude/skills/release-tag/`, includes a sensitive-content scan), and every `run.json` records it under `engine` (README § Releases). Push protocol: maintainer pushes themselves; do **not** push to `main`/`master` without explicit ask.

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
│       ├── text_repair.py            # PDF text-layer checks: ligature rejoin, table PDF-text fallback, heading type (font size / weight / slant)
│       ├── structure.py              # structure pass: furniture, captions, title, heading levels, roles + links, quality report (structure.json); rules in .claude/reference/structure/RULES.md
│       ├── run_snapshot.py           # run.json (env + timing + models)
│       ├── sources.py                # inputs that are not PDFs: a .docx becomes a PDF (Docling's LibreOffice helper), a .zip stands for the PDF and Word files inside it
│       └── cli.py                    # `amir-batch` typer CLI
│       └── figure_data/              # the figure-to-data step (2026-11-18): prepare.py, methods/ (ollama, cloud + endpoint, agent + toolbox, claude_cli), reading.py, report.py, step.py, publish.py; the measured engine (pipeline, panels, evidence, readers, verify); `amir-figdata` CLI; design in .claude/reference/figure-data/
├── tests/test_engines/               # engine tests (pdf_engine, html_export, export_check, cli, figure_data); tests/data/figure_data/ holds the 5-figure smoke set + agent-made truth
├── tools/figure-labeler/             # local HTML labelling kit (pack.py → self-contained folder; validate.py); packs under samples/figure-labeler-packs/ (git-ignored)
├── showcase/                         # demo bundles of the first author's paper — CC BY-NC-ND 4.0, NOT MIT (showcase/LICENSE)
├── samples/                          # gitignored except README — working set `aca-papers/` → `aca-papers_out/`; earlier sets and outputs under `archived/`
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
| `<my>.md` | Linked markdown — `![](images/picture_NNN.png)` refs; noise pictures replaced by `<!-- noise picture: reason -->`; VLM figure descriptions wrapped in `<!--<annotation kind="description">-->…<!--<annotation/>-->`; a table whose cells miss printed words is followed by `Table text from the PDF (cell recall 0.61): …` (`docling/engines/serializers.py`, shared with the chunker) | default |
| `<my>.embedded.md` | Standalone — base64-inlined images (same noise filtering); ~10–15× larger | when `embed_images=True` (default) |
| `<my>.html` | Standalone manuscript HTML — blocks tagged `data-self-ref`/`data-page`/`data-bbox`, JSON manifest (figures/tables/chunks/run) in `<script id="extrct-manifest">`; holds every `document.json` item (furniture, noise pictures, figure text, table footnotes marked, not dropped); `docling/engines/html_export.py` | when `embed_images=True` (default) |
| `document.json` | Full `DoclingDocument` (round-trippable) | `save_artifacts=True` (default) |
| `nodes.jsonl` | One JSON per `iterate_items()` node — label, prov/bbox, text, captions, table data, `_kind`, `_level`, `image_path` | `save_artifacts=True` |
| `chunks.jsonl` | HybridChunker output: `{index, text, token_count, headings, captions, page_nos, self_refs}` | `save_artifacts=True` |
| `tables.jsonl` | Per-table: `caption_text`, `markdown`, `html`, dims, flat cells (with row/col offsets and spans), `image_path` | `save_artifacts=True` |
| `figures.jsonl` | Per-figure: `caption_text`, `image_path`, `figure_type` (+ `_confidence`, `_model`; BiomedCLIP), `vlm_caption`, `generic_classifier_label` (noise filter only), `is_noise`, `noise_reason`, raw annotations | `save_artifacts=True` |
| `structure.json` | Where each element sits (`docling/engines/structure.py`, rules in `.claude/reference/structure/RULES.md`): `outline` (section headers with level, number, title, page, parent, path, zone, level_source), `elements` (per `self_ref`: role, section_ref, number, caption links, first mention, what a rule relabelled), `relabels`, `structure_version`. The pass runs before every export and changes labels in place (`self_ref`s stay): a line repeated in the page margin → page header/footer, `Table S11. …` / `Fig. 2` headings → captions tied to their table/figure, the title → `title`, heading levels → `SectionHeaderItem.level` (so `<h2>`..`<h6>`, markdown `##`/`###` and chunk heading paths follow). `<my>.html` carries the same as `data-role`, `data-level`, `data-section-ref`, `data-number`, `data-caption-ref`, `data-for`, ... | `save_artifacts=True` |
| `run.json` | `structure_version`, `quality` (label counts per document and page, `pages_without_text`, `chars_in_tables_share`, `warnings` with stable codes; a blocking one — `few_text_blocks`, `no_body_text` — adds a `quality` error and sets PARTIAL_SUCCESS), `document_role` and `related` (supplement ↔ manuscript, paired by file name in `amir-batch`), schema_version, `engine` (release version, exact `release` tag or null, git commit, dirty flag), source, status, timing, full `engine_config`, full `pipeline_options` (incl. model spec), per-stage models summary, environment (python / platform / package versions / torch CUDA build + device), per-step `errors`, `complete: true` (written last; a bundle without it was interrupted) | `save_artifacts=True` |
| `check.json` | Bundle self-check (`docling/engines/export_check.py`, `check_bundle`): HTML item coverage (every `document.json` item tagged once), per-page PDF text-layer recall (multiset; flags < 0.90 or ≥ 50 lost words, document < 0.97, top missing tokens), uncovered text (printed words of a page — runs of ≥ 2 letters, so unmapped-font glyphs don't count — whose letters lie in no item box on that page, CropBox/`/Rotate`-aware, off-page text ignored; flags > 5 % or ≥ 30 words on pages of ≥ 30 words, with a 70-char sample), export fidelity vs `document.json` (html / md / chunks ≥ 0.99, VLM text stripped), ligature-split marker (L-2), tables (low cell recall, degenerate grids), empty chunks, structure sanity (no headings on a long paper), cheap guards; `ok` + `issues` roll-up; `summary_line()` is the CLI column | `save_artifacts=True` |
| `images/page_NNNN.png` | Page renders | when image gen on (auto if `save_artifacts`) |
| `images/picture_NNN.png` | `PictureItem.get_image()` crops | same |
| `images/table_NNN.png` | `TableItem.get_image()` crops | same |
| `preview.html` | Clickable bbox viewer. Top: summary chips (pages / figures / tables / chunks / noise / chart figures with data). Click: per-kind formatted side panel (picture: caption + VLM desc + figure data read by a model + classifier + thumbnail; table: dims + rendered HTML; text: body). Noise pictures rendered dashed-gray with "noise" badge, figures with a reading tagged "data". Raw JSON behind a "Show raw" toggle. Rebuilt from the bundle's files by the figure-to-data step (`rebuild_html_preview`). | `make_html_preview=True` |

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
uv run amir-batch samples/ --no-skip-existing              # redo bundles that are already complete (default: skip them)
uv run amir-batch samples/ --check-only                    # re-run the bundle self-check on existing bundles, no conversion
uv run amir-batch samples/ --retries 2                     # engine exceptions are retried N times (default 1)
uv run amir-batch --help                                   # all flags
```

The CLI is `docling/engines/cli.py` (typer + rich), wired via `pyproject.toml` `[project.scripts]` as `amir-batch`. One `PdfEngine` is built per batch (models load once); the summary has a `check` column (`check.json` summary), rows with a failed export step show `SUCCESS*`, and the exit code is 1 when any row is FAILURE/PARTIAL_SUCCESS/EXCEPTION/SUCCESS*/MISSING/INCOMPLETE, 3 when the only problems are bundle-check issues, else 0 (same rule for `--check-only`). Output folders are sanitized stems; collisions within a batch (or with a folder holding a different PDF) get `_2`, `_3`... Ctrl-C ends the batch with exit 130.

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
uv run pytest tests/test_engines/ -q       # just engine tests (fast — 21 pass, 1 skip)
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

- **Reading-order column-flip on mixed-layout pages** — `samples/archived/test-pdf-ai-manuscript.pdf` is the reproducer. Docling's layout post-processor emits the right column before the left when a full-width region (abstract spillover) sits above a two-column body. Documented in `.claude/issues-with-docling/reading-order-mixed-layout-page.md`. Not yet filed upstream. Workaround #1 (`force_backend_text=True`) is hypothesised, untested. We ship as-is; revisit when a downstream consumer's hierarchy depends on order.
- **Upstream bug, patched in the fork: cross-page merges on pages of another size.** `ReadingOrderModel` converted the box of a paragraph's continuation with the height of the page the paragraph *starts* on, so a continuation from a landscape page (612 pt high) onto a portrait one (792 pt) landed 180 pt too low (showcase p7 `#/texts/44`: t 537 instead of 717). The fork passes the continuation's own page height (`readingorder_model.py`, `materialize_siblings`; test `tests/test_readingorder_cross_page_merge.py`); to be filed upstream. `check.json`'s `uncovered_text` is what catches this class of bug.
- **OCR is rarely active** on born-digital PDFs — `pypdfium2` provides the text. RapidOCR fires only on figure-region crops and usually returns empty. The "RapidOCR returned empty result!" warning is normal. If you ever process scans, the right upgrade is `run_comparison(vlm_preset="nanonets_ocr2")`, not switching the OCR engine.
- **vLLM** is not installed in this env. The engine defaults to `picture_description_engine="default"` which uses `AUTO_INLINE` and gracefully falls back to transformers. Forcing `"vllm"` without `pip install vllm` crashes the pipeline at convert time, not at engine construction.
- **`run.json` uses `serialize_as_any=True`** on `pipeline_options.model_dump()` so subclass fields like `layout_options.model_spec` survive (otherwise pydantic strips them — see Docling commit history).
- **Picture noise classifier** uses `document_figure_classifier_v2` (downloaded on first use). Labels observed in the wild: `logo`, `signature`, `watermark`, `barcode`, `qr_code`, `page_header`, `page_footer`, `photograph`, `box_plot`, `scatter_plot`, `icon`, `full_page_image`. The noise set in `picture_filter.py::DEFAULT_NOISE_CLASSES` is configurable.
- **`.claude/hooks/lib/` must stay tracked.** Upstream's `.gitignore` ignores every `[Ll]ib` folder, so until 2026-11-02 the hooks' shared helpers were never committed and 5 of the 6 project hooks (secrets and destructive-command guards included) crashed on import in any fresh clone — silently, since a crashing hook doesn't block. `.gitignore` now re-includes it with `!.claude/hooks/lib/`. If a hook raises `ModuleNotFoundError` on a new machine, check this first.
- **`showcase/` is not MIT.** The paper (arXiv:2409.00084; published as npj Digit Med 8, 797, 2025) and every conversion of it are CC BY-NC-ND 4.0 — see `showcase/LICENSE`. Keep that file and the README citation when regenerating. The maintainer chose to keep the full paper (2026-11-02) over a page excerpt or a CC BY replacement: the license allows sharing it in whole or in part, and it has been public in history since `c6aacb06`.
- **Upstream bug, patched in the fork: a diagonal watermark folds each page into one text block** (the 20-page SSRN paper that came out as 5 text blocks with no headings, 2026-11-02; found 2026-11-16). The watermark is one rotated text cell whose upright box spans the page; `LayoutPostprocessor` either assigned it to a paragraph and stretched that paragraph's box, or made it an orphan cluster that won every overlap. `_find_overlay_cells` keeps such a cell out (skewed > 5°, box ≥ 10 % of the page, upright text in the majority), `Cluster.overlay` carries it to the reading-order stage, which writes it to the `background` content layer outside the reading flow. The accepted-manuscript paper ("ARTICLE IN PRESS") had the same bug: 12 real headings were lost. A/B on 52 sample PDFs: 50 unchanged. Details and what is not covered: `.claude/issues-with-docling/watermark-cell-swallows-page.md`. Bundles converted before this fix (r1-r3) of a watermarked PDF must be reconverted; `run.json` → `quality.warnings` (`few_text_blocks`) now flags the collapse.
- **Heading levels need the PDF.** Box sizes vary ±10 % between headings set alike, so levels of unnumbered, unnamed headings are ranked by the type read from the PDF text layer (`pdf_text_styles`); a URL source or a rebuilt old bundle falls back to coarse box sizes. Where every heading is set alike, unnamed headings nest under the standard-named section before them. Limits in `.claude/reference/structure/RULES.md`.
- **Conversion weak spot, open**: text printed inside figures (axis labels, panel text) leaks into the body text of `<stem>.md` / chunks when the layout model misses the figure.
- **A PDF whose text layer does not say what the pages print** (found 2026-11-20 on the `nirct_validation22` set, fixed in r6: `docling/utils/text_layer.py`). A font embedded without a Unicode map leaves the text layer with glyph codes: "6DPSOH VL]H" where the page prints "Sample size". r5 converted such pages to unreadable text with status SUCCESS, and the check saw only a low recall. On 4,723 pages (87 PDFs) five PDFs have it, in two kinds, judged per font object on a page as pdfium reports it. *Glyph order* (3 PDFs, 124 pages; one supplement on all 57 pages): the codes are glyph numbers of the standard TrueType order, 29 below ASCII; the text is recovered exactly and written into the page's text cells in the preprocessing stage, so layout, tables and exports see the printed text. *Unmapped* (3 PDFs, 11 pages: shell tables of a statistical analysis plan, a signature page, a journal's reporting form): codes handed out as the characters came; a page with 30 % or more such characters loses its text cells and is read by Docling's OCR as a whole (`Page.text_layer_unreadable`). Recorded in `run.json` → `quality.text_layer` with warnings `text_layer_decoded`, `text_layer_read_by_ocr`, `text_layer_partly_unreadable` (and blocking `text_layer_unreadable` when OCR is off), and in `check.json` → `text_layer`; `page_recall` checks a decoded page against its decoded text and leaves an OCR page out. Measured before choosing: OCR of a glyph-order page through the pipeline holds 70 to 97 % of the printed words (RapidOCR loses about one line in twelve of plain prose), decoding holds all of them, so OCR is only for what cannot be decoded. Not covered: a glyph-order font object whose characters on a page hold no space, digit or punctuation (a one-word heading) is left as it is; single unmapped symbols of an otherwise readable font (a "±" in a math font) are counted and not repaired; glyph numbers past 182 come out as U+FFFD.
- **A long `amir-batch` run can die with a segmentation fault** (exit 139, no Python trace; once, 2026-11-19, at the 38th document after 6.2 h, in the full configuration). Not caused by the document: it converted on the next pass. Run the same command again: complete bundles are skipped. A watcher has to look at the exit code, not at the log, to see it.
- **Granite-Vision tables retype cell text from the image** (`<tables_otsl>` output carries the text) instead of reading the PDF, and its generation had no length limit (tokenizer `model_max_length` is unset, ~1e30): a supplement of 41 boxed prompts, which the layout model calls tables, generated for 75+ min with GPU memory climbing 17 → 57 GB. `_generation_budget` in `table_structure_model_granite_vision.py` now caps each page at max(2048, 3 × PDF-text tokens in the crops + 512) — no real table of 88 came near it. Tables whose cells hold < 95 % of the words printed in their box keep that text (`amir__pdf_text`, HTML `details.extrct-table-pdf-text`); 10 of 88 did.
- **Granite-Vision budget: do not raise it for "long tables".** Measured on the r3 smoke run (2026-11-04): the two tables that hit their budget were the model looping, not long content — AMIE-Mx p37 generated 8,054 tokens (175 × 9 grid, 59 cells "✓", 50 cells "2") for a box printing 365 words; EchoAgent-Guideline p3 generated a 1 × 679 grid for a 49-word boxed block the layout model calls a table. Real tables stay under 3 × PDF-text tokens (median 1.4×), which the budget already allows. A bigger budget only makes the loop longer (this was the 75-min hang). Such a table is now redone by TableFormer (`GraniteVisionTableStructureOptions.tableformer_fallback`, default on): a crop that hits the budget, or whose grid is degenerate by the rule `check.json` uses (`degenerate_table_reason` in `docling/datamodel/base_models.py`), takes TableFormer's structure, matched to the PDF's text cells; the log says `GraniteVision table [id] on page N: <reason>; structure taken from TableFormer`. The floor stays 2048: measured on EchoAgent p3, Granite loops for 92 s to a 2,048 budget and 188 s to 4,096 before TableFormer (0.2 s) replaces it either way, so a higher floor only burns time. Measured 2026-11-05: EchoAgent p3 → 8 × 6 grid, cell recall 1.00 (was 0.06), check clean; AMIE-Mx p37 → 37 × 9, recall 1.00 (was 0.22; Granite's 100 guideline URLs were invented, TableFormer has the 120 printed ones), 32 % filled — just over the 30 % line — and 20 cells hold two or more rows' URLs, so the row structure of that dense list is still coarse. TableFormer adds 0.2 s per page.
- **Docling's HTML serializer leaves things out** that `html_export.py` puts back: picture children (text inside figures), furniture (`HTMLParams.layers` defaults to body), footnotes of floating items and captions of code blocks (the doc serializer leaves them to the floating item, whose HTML serializer never renders them). `test_document_html_keeps_everything_docling_extracted` guards each; when upgrading docling-core, rerun it first.
- **Hooks are hash-locked** (`.claude/.meta/hooks.lock`, checked at session start). Claude's Edit/Write are denied in `.claude/hooks/`: the maintainer copies a hook in, then the folder-handler's `approve_hooks` re-locks. `30-ritual-ticket.py` mints the `/project-memory` ticket.
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
cd vendor/extrct_docling && git checkout extrct_docling-v2.131.0-r6 && cd ../..
git add vendor/extrct_docling && git commit -m "pin extrct_docling@extrct_docling-v2.131.0-r6"
```

## 12 · What to do next (if you take over)

Start from `.claude/STATUS.md` (rewritten by every `/project-memory`); its Next steps are current. Figure-to-data: the chart-to-data mini bench (`docs/mini-bench/chart-to-data/`, round 1 and `round-2/`, 2026-11-17) found most failures in the call path and fixed them (OCR words, tick-label panel split, overview gate, compact streamed replies); round 3 (2026-11-18, `round-3/`) built the step as its own part after the conversion with three reading methods (`ollama`, `cloud`, `agent`; `amir-batch --figure-data ...`, `amir-figdata step`), described in `.claude/reference/figure-data/STANDALONE-STEP.md`; measured on the 15 bench figures: `cloud` with Sonnet 5.5 through OpenRouter 10 of 10 data charts usable and 560 of 560 values for 0.70 USD, `agent` 10 of 10 and 470 for 1.12 USD, `cloud` with Gemini 3.8 Flash 9 of 10, `ollama` 6 of 10 with 2 misleading; round 4 (2026-11-19, `round-4/`) ran `amir-batch --figure-data` end to end with the four setups on the showcase paper (bundles in `samples/round-4-showcase/`, not published): of 573 values in its six main figures `cloud` Sonnet 5.5 had 408 right (0.91 USD, 18 min the whole command), `cloud` Gemini 3.8 Flash 554 (1.42 USD, 42 min), `agent` 251 (2.97 USD, 27 min), `ollama` 83 with three figures that would mislead; the page viewer now shows the readings (`visualizer.rebuild_html_preview`), an embedded bitmap is captured with its soft mask, the end-to-end test is `tests/test_engines/test_figure_data_batch.py`; a split-only check on 51 figures followed the same day (`round-4-plus-splitter/`, nothing built from it yet): one overview call to Sonnet 5.5 or Gemini 3.8 Flash cuts 49 of 51 figures right, the rule splitter, Docling's layout detector (Heron) and FigEx2 24 each, Gemma 28; a model's boxes clip labels and become usable crops as seeds of the rules' own cutter (220 of 236 charts whole); without a cloud call, Gemma's chart count choosing between the rules' cut and Heron's gets 35 of 51; a final test the same day (`round-4-plus-splitter/final-test/`) decided the design: the reading model lists the charts (Gemma 4 26B in the local engine's overview call; one extra call to the reading model in the cloud method, Sonnet 5.5 by default), the rule splitter's cut is taken when it has that many charts, else the rules' cutter (`panels._cut_between`) is started from the model's boxes: 37 of 51 figures cut right locally and 46 with a cloud model against 24 today; the figure's caption in that call and a second call ruling between the two cuts were tested and add nothing; Heron and FigEx2 are out; round 5 (2026-11-19, `round-5/`) built that rule (`panels.cut_from_list`; the local engine lists in its overview call, the cloud method in one extra call at low effort, `prepare.relist` cuts the prepared folder again and every run starts from the rules' cut) and ran `amir-batch --figure-data` with both on three papers: the cut right on 14 and 15 of 18 figures against 6, on the showcase paper 148 of 573 values right locally (96 before) and 378 with Sonnet (421 before: one dense single chart lost the crops a wrong cut had given it), the dense figures' sample 46 of 60 (38); a cloud reply that wraps its JSON in a sentence is now read instead of thrown away; release r5 also lets `amir-batch` take Word files and ZIP archives (`sources.py`); open after it: the read call's reasoning effort (still high), values inside one dense chart, grids of 14 to 18 small charts, the agent method (it works from the rules' cut), and the other open points of `round-4/LOG.md` section 11, a round on more papers. Background: `.claude/reference/figure-data/DESIGN.md` (decisions, wiring, schema) and `RESULTS-2026-11-09.md` (5-figure Gemma 4 test: panels and vector/printed routes exact, VLM pointing unusable → move numbers to deterministic colour geometry; then the 50-figure human set and the four-model comparison): export self-checks in `amir-batch`, Granite-Vision vs TableFormer measured on the converted batches, the upstream Granite-Vision `max_new_tokens` report, small `-r3` items. Longer-standing options:

1. **Conversion quality on hard layouts.** Figure-text leaks under §9 "Conversion weak spot, open" (the SSRN paper is fixed, see §9). (The old "real GPU validation pass" item is done — see the 2026-08-07 and 2026-10-01 rows in `AMIR_STAGE.md`.) Older bundles (`showcase/`, earlier sample runs) predate `<stem>.html`; `rebuild_document_html(pdf_dir)` backfills it without reconverting.
2. **Reading-order bug** — test workaround #1 (`force_backend_text=True`) on `test-pdf-ai-manuscript.pdf`. If it fixes the column flip, expose a `reading_order` knob on `PdfEngine`. Otherwise file upstream per the checklist in `issues-with-docling/reading-order-mixed-layout-page.md`.
3. **Tokenizer / VLM upgrades**, per "Future considerations" in `AMIR_TODO.md`: swap `sentence-transformers/all-MiniLM-L6-v2` → `Qwen/Qwen3-Embedding-4B` (bump `chunk_max_tokens` to 1024–2048) and `Qwen/Qwen2.5-VL-3B-Instruct` → Qwen3-VL once vLLM ships stable support. Both are one-line changes in `docling/engines/vlm_specs.py` / `pdf_engine.py`.
4. **onnxruntime-gpu on aarch64** — there's a separate hand-off at `.claude/private-hand-off/onnxruntime-gpu-aarch64.md` (gitignored) for getting GPU OCR working system-wide on the DGX Spark.

If the maintainer asks for "the full picture" again, point them at:
- `AMIR_cheatsheet.html` for commands
- `REPO_CONTEXT.md` for architecture
- `STATUS.md` for current state, `Project-log.jsonl` for what happened (history before 2026-11-04: `AMIR_STAGE.md`)
- this file for the hand-off context

Good luck.
