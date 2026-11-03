# Amir Engine — Current Stage

Live tracker for the build defined in [AMIR_TODO.md](AMIR_TODO.md). Keep entries short; update when starting or finishing a task.

## Current phase

**PHASE 1 + 2 + 3 — Foundation + Chunking + VLM** — **COMPLETE.** 13 tests green; smoke-tested on `samples/test-pdf-ai-manuscript.pdf` (8 pages, 0 errors, 7 figures, 5 tables, 50 chunks, journal-logo correctly flagged as noise and stripped from both markdown files).

### Phase 1 status

| TODO item | State | Notes |
|---|---|---|
| `docling/engines/pdf_engine.py` wrapper | ✅ done | Thin facade over `DocumentConverter`. |
| Output schemas | ✅ done | Landed at `docling/engines/schemas.py` (not `docling/models/engine_output.py` — `docling/models/` is reserved for upstream ML model wrappers). |
| Input validation | ✅ done | Landed at `docling/engines/validation.py` (not `docling/utils/`) so all Amir code lives in one subtree. |
| `tests/test_engines/test_pdf_engine.py` | ✅ done | Real fixture: `tests/data/pdf/sources/2305.03393v1-pg9.pdf`. 4 e2e tests + 5 unit tests. |
| Local paths + URLs | ✅ done | `classify_source()` + `validate_pdf_source()`. |
| Error handling + logging | ✅ done | Catches `ConversionError`; `_log = logging.getLogger(__name__)`. |
| HTML bbox visualiser (clickable) | ✅ done | `docling/engines/visualizer.py` — overlays are one-per-`DocItem` from `iterate_items()`, **click any bbox** to open a side panel with the node's full metadata; Esc to clear. |
| Linked + standalone markdown | ✅ done | `link_images=True` (default): primary `<stem>.md` rewrites placeholders to `![](images/picture_NNN.png)` so markdown viewers render figures. `embed_images=True` (default): additionally writes `<stem>.embedded.md` with base64 data URIs for single-file sharing. |
| Per-PDF output folder | ✅ done | All artifacts land under `<output_dir>/<pdf-stem>/` (sanitised). |
| Persistent data nodes | ✅ done | `docling/engines/artifacts.py` — writes `document.json` (full `DoclingDocument`), `nodes.jsonl` (one line per node with bbox/text/captions/table data + `image_path` for pictures/tables), and `images/picture_NNN.png` / `table_NNN.png` via `PictureItem.get_image()` / `TableItem.get_image()`. |
| Run snapshot | ✅ done | `docling/engines/run_snapshot.py` — `<pdf-dir>/run.json` with schema_version, source, status, timing (started_at / finished_at / duration_seconds), engine_config, full pipeline_options (`serialize_as_any=True` so subclass fields like `layout_options.model_spec` survive), per-stage models summary, environment (python, platform, machine, system, tracked package versions), output_summary, errors. Hostname intentionally **not** captured. |

### Path deviations from the TODO

Two paths were quietly corrected during implementation:

- `docling/models/engine_output.py` → **`docling/engines/schemas.py`**
- `docling/utils/validation.py` → **`docling/engines/validation.py`**

Reason: `docling/models/` holds upstream's ML-model wrappers (layout, OCR, VLM); putting Pydantic data schemas there is a naming collision waiting to happen. Same logic for `docling/utils/`. Keeping all Amir Engine code under `docling/engines/` makes future upstream merges easier.

## Per-PDF output layout (Phase 1+2+3 deliverable)

