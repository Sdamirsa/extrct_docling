# Hand-off note: using the PDF→HTML bundle for extraction citations

For the student's extraction agent (case reports → variables → database) and
whoever operates it. Read this before wiring up "explainability" (linking an
extracted variable to the location it came from).

## What this pipeline does, in one line

Each PDF is converted once into a per-document bundle: structured JSON
(`chunks.jsonl`, `tables.jsonl`, `figures.jsonl`, `nodes.jsonl`,
`document.json`) for machines, plus a clickable HTML bbox viewer
(`preview.html`) for humans to audit the same data against the original page
images. Both sides address the same underlying nodes by the same ID
(`self_ref`), which is what makes citation possible.

## What to share — the whole per-document folder, not the `.html` file alone

Share `samples/out/<pdf-stem>/` as a unit (zip it if needed). `preview.html`
references `images/page_NNNN.png` and `images/{picture,table}_NNN.png` by
relative path — copied out on its own it renders a blank page. Verified: copying
just `preview.html` to an empty directory and opening it shows no page images.

Inside that folder:

| File | Who reads it | Use |
|---|---|---|
| `chunks.jsonl` | agent | narrative-text source for most extracted variables |
| `tables.jsonl` | agent | table-cell-derived variables |
| `figures.jsonl` | agent | figure/caption-derived variables |
| `nodes.jsonl`, `document.json` | agent (rarely) | full node detail if a chunk/table/figure row isn't enough |
| `preview.html` + `images/` | human | visual audit — click or deep-link to see the page + highlighted box behind any extraction |
| `run.json` | either | which engine config produced this bundle (see "Citations must survive reprocessing" below) |

## The addressable unit: `self_ref`

Every node in the converted document — a paragraph, a table, a picture — has
a stable-within-this-run ID like `#/texts/12`, `#/tables/0`, `#/pictures/2`.
This is the same ID in all four places:

- `chunks.jsonl[*].self_refs` (a chunk can cover several nodes) and
  `chunks.jsonl[*].page_nos`
- `tables.jsonl[*].self_ref` (+ `prov[*].page_no` / `.bbox`)
- `figures.jsonl[*].self_ref` (+ `prov[*].page_no` / `.bbox`)
- `preview.html`'s bounding-box overlays, each with `data-self-ref="..."`

So: extract a variable from a chunk/table/figure row → note its `self_ref`
(or refs, plural — see below) → that's your citation.

## How to point a human at the evidence

`preview.html` now supports a `?ref=` query parameter (added for this
hand-off; verified against a real converted PDF — see "What was verified"
below):

```
preview.html?ref=%23%2Ftexts%2F12
```

(`#/texts/12`, URL-encoded — `#` becomes `%23`, `/` becomes `%2F`; most
languages' URL-encoding helpers do this for you, e.g. Python
`urllib.parse.quote("#/texts/12")`.)

Opening that link:

- scrolls to the first matching bounding box,
- gives it a persistent red highlight (distinct from the blue hover/click
  state, and from the noise/dashed styling),
- opens the side panel with that node's full metadata.

**Multiple locations for one extraction** (e.g. a diagnosis stated in the
narrative and repeated in a table): comma-separate the refs — every match
gets highlighted, the first one gets scrolled-to and opens the panel:

```
preview.html?ref=%23%2Ftexts%2F12,%23%2Ftables%2F0
```

**Page-only citation** (no specific node, just "see page 3") already worked
before this change and needs no query param — page sections carry
`id="page-N"`:

```
preview.html#page-3
```

**Getting a link back out of the viewer**: click any bounding box; the side
panel's "Citation link" field shows the ready-made `?ref=` URL for that node
(plain text, select-all-on-click — no clipboard API dependency, so it also
works opened from `file://`).

## Citations must survive reprocessing — don't store a bare `self_ref`

`self_ref` is a **positional index** into this run's DoclingDocument (the
Nth text node, the Nth table, ...). Verified empirically for one sample PDF:
re-running the engine with `--granite-vision-tables` on vs. off produced an
**identical, same-order `self_ref` set** — table-structure and
picture-description models only annotate existing nodes, they don't
add/remove/reorder them, so today's CLI flags don't shift indices.

