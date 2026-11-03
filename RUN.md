# Running `amir-batch`

How to convert PDFs in `samples/` through `PdfEngine` (the Amir Engine), and
what happens to PDFs that were already processed.

## TL;DR — the command you need right now

Six new PDFs landed in `samples/` today (`10732855.pdf`, `16107129.pdf`,
`19912435.pdf`, `24890555.pdf`, `31778462.pdf`, `39748932.pdf`) and
`samples/out/` already has results for the three older ones
(`test-case-report1`, `test-case-report2`, `test-pdf-ai-manuscript`).

**`amir-batch` has no "already done, skipping" logic.** Point it at a
directory and it reprocesses *every* `*.pdf` it finds, unconditionally,
overwriting the matching folder under `samples/out/<stem>/` even if that
folder already exists and is unchanged. There's no cache, hash check, or
`--skip-existing` flag.

So there are two honest ways to run it today:

**Option A — reprocess everything** (simplest, but re-runs the 3 already-done
PDFs too; each is a full VLM pass, budget the time accordingly):

```bash
uv run amir-batch samples/ -o samples/out
```

**Option B — only the new PDFs** (skip-equivalent: name the new files
explicitly so the 3 finished folders are left untouched):

```bash
uv run amir-batch \
  samples/10732855.pdf \
  samples/16107129.pdf \
  samples/19912435.pdf \
  samples/24890555.pdf \
  samples/31778462.pdf \
  samples/39748932.pdf \
  -o samples/out
```

Option B is what "skip the ones already done" actually means in practice —
there is no flag that does it for you, so scope the input list yourself.


## How `_collect_pdfs` decides what to process

From `docling/engines/cli.py`:

- A **directory** argument is scanned **non-recursively** for `*.pdf`
  (case-sensitive glob, but the file-argument path also lower-cases the
  suffix check) — subfolders and extension-less files are invisible to it.
- A **file** argument is included only if `path.suffix.lower() == ".pdf"`.
- Anything else is skipped with a yellow console warning, not an error.
- The final list is deduplicated and sorted by resolved path — order is
  deterministic, not input order.

There is no read of `samples/out/` before running, so it cannot know a PDF
was already converted. If you want that behavior, the fix is choosing which
paths to pass in (Option B above), not a CLI flag — none exists yet.

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
page count, figures (with noise count), tables, chunks, errors, and the
per-PDF output path. Exit code is `1` if any PDF ends `FAILURE` or
`EXCEPTION`, else `0`.

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
run.json               # env, timing, full engine_config/pipeline_options
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
