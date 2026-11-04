# Running `amir-batch`

How to convert PDFs in `samples/` through `PdfEngine` (the Amir Engine), and
what happens to PDFs that were already processed.

## TL;DR — the command you need right now

Six new PDFs landed in `samples/` today (`10732855.pdf`, `16107129.pdf`,
`19912435.pdf`, `24890555.pdf`, `31778462.pdf`, `39748932.pdf`) and
`samples/out/` already has results for the three older ones
(`test-case-report1`, `test-case-report2`, `test-pdf-ai-manuscript`).

**Since `-r3`, `amir-batch` skips finished bundles by default.** A PDF is
skipped when `samples/out/<stem>/run.json` says the conversion completed
(`complete: true`, status SUCCESS or PARTIAL_SUCCESS, no step errors) for the
same file (`source.binary_hash`, else name and size) with the same engine
release and the same options; the row shows `SKIPPED` with the saved
`check.json` summary. Anything else is converted again and the reason printed
(`reconverting <stem>: engine version differs (2.131.0-r2 -> 2.131.0-r3)`,
`options differ (make_html_preview)`, `previous run had errors`, ...). So a
new release reconverts every older bundle it is pointed at, on purpose, and
the simple command is also the right one:

```bash
uv run amir-batch samples/ -o samples/out              # converts only what is new
uv run amir-batch samples/ -o samples/out --no-skip-existing   # redo everything
uv run amir-batch samples/ -o samples/out --check-only # re-check existing bundles, no conversion
```

Bundles written before `-r3` have no `complete` field, so they are converted
once more and then skipped from then on.

A PDF whose engine raised is retried once (`--retries N` to change). Ctrl-C
stops the batch, prints the rows done so far and exits 130; the interrupted
bundle has no `complete: true`, so the next run redoes it.


## How `_collect_pdfs` decides what to process

From `docling/engines/cli.py`:

- A **directory** argument is scanned **non-recursively** for files whose
  suffix is `.pdf` in any case — subfolders and extension-less files are
  invisible to it.
- A **file** argument is included only if `path.suffix.lower() == ".pdf"`.
- Anything else is skipped with a yellow console warning, not an error.
- The final list is deduplicated and sorted by resolved path — order is
  deterministic, not input order.
- Output folder names are the sanitized stem; two PDFs of a batch that map to
  the same name (`Smith 2020.pdf` and `Smith_2020.pdf`, or `main.pdf` in two
  input folders) get `_2`, `_3`, ... suffixes, logged at run time.

## Full command reference

```bash
uv run amir-batch <pdf-or-dir> [<pdf-or-dir> ...] [OPTIONS]
```

| Option | Default | What it does |
|---|---|---|
| `-o, --output-dir` | `samples/out` | Root output directory; one subfolder per PDF stem. |
| `-c, --compare / --no-compare` | off | Runs standard vs. full-page-VLM A/B per PDF (writes `standard/`, `full_page_vlm/`, `comparison.md` instead of the normal bundle). |
| `--preview / --no-preview` | on | Renders the clickable HTML bbox viewer (`preview.html`). |
| `--vlm-preset` | `granite_docling` | Full-page VLM preset, only used with `--compare`. |
| `--images-scale` | `1.5` | Scale factor for rendered page/crop images (rendering only — does not affect layout or `self_ref` assignment). |
| `--granite-vision-tables / --no-granite-vision-tables` | **on** | Table structure via Granite-Vision VLM (4.1-4b) vs. plain TableFormer. |
| `--picture-description` | `granite_vision_4b` | VLM preset for figure captions. Other values: `granite_vision`, `smolvlm`, `pixtral`, `qwen25_vl_3b`, or `off`. |
| `--figure-types / --no-figure-types` | **on** | Types every figure with BiomedCLIP (`ct`, `angiography`, `ecg`, `ultrasound`, `kaplan_meier`, `bar_chart`, ...) → `figures.jsonl[*].figure_type`. Runs in every config, VLM or not; ~0.8 GB GPU, ~15 ms per figure. Needs the `models-vlm-inline` extra (open-clip-torch). |
| `--picture-area-threshold` | `0.03` | Smallest picture (fraction of the page area) that gets a VLM caption. Docling's default of 0.05 left real charts at 4-5 % of the page uncaptioned. |
| `--skip-existing / --no-skip-existing` | **on** | Skip a PDF whose bundle is complete and error-free for the same file (binary hash, else name + size), engine release and options; otherwise reconvert and print why. |
| `--retries` | `1` | Rerun a PDF that many more times when the engine raises, before marking it `EXCEPTION`. |
| `--check-only` | off | Run the bundle self-check on existing bundles (writes `check.json`), no conversion. |

Defaults are VLM-heavy (`--granite-vision-tables` on, `--picture-description
granite_vision_4b`) — expect first-run model downloads and a noticeably
longer per-PDF time than a bare-bones run. If you're just checking that a new
PDF parses, add `--picture-description off --no-granite-vision-tables` for a
fast pass.