```
out/<pdf-stem>/
├── <pdf-stem>.md            # primary markdown (noise stripped; ![](images/picture_NNN.png) refs)
├── <pdf-stem>.embedded.md   # standalone — base64-inlined images (when embed_images=True, default)
├── document.json            # full DoclingDocument (round-trippable)
├── nodes.jsonl              # one JSON object per node from iterate_items()
├── chunks.jsonl             # HybridChunker output: index, text, token_count, headings, page_nos, self_refs
├── tables.jsonl             # one TableItem per row: caption_text, markdown, html, flat cells (with spans), dims
├── figures.jsonl            # one PictureItem per row: caption_text, image_path, figure_type (BiomedCLIP), vlm_caption, generic_classifier_label, is_noise/noise_reason
├── run.json                 # env + timing + engine_config + pipeline_options (incl. model_spec) + packages
├── images/
│   ├── page_NNNN.png        # page renders
│   ├── picture_NNN.png      # PictureItem.get_image() crops (ALL pictures kept; noise just tagged)
│   └── table_NNN.png        # TableItem.get_image() crops
└── preview.html             # bbox viewer — summary chips + clickable formatted side panel
```

For the optional full-page-VLM A/B run (``compare_pipelines.run_comparison``):

```
out/<pdf-stem>/
├── standard/                # full PdfEngine bundle as above
├── full_page_vlm/           # same shape, produced via VlmPipeline (default GraniteDocling)
└── comparison.md            # side-by-side stats + first lines of each markdown
```

`PdfEngine(save_artifacts=True)` (default) auto-enables `generate_page_images` + `generate_picture_images`; `filter_noise_pictures=True` (default) auto-enables `do_picture_classification` so journal logos / repeated banners are tagged.

## Next action

Phases 1–3 are done. Pipelines produce a clean, agent-readable bundle per PDF (text via chunks, structured tables, structured figures with optional VLM captions). Phase 4 (LLM context enrichment) was **dropped** by design; downstream consumers can run their own LLM over `chunks.jsonl` + `figures.jsonl` + `tables.jsonl` if they want summaries/topics/metadata.

Open items for future work (not active):
- `vlm_specs.build_picture_description_options` never passes the spec's `prompt`, so every preset runs with the stage default "Describe this image in a few sentences." (confirmed in `run.json`). Fixing it changes caption style — decide before regenerating showcases.
- Figure-type eval sample has no histopathology / plain X-ray / endoscopy / Kaplan–Meier / forest-plot figures; re-measure on a corpus that has them. Combining BiomedCLIP with a Granite-Vision label-only pass would reach 96.9 % if the right one could be picked (oracle) — worth a look if accuracy matters more than a second VLM pass.
- Pull GraniteDocling table-structure and Qwen2.5-VL-3B picture description through a real GPU run end-to-end and pin numbers in `run.json`.
- Conversion weak spots from the 2026-11-02 4-paper batch: a 20-page SSRN-formatted paper came out as 5 text blocks with no headings (text itself complete, 99.8 % of PDF words); text printed inside figures leaks into body text of the markdown. Not investigated.
- The noise veto's evidence is one paper's echo frames; re-check `IMAGING_FIGURE_TYPES` / 0.9 when a corpus with small CT / X-ray / histology thumbnails turns up.
- `showcase/` and older sample bundles predate `<stem>.html`; `rebuild_document_html(pdf_dir)` backfills it without reconverting (adds files to the repo for `showcase/`).
- Phase 5 (FastAPI + CLI exposing `PdfEngine.convert` and `run_comparison`) when batch-processing demand appears.
- Tokenizer/model swap to Qwen3-Embedding-4B + Qwen3-VL (see "Future considerations" in AMIR_TODO).

## Log