That is not a guarantee for every future change. A docling library upgrade,
a layout/reading-order model change, or a different noise-filter threshold
could shift node boundaries and silently repoint an old `self_ref` at the
wrong text. There's no error when that happens — the ref still resolves to
*something*, just not the same thing the citation was made against.

So store the citation as a small tuple, not a bare string:

```json
{
  "doc_id": "24890555",
  "self_ref": ["#/texts/12"],
  "page_no": [1],
  "verbatim_snippet": "Spontaneous coronary artery dissection",
  "source_file": "chunks.jsonl",
  "engine_run_started_at": "2026-08-05T18:32:07+00:00"
}
```

- `self_ref` + `page_no` — the fast path; what `?ref=` uses.
- `verbatim_snippet` — short excerpt (from the chunk/cell/caption text) as a
  fallback if `self_ref` no longer resolves cleanly after a reprocess; also
  what a human uses to sanity-check the highlighted box is the right one.
- `source_file` — which of `chunks.jsonl` / `tables.jsonl` / `figures.jsonl`
  the extraction came from (the extraction path differs per file, see next
  section).
- `engine_run_started_at` — from that document's `run.json` →
  `timing.started_at`; ties the citation to the exact engine config that
  produced it, so a future audit knows whether a `self_ref` mismatch is
  expected (bundle was regenerated) or a real bug.

## Cover all three source routes, not just narrative text

`chunks.jsonl` only carries text-bearing nodes (`HybridChunker`'s
`doc_items`) — pictures generally have none. A variable read off a table
cell or a figure caption/VLM description won't have a matching chunk; it
resolves through `tables.jsonl` / `figures.jsonl` instead (both carry
`self_ref`, `prov[*].page_no`, `prov[*].bbox`, `caption_text`, and for
figures also `vlm_caption`). If the extraction agent only wires up citations
against `chunks.jsonl`, every table- and figure-derived variable will have no
citation path — cover all three.

## What was verified for this note

- `preview.html` copied alone (without `images/`) renders with no page
  images — confirmed by copying it to an empty directory.
- `self_ref` values are identical (same set, same order) between a
  `--granite-vision-tables` on/off pair on the same PDF — confirmed by
  diffing `nodes.jsonl` from two real conversion runs.
- The new `?ref=` highlight/deep-link code was exercised by regenerating a
  real `preview.html` and grepping the output for the expected markup and
  JS (`cited`, `highlightRefs`, `citation-link`) — balanced-braces checked
  too. **Not** verified in an actual browser (none available in this
  environment) — do a manual click-through before relying on it for a demo.
- `tests/test_engines/test_pdf_engine.py` (13 passed, 1 skipped) and
  `make validate` pass with the `visualizer.py` change included.

## Required features — status

What the viewer needs for a student to navigate a citation easily, and
whether it exists yet:

| Feature | Status |
|---|---|
| Per-node stable ID addressable from JSON output | done — `self_ref` |
| Deep link to a page | done — `#page-N` |
| Deep link + highlight to one or more specific nodes | done — `?ref=a,b,...` (this hand-off) |
| Copy a citation link from the viewer itself | done — panel's "Citation link" field |
| Multi-node citation shown together (not just highlighted) | **not built** — today only the first `ref` opens the side panel; the rest are highlighted but you scroll to see them |
| Single-file, zero-dependency HTML (no separate `images/` folder) | done — `preview.embedded.html` (the viewer, page renders inlined) and `<stem>.html` (reading view; every block carries `data-self-ref` / `data-page` / `data-bbox`, so `<stem>.html#texts-12` is a citation anchor) |
| A landing page/index across many documents | **not built** — if the student receives more than a handful of PDFs, they currently open each `preview.html` separately; no cross-document index exists yet. |

None of the "not built" rows are required for a single-document,
single-citation workflow — the done rows already cover "extract a variable,
link it to where it came from, let a human verify it." Build the rest only
if the workflow in practice needs it.
