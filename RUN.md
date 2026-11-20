# Running `amir-batch`

How to convert PDFs in `samples/` through `PdfEngine` (the Amir Engine), and
what happens to PDFs that were already processed.

## TL;DR — the command you need right now

The working set is `samples/aca-papers/` (18 papers and 5 supplements); its
bundles go to `samples/aca-papers_out/`. Everything older (earlier sample
sets and their outputs) is under `samples/archived/`.

```bash
uv run --no-sync amir-batch samples/aca-papers -o samples/aca-papers_out \
    --supplement "PULSE Supplementary.pdf=Wang_et_al_2026_A_knowledge_enhanced_domain_aware_large_language.pdf"
```

The numbers behind the charts are a step after it, with one of the two recommended step configs
(`configs/figure-to-data/README.md`): `uv run --no-sync amir-figdata step samples/aca-papers_out --config
configs/figure-to-data/recommended-cloud.toml` (Claude Sonnet 5.5 through OpenRouter, five bundles at a
time) or `recommended-local.toml` (Gemma 4 in Ollama); `amir-batch ... --figure-data-config <file>` does
both in one command.

Four supplements are paired with their manuscript by file name
(`AMIE-Mx Supplementary.pdf` ↔ `AMIE-Mx.pdf`); `--supplement` names the fifth,
whose name shares nothing with its manuscript's. Run it from a clean checkout
of the release tag so every `run.json` records the release with
`git_dirty: false`.