| Date | Phase | Change |
|---|---|---|
| 2026-05-21 | — | `.claude/` workspace initialised. |
| 2026-05-21 | 1 | `.claude/` re-scaffolded via `claude-folder-handler` (packs: data-science, llm-app, llm-extraction, security-hardening, visualization). Amir files restored on top. |
| 2026-05-21 | 1 | Foundation code landed: `docling/engines/{__init__,schemas,validation,pdf_engine}.py` + `tests/test_engines/test_pdf_engine.py`. |
| 2026-05-21 | 1 | HTML bbox visualiser landed: `docling/engines/visualizer.py`, wired into `PdfEngine` via `make_html_preview=True`. 7/7 tests pass. Smoke-tested on `samples/test-pdf-ai-manuscript.pdf`. |
| 2026-05-21 | 1 | Dev env: `--all-extras` unusable on aarch64 (no `onnxruntime-gpu` wheel). Working install: `uv sync --frozen --group dev --no-group docs --no-group examples --extra standard`. See [REPO_CONTEXT.md](REPO_CONTEXT.md) for full notes. |
| 2026-05-21 | 1 | Per-PDF subfolder layout + `embed_images=True` standalone markdown landed in `PdfEngine`. |
| 2026-05-21 | 1 | Reading-order column-flip bug observed on mixed-layout pages — documented at [.claude/issues-with-docling/reading-order-mixed-layout-page.md](issues-with-docling/reading-order-mixed-layout-page.md), Phase 1 ships as-is. |
| 2026-05-21 | 1 | **Persistent data nodes** landed: `docling/engines/artifacts.py` (`document.json` + `nodes.jsonl` + figure/table crops). `PdfEngine(save_artifacts=True)` is the default. |
| 2026-05-21 | 1 | **Clickable preview** landed: viewer now draws one bbox per `DocItem`, click opens side panel with full node JSON. Esc clears selection. |
| 2026-05-21 | 1 | **Run snapshot** landed: `docling/engines/run_snapshot.py` writes `run.json` per PDF (env, timing, models, full pipeline_options). `tach.toml` gained a `docling.engines` module entry. 9/9 tests green; `make validate` clean. |
| 2026-05-21 | 1 | **Linked + standalone markdown** landed: primary `.md` rewrites `<!-- image -->` placeholders to `![](images/picture_NNN.png)` refs (matches `nodes.jsonl.image_path`); `embed_images=True` (now default) additionally writes `<stem>.embedded.md` with base64 images. Manuscript smoke: primary 55 KB / 0 placeholders, embedded 697 KB / 7 base64 figures. |
| 2026-05-21 | 2 | **HybridChunker integration** landed: `docling/engines/chunker.py` writes `chunks.jsonl` (50 chunks on manuscript). Tokenizer = `sentence-transformers/all-MiniLM-L6-v2`, max_tokens=512. Auto-on with `save_artifacts=True`. |
| 2026-05-21 | 2 | **Structured outputs** landed: `tables.jsonl` (caption_text + markdown + html + flat cells with row/col offsets/spans) and `figures.jsonl` (caption_text + image_path + vlm_caption + classifier_label) via `docling/engines/structured_outputs.py`. |
| 2026-05-21 | 3 | **Granite-Vision tables** flag landed (opt-in; downloads a 2B model on first use). |
| 2026-05-21 | 3 | **Picture description VLM** wired: `PdfEngine(picture_description="qwen25_vl_3b", picture_description_engine="vllm")` builds `PictureDescriptionVlmEngineOptions` + `VllmVlmEngineOptions` pointing at `Qwen/Qwen2.5-VL-3B-Instruct`. Captions land in `figures.jsonl[*].vlm_caption`. Custom Qwen spec lives in `docling/engines/vlm_specs.py` (Docling's bundled Qwen preset is MLX-only). |
| 2026-05-21 | 3 | **Picture noise filter** landed (default-on): `docling/engines/picture_filter.py` classifies logos / watermarks / repeated banners via classifier labels + bbox-repeat heuristic. Auto-enables `do_picture_classification`. On the manuscript, correctly tagged the *European Journal of Radiology* running logo as `classifier:logo` (1 of 7 pictures). Noise pictures are stripped from both `<stem>.md` and `<stem>.embedded.md` (replaced with `<!-- noise picture: reason -->`). |
| 2026-05-21 | 3 | **Full-page VLM comparison runner** landed: `docling/engines/compare_pipelines.py::run_comparison()` writes `out/<stem>/{standard,full_page_vlm,comparison.md}`. Default uses `GRANITEDOCLING_TRANSFORMERS` (DocTags → comparable bundles). |
| 2026-05-21 | 3 | **HTML preview extended**: summary chips (pages / figures / tables / chunks / noise), per-kind formatted side panel (picture: caption + VLM description + classifier + thumbnail; table: dims + rendered HTML; text: body text), noise pictures rendered dashed gray with badge. Raw JSON still available via collapsible toggle. |
| 2026-08-07 | — | `RUN.md` (repo root) + `docs/hand-off-notes/hand-off-note-for-citation.md` landed: batch-run guide (`amir-batch` has no skip-already-done logic — documented the manual workaround) and a spec for using the per-PDF bundle as extraction-citation evidence. |
| 2026-08-07 | 1 | **Citation deep-link** landed in `docling/engines/visualizer.py`: `preview.html?ref=self_ref[,self_ref...]` scrolls to and persistently highlights the matching bbox(es) and opens the side panel; the side panel now also shows a ready-made citation link for whatever node is selected. Page-only anchors (`#page-N`) already worked. |
| 2026-08-07 | 3 | **Fixed: Granite-Vision-4.1-4b defaults were broken since the "Granite-Vision defaults" commit** — every PDF failed with `EXCEPTION` at pipeline-init under default flags (`--granite-vision-tables` on, `--picture-description granite_vision_4b`, both on by default). Root cause: `ibm-granite/granite-vision-4.1-4b`'s connector is a Blip2-style Q-Former, which doesn't support `sdpa` attention (huggingface/transformers#28005); the picture-description path also loaded the model via plain `AutoModel` (no `.generate()`) instead of `AutoModelForImageTextToText`. Fixed in `docling/models/inference_engines/vlm/transformers_engine.py` (additive `attn_implementation` extra_config override, doesn't affect other models), `docling/engines/vlm_specs.py` (sets `eager` attention + `AUTOMODEL_IMAGETEXTTOTEXT` for this spec), and `docling/models/stages/table_structure/table_structure_model_granite_vision.py` (single-model file, `sdpa`→`eager` fallback directly). Verified end-to-end with default flags on real PDFs: picture description produces populated `vlm_caption`s, table structure produces 5 well-formed tables on `test-pdf-ai-manuscript.pdf`. `AMIR_TODO.md`'s "pull Granite-Vision through a real GPU run end-to-end" open item is now done. |
| 2026-09-29 | — | Synced with upstream Docling **v2.131.0** (474 commits). Upstream now handles the Granite-Vision-4.1 Q-Former attention itself, so the 2026-08-07 patches to `transformers_engine.py` / `table_structure_model_granite_vision.py` were dropped in favour of upstream; `vlm_specs.py` mirrors upstream's pinned 4.1-4B spec. Added `preview.embedded.html`, cross-platform fixes (UTF-8 I/O, Windows install notes), and a 3-config `showcase/`. **Open:** Granite-Vision tables on v2.131.0 mis-split table 3 of the showcase paper (14×10 vs true 8×11; TableFormer gets it right); not caused by attention impl. |
| 2026-10-01 | — | Clean GPU benchmark (GB10, v2.131.0, GPU otherwise idle) on the 68-page showcase paper: default 706.8 s / peak 19 225 MiB; `figures-vlm` 135.5 s / 11 761 MiB; `fast` 56.1 s / 1 565 MiB. READMEs updated (default now ≥ 24 GB GPU). |
| 2026-10-01 | 3 | **Fixed: figure "classifier label" was meaningless for medical papers.** Docling's `DocumentFigureClassifier-v2.5` has 26 generic classes and no medical ones (ECG → `line_chart`, angiogram → `photograph`); it scored 16.5 % on a 97-figure hand-labelled sample (cardiology case reports + medical-AI papers). Benchmarked replacements on that sample: **BiomedCLIP zero-shot 83.5 % top-1 / 87.6 % incl. valid alternates, 14 ms/fig, 0.8 GB**; Granite-Vision-4.1-4B type+description prompt 79.4 / 84.5 %, 1.1 s/fig, 11.3 GB; Granite-Vision label-only prompt 80.4 / 93.8 %, 0.22 s/fig but needs a second VLM pass. Chose BiomedCLIP in every config: `docling/engines/figure_typing.py`, `PdfEngine(figure_types=True)` / `--figure-types` (default on) → `figures.jsonl[*].figure_type` (+ `_confidence`, `_model`) and `PictureItem.meta.amir__figure_type` in `document.json`. Generic label renamed `generic_classifier_label` (noise filter only); `icon` + `bar_code` added to noise classes (CC-BY / ORCID / "Check for updates" badges were leaking into markdown). Preview "noise" chip counted all pictures — fixed. New dependency: `--extra models-vlm-inline` (open-clip-torch). |
| 2026-10-01 | 3 | **Noise filter area guard.** Making `icon` a noise class hid a page-wide 3-D CT rendering (`39397583`, 8.2 % of the page) that the generic classifier called `icon`. Classifier noise labels now only count below 5 % of the page area (`DEFAULT_MAX_CLASSIFIER_NOISE_AREA`); all 43 true logos/badges/QR codes across 25 papers were ≤ 1.65 %. BiomedCLIP can't be the veto — it calls the Springer logo `ecg` at 1.00. S_20pdfs re-run with the fix: 19/19 SUCCESS, 0 errors. |
| 2026-10-01 | — | Intermittent OpenCV 5.0.0 segfault in RapidOCR on aarch64 kills whole batches — see [issues-with-docling/opencv5-resize-segfault-aarch64.md](issues-with-docling/opencv5-resize-segfault-aarch64.md); workaround: one process per PDF + retry. |
| 2026-10-02 | 2 | **Fixed: model-guessed picture labels leaked into text exports.** docling-core's markdown/chunk serializers append the generic classifier label to every picture ("Line chart" under an ECG in `chunks.jsonl` and `<stem>.md` — the original bug, now inside RAG chunks) and, since figure typing, the repr of the `amir__figure_type` dict. Both are now excluded (`TEXT_EXPORT_META_PARAMS` in `figure_typing.py`, used by `PdfEngine` markdown exports and a custom chunker serializer provider); the type stays structured in `figures.jsonl` / `document.json` / preview. S_20pdfs regenerated: 19/19 SUCCESS, 0 errors, no label text in any markdown/chunks (one OpenCV segfault on `19859766`, retry succeeded). |
| 2026-10-02 | — | **Showcase regenerated** — all three configs from one code version (v2.131.0 + figure typing + label-free text exports), GPU otherwise idle: `fast` 65 s / 1 637 MiB, `figures-vlm` 143 s / 11 761 MiB, `default` 706 s / 19 225 MiB (peaks unchanged by BiomedCLIP). `default/` now shows Granite-Vision's table-3 regression (14×10 vs true 8×11); figure types 13/15 on this chart-heavy paper. |
| 2026-11-02 | 2 | **Standalone `<stem>.html`** (`docling/engines/html_export.py`): Docling's HTML serializer (kept over a custom renderer — it already does merged-cell tables, captions, formula crops, inline images) subclassed to stamp every block and caption with `id` / `data-self-ref` / `data-label` / `data-page` / `data-bbox` (top-left origin), figure type as data attributes, model-generated meta labelled, noise pictures dropped (captions kept, like markdown/chunks), generic classifier label hidden, plus a JSON manifest (`figures`/`tables`/`chunks` rows, `run.json`, `how_to_read`). On `samples/4new_for_aca`: every chunk `self_ref` resolves to an element; 0.2–1.8 MB, ~0.1 s per paper. `rebuild_document_html(pdf_dir)` regenerates from an existing bundle. Repo renamed `am-mini-docling` → `extrct_docling` the same day. |
| 2026-11-02 | — | **Pre-push audit.** Found `.claude/hooks/lib/` had never been committed (upstream `.gitignore` ignores every `[Ll]ib` folder), so 5 of 6 project hooks crashed on import in fresh clones; re-included in `.gitignore`, verified from a `git archive` export (secrets hook blocks, exit 2). Added `showcase/LICENSE`: the paper (arXiv:2409.00084 / npj Digit Med 8, 797) and its conversions are CC BY-NC-ND 4.0, the repo's MIT doesn't cover the folder; the PDF is the authors' Word-exported manuscript. Kept the full paper — an excerpt is no safer (the license allows sharing "in whole or in part") and it has been public since `c6aacb06`. Scan of the outgoing commits: no machine paths, tokens or IPs; only emails are the paper's public author addresses. |
| 2026-11-03 | 2 | **`<stem>.html` made a full ingestion + first release** (tagged `extrct-v1.0.0`, then renamed — see the release row below). On 18 ACA papers the HTML was missing 7 458 of 10 940 `document.json` items: text inside figures (6 892 — Docling's HTML serializer never visits picture children), page headers/footers (489 — `HTMLParams.layers` defaults to body), noise pictures (44, deleted), a table footnote (docling-core skips footnotes "for the floating item", whose HTML serializer then ignores them). Now 0 missing / 0 duplicated: furniture marked `data-content-layer`, noise kept with `data-noise`, figure text in a collapsed `details.extrct-figure-text`, footnotes after the table, numbered list markers (`[12]` references) as text, undecoded formulas get their PDF-text-layer characters. Against the PDFs' own text layer the HTML holds 99.5 % of words (rest: formula spacing, text-layer artefacts, one Granite-Vision table that truncated cells). **Noise veto:** the generic classifier hid 6 echo frames inside a composite figure as `icon`/`logo`; all 68 classifier-hidden pictures in 37 papers were labelled by eye — BiomedCLIP imaging types ≥ 0.9 (ecg / nuclear_medicine excluded: Springer logo ecg 1.00, badge nuclear_medicine 0.93; a QR code was ultrasound 0.85) un-hide exactly the 6 frames and none of 62 badges. **Ligature repair** (`text_repair.py`): docling-parse split "speci fi city" (82 words in 2 papers), rejoined only into words pdfium reads on the page. `run.json` gains `engine` (release, git commit, dirty flag) and torch / open-clip-torch / docling-slim versions. Known: the SSRN paper's text is complete but packed into 5 blocks with no headings (layout model). |
| 2026-11-03 | 3 | **Granite-Vision table generation capped + table PDF-text safety net; release `extrct_docling-v2.131.0-r1`** (briefly tagged `extrct-v1.0.0` / `extrct-v1.0.1`; those tags were deleted when releases were renamed after the Docling base version). The release build hung on `AMIE-Mx Supplementary` (41 boxed prompts captioned "Table SI.x"): 75+ min on one PDF, GPU memory 17 → 57 GB. Cause: `table_structure_model_granite_vision.py` passed the tokenizer's `model_max_length` (unset, ~1e30) as `max_new_tokens`. On 88 converted tables the OTSL output never exceeded 3 × the PDF-text tokens of the crop + 512 (median 1.4 ×, max output 2 328 tokens), so each page now gets max(2048, that); the supplement converts in 16 min, memory flat at 16.5 GB, 99.7 % of its PDF words in the HTML. Granite-Vision also *retypes* cell text from the image: 10 of 88 tables kept < 95 % of the words printed in their box (worst 0.82; on the supplement 0.22, likely a capped runaway). Those tables now keep the box's PDF text (`amir__pdf_text` meta → HTML `details.extrct-table-pdf-text`, `data-cell-text-recall`); PDF-word coverage of the HTML rose 99.44 → 99.65 % (4 papers) and 99.51 → 99.60 % (14). |

## Blockers

_None._

## Open questions

- Cache backend for VLM (Phase 3): in-memory only, or disk-backed? Decide before Phase 3 starts.
- For Phase 4 (LLM metadata) — confirm Anthropic API key is the only LLM credential needed, or also OpenAI / local model fallback?
- GPU-enabled Docker on this box (aarch64 + NVIDIA GB10) is being explored on a separate branch (not `dgx`) — see that branch for outcome/status note. The root `Dockerfile` here stays CPU-only/upstream-only by design.