**These defaults were broken until 2026-08-07** — both flags load
`ibm-granite/granite-vision-4.1-4b`, whose connector is a Blip2-style
Q-Former that the installed `transformers` doesn't support running under
`sdpa` attention (huggingface/transformers#28005), and the picture-description
path was additionally loading the model via a plain `AutoModel` that has no
`.generate()`. Every PDF failed with `EXCEPTION` at pipeline-init time. Fixed
in `docling/models/inference_engines/vlm/transformers_engine.py`,
`docling/models/stages/table_structure/table_structure_model_granite_vision.py`,
and `docling/engines/vlm_specs.py` — verified end-to-end on a real PDF with
default flags: `SUCCESS`, non-empty `figures.jsonl[*].vlm_caption`, table
structure model loads and runs. See `.claude/AMIR_STAGE.md` log for the entry.

The terminal report (rich table) shows one row per PDF: status, duration,
page count, figures (with noise count), tables, chunks, errors, the bundle
self-check summary (`check.json`: HTML item coverage, PDF text-layer recall
per page, export fidelity, ligature splits, degenerate tables, empty chunks,
structure sanity) and the per-PDF output path. A conversion whose Docling
status is SUCCESS but where an export step failed shows `SUCCESS*` with the
failed components in the errs column. Exit code is `1` if any row ends
`FAILURE`, `PARTIAL_SUCCESS`, `EXCEPTION`, `SUCCESS*`, `MISSING` or
`INCOMPLETE` (red status), else `3` if only bundle checks found issues
(yellow check cell; ordinary papers often have a few, e.g. a degenerate
table), else `0` — so `amir-batch … && next` stops only on real failures.
`--check-only` follows the same rule.

## What lands in `samples/out/<pdf-stem>/`

```
<stem>.md              # primary markdown, noise pictures stripped
<stem>.embedded.md     # standalone markdown, base64-inlined images
<stem>.html            # standalone manuscript HTML (images inlined), see below
document.json          # full DoclingDocument (round-trippable)
nodes.jsonl            # one row per DocItem (iterate_items() order)
chunks.jsonl           # HybridChunker output: text, headings, page_nos, self_refs
tables.jsonl           # one row per table: caption, markdown, html, cells
figures.jsonl          # one row per picture: caption, image_path, figure_type, vlm_caption, is_noise
run.json               # env, timing, full engine_config/pipeline_options, errors, complete flag (written last)
check.json             # bundle self-check: coverage, text-layer recall, fidelity, tables, chunks, issues
images/                # page renders + picture/table crops
preview.html           # bbox viewer — needs images/ alongside it, see below
preview.embedded.html  # same viewer, images inlined — a single shareable file
```

`<stem>.html` is the one-file version of the manuscript for humans *and* agents:
Docling's HTML export (headings, lists, tables with merged cells, captions,
figures inline) where every block carries `id`, `data-self-ref`,
`data-label`, `data-page` and `data-bbox` (PDF points, top-left origin),
figures add `data-figure-type`, and
`<script id="extrct-manifest" type="application/json">` embeds the
`figures` / `tables` / `chunks` rows and `run.json` (its `how_to_read` field
explains the format).

Unlike the markdown and chunks, it leaves out nothing Docling extracted —
every `document.json` item is one tagged element — and marks what isn't
running text instead of dropping it: page headers/footers
(`data-content-layer="furniture"`: journal line, printed page numbers),
logos and badges (`data-noise`, dimmed), text printed inside a figure (a
collapsed "Text inside this figure" block in the figure), table footnotes,
reference / step numbers (`span.extrct-marker`, e.g. `[12]`), for a
formula Docling didn't decode its characters from the PDF text layer, and
for a table whose cells (retyped by the Granite-Vision table model) miss
words printed in its box, that box's PDF text (`data-cell-text-recall`). On
the 18 ACA papers it holds 99.5 % of the words in the PDFs' own text layer;
the rest are mostly formula spacing and text-layer artefacts. To (re)build it
for an existing bundle without reconverting:

```bash
uv run --frozen python -c "from pathlib import Path; from docling.engines import rebuild_document_html as r; [r(p.parent) for p in Path('samples/out').glob('*/document.json')]"
```

`preview.html` is **not standalone** (use `preview.embedded.html` for that) — it references `images/page_NNNN.png`
etc. by relative path. Sharing just the `.html` file renders a blank page;
share the whole `samples/out/<stem>/` folder (or zip it). See
[docs/hand-off-notes/hand-off-note-for-citation.md](docs/hand-off-notes/hand-off-note-for-citation.md)
for what to hand to another agent/student and how it's used for citing
extraction sources.

## After running

```bash
make validate   # mutating hooks on the changeset
make check       # read-only checks
uv run pytest tests/test_engines/   # targeted tests for this engine
```