**`amir-batch` skips finished bundles by default.** A PDF is skipped when
`<output>/<stem>/run.json` says the conversion completed (`complete: true`,
status SUCCESS or PARTIAL_SUCCESS, no step errors) for the same file
(`source.binary_hash`, else name and size) with the same engine release and
the same options; the row shows `SKIPPED` with the saved `check.json`
summary. Anything else is converted again and the reason printed
(`reconverting <stem>: engine version differs (2.131.0-r3 -> 2.131.0-r4)`,
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


## Which files of the input are processed

From `docling/engines/cli.py` (`_collect_sources`) and
`docling/engines/sources.py`:

- A **directory** argument is scanned **non-recursively** for PDF, Word
  (`.docx`) and ZIP files, the suffix in any case. Subfolders,
  extension-less files and every other kind (a `.csv` index, say) are
  invisible to it.
- A **file** argument is taken when it has one of those three suffixes;
  anything else is skipped with a yellow console warning, not an error.
- A **Word file** is turned into a PDF first, with LibreOffice through
  Docling's own helper (a throwaway profile, macros off, a timeout), and
  then converted like any PDF: its bundle has pages, boxes, the page
  viewer, the checks and figure data. Without LibreOffice the file gets an
  `EXCEPTION` row and the batch exits 1.
- A **ZIP archive** stands for the PDF and Word files inside it. Each
  becomes a bundle named `<archive>__<file>`; the files of
  `12345_supplements.zip` are paired with `12345.pdf` as its supplements.
- What was made or taken out is kept under `<output>/_converted/`, so the
  checks and the figure-to-data step find the PDF again and an unchanged
  source is not converted twice. `run.json` records where a bundle's PDF
  came from under `source.converted_from` (file name, size, hash, the
  archive, the converter).
- The final list is deduplicated and sorted by resolved path: the order is
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
| `--granite-vision-tables / --no-granite-vision-tables` | **on** | On: each table goes to the model that has its text (r7): TableFormer for a table whose box holds PDF text, Granite-Vision VLM (4.1-4b) for a table of contents, an image-only table and a page read by OCR; `tables.jsonl` → `structure_model` names it. Off: plain TableFormer for every table. With it on, a table whose generation hits the token budget or whose grid is degenerate is redone by TableFormer (logged as `structure taken from TableFormer`). |
| `--picture-description` | `granite_vision_4b` | VLM preset for figure captions. Other values: `granite_vision`, `smolvlm`, `pixtral`, `qwen25_vl_3b`, or `off`. |
| `--figure-types / --no-figure-types` | **on** | Types every figure with BiomedCLIP (`ct`, `angiography`, `ecg`, `ultrasound`, `kaplan_meier`, `bar_chart`, ...) → `figures.jsonl[*].figure_type`. Runs in every config, VLM or not; ~0.8 GB GPU, ~15 ms per figure. Needs the `models-vlm-inline` extra (open-clip-torch). |
| `--picture-area-threshold` | `0.03` | Smallest picture (fraction of the page area) that gets a VLM caption. Docling's default of 0.05 left real charts at 4-5 % of the page uncaptioned. |
| `--skip-existing / --no-skip-existing` | **on** | Skip a PDF whose bundle is complete and error-free for the same file (binary hash, else name + size), engine release and options; otherwise reconvert and print why. |
| `--retries` | `1` | Rerun a PDF that many more times when the engine raises, before marking it `EXCEPTION`. |
| `--check-only` | off | Run the bundle self-check on existing bundles (writes `check.json`), no conversion. |
| `--pair-supplements / --no-pair-supplements` | **on** | A PDF named like another of the batch plus `Supplementary` (`supplement`, `supp`, `SI`, `appendix`, an optional number) is recorded as that manuscript's supplement: `run.json` of both gets `related` (role, file name, size, hash, bundle folder), the supplement `document_role: "supplement"`, and every element of its HTML `data-document-role`. |
| `--supplement SUPP.pdf=MANUSCRIPT.pdf` | none | Pair two PDFs of the batch whose names do not say so (repeatable); recorded with `pairing: "explicit"`. |
| `--figure-data` | `off` | Adds the figure-to-data step on the finished bundles: `ollama` (a local model, nothing leaves the machine), `cloud` (a cloud model's API endpoint: a short call that lists the charts, then one call per figure) or `agent` (one agent session per figure). See [Figure-to-data](#figure-to-data-the-numbers-behind-the-charts). |
| `--figure-data-model` | the backend's own | `gemma4:26b-a4b-it-qat` on Ollama, `anthropic/claude-sonnet-5.5` on the cloud endpoint (OpenRouter's name), `claude-sonnet-5-5` for the agent. |
| `--figure-data-backend` | the method's own | Where the model runs. `cloud`: `openai-compatible` (an API endpoint). `agent`: `claude-cli` (the Claude Code CLI with its own login) or `ollama` (the agent on a local model). |
| `--figure-data-base-url` | `https://openrouter.ai/api/v1` | `cloud`: the chat-completions endpoint, any that speaks the OpenAI format (a provider, a gateway, a local Ollama at `http://127.0.0.1:11434/v1`). |
| `--figure-data-key-env` | `OPENROUTER_API_KEY` | `cloud`: the variable that holds the endpoint's API key, read from the environment, else from `.env`. |
| `--figure-data-ollama-url` | `http://127.0.0.1:11434` | `ollama`, and `agent` on the `ollama` backend: where Ollama listens. |
| `--figure-data-when` | `end` | `end`: read the figures once the whole batch is converted (the conversion models are released first, the reading model loads once). `each`: after each PDF. |

## Figure-to-data: the numbers behind the charts

An optional step after the conversion (`default-plusFigData` is the
suggested default plus `--figure-data ollama`). It never changes a
conversion's status, and it can be run on its own at any later time:

```bash
uv run amir-batch samples/ -o samples/out --figure-data ollama     # convert, then read the charts
uv run amir-figdata step samples/out --pdf-dir samples --method agent   # on an existing output folder
uv run amir-figdata prepare samples/out --pdf-dir samples         # or phase by phase
uv run amir-figdata read samples/out --method cloud
uv run amir-figdata embed samples/out
```

Three phases: **prepare** (no model: each chart candidate is captured from
the PDF at high resolution with its printed text), **read** (one of three
methods), **embed** (the reading is written at the figure in the markdown,
the HTML, `chunks.jsonl`, `figures.jsonl`, `document.json`, with a note that
a model read it; the page viewer is rebuilt, so a figure with a reading
carries a `data` tag and shows note, table and a link in its side panel;
`run.json` gets a `figure_to_data` block, `check.json` the counts, and the
batch summary's `check` column shows them as `charts shown/read/candidates`).

| Method | The figure goes to | Needs | Use it when |
|---|---|---|---|
| `ollama` | nowhere | Ollama, a GPU with 16 GB for the default model | nothing may leave the machine; expect about half the charts usable and review them |
| `cloud` | the endpoint: OpenRouter and the model host it picks | an API key in `.env` (below) | the papers may be sent out and you have an API key: with Sonnet 5.5 all ten bench charts usable and every value returned, in the least time and at the least cost |
| `agent` | the model's provider (nowhere with `--figure-data-backend ollama`) | Claude Code CLI, logged in | the papers may be sent out and you have Claude Code but no API key: all ten bench charts usable; each reading is checked and corrected in the loop |

Measured on 15 figures: [docs/mini-bench/chart-to-data/round-3](docs/mini-bench/chart-to-data/round-3/README.md).
On one whole paper, command by command (time, cost, what each leaves in
the bundle): [round-4](docs/mini-bench/chart-to-data/round-4/README.md).
There the conversion took 11 to 12 minutes and the step 6 minutes
(`cloud`, Sonnet 5.5), 14 (`agent`), 27 (`ollama`) or 30 (`cloud`,
Gemini 3.8 Flash) for 12 chart candidates, some of them grids of up to
eleven charts.

**The cloud method's API key.** Put it in a `.env` file in the folder you
run from (or any folder above it), or export it; `.env` is git-ignored:

```
OPENROUTER_API_KEY=sk-or-...
```

The key is read at the first figure, sent only as the request's
`Authorization` header, and never written into a run record. Without it
the figures are recorded as failed with the reason, and nothing is sent.
For another model on OpenRouter: `--figure-data-model
google/gemini-3.8-flash` (measured: nine of ten bench charts usable, no
cheaper and four and a half times slower than Sonnet 5.5). For another
endpoint: `--figure-data-base-url <url> --figure-data-key-env <VARIABLE>
--figure-data-model <its model name>`. An endpoint on this machine (a
local Ollama's `/v1`) needs no key. The call asks the model to think
(`reasoning_effort` medium since r6; `amir-figdata read --effort high`
costs half as much again and returns the unlabelled values of dense
charts that medium leaves out) and allows 64,000 output tokens; an
endpoint that rejects the reply schema or the reasoning setting is asked
again without it.

Each paper gets a `figure-to-data/` folder: `prepare.json`, one folder per
figure (`figure.png`, `figure.txt`, `evidence.json`, then
`figure-to-data.md` and `figure-to-data.json` once read) and `runs/` with
the config of every run. A bundle that already had the step with the same
method and model is skipped, so an interrupted batch continues where it
stopped. Values under the confidence threshold (0.7) stay out of the
exports; the figure then carries a pointer to its `figure-to-data.md`.
Design and reasons: `.claude/reference/figure-data/STANDALONE-STEP.md`.

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
per page, printed text outside every item box, export fidelity, ligature
splits, degenerate tables, empty chunks, structure sanity) and the per-PDF
output path. A conversion whose Docling
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
structure.json         # outline with heading levels; per element: role, section, number, caption links; relabelled items
run.json               # env, timing, full engine_config/pipeline_options, errors, complete flag (written last),
                       # quality (label counts, warnings), structure_version, document_role, related
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
`figures` / `tables` / `chunks` rows, the outline and `run.json` (its
`how_to_read` field explains the format).

Each block also says where it sits: the title is `<h1>`, section headers are
`<h2>`..`<h6>` with `data-level`, every block has `data-role` (`abstract`,
`body`, `reference`, `table-caption`, ...) and `data-section-ref` (the
section header it is under), a table or figure has `data-number`
(`Table 2`) and `data-caption-ref`, its caption `data-for`. The rules and
attribute list are in `.claude/reference/structure/RULES.md`; the same
records are in `structure.json`. `run.json` → `quality.warnings` uses stable
codes (`few_text_blocks`, `no_body_text`, `no_headings`, ...); a blocking
one turns the status into `PARTIAL_SUCCESS`.

The footnotes of a table or a figure follow it in all three text exports
since r7, one paragraph each and in the same order: in `<stem>.html`
(`div.extrct-table-notes`), in `<stem>.md` and in the chunk that holds the
table or figure. Before r7 the markdown and the chunks had none: on 65
trial papers and supplements that was 350 footnotes (analysis populations,
missing data, definitions).

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

**A PDF whose text does not say what the page prints** (since r6). Some
PDFs embed a font without a Unicode map: the page prints "Sample size" and
the PDF's text reads `6DPSOH VL]H`. The conversion reads such text through
its fonts. Where the codes are glyph numbers in the standard order it
decodes them exactly, and the bundle holds the printed text. Where they
cannot be decoded and make up 30 % or more of a page, the page is read by
OCR. `run.json` → `quality.text_layer` names the pages (`glyph_order_pages`,
`unreadable_pages`, `partly_unreadable_pages`) with the warnings
`text_layer_decoded`, `text_layer_read_by_ocr` and
`text_layer_partly_unreadable`; `check.json` → `text_layer` lists the pages
read by OCR and the partly unreadable ones as issues, because nothing in
the PDF can confirm their text. A bundle converted before r6 from such a
PDF holds unreadable text with status `SUCCESS`: convert it again, alone,
with `amir-batch <folder> -o <out> --only <file.pdf>` (repeatable). The
whole folder is still read, so a supplement keeps its manuscript, and the
bundles of the other PDFs stay as they are, whatever release wrote them.

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
