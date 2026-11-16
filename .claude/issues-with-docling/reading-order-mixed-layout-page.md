# Reading-order flip on mixed-layout pages (full-width over two-column)

| | |
|---|---|
| **Severity** | Medium — produces semantically broken markdown on academic-journal layouts |
| **Status** | Open, not yet filed upstream |
| **First-seen** | 2026-05-21, during Phase 1 smoke-testing of `PdfEngine` |
| **Affects** | `docling.document_converter.DocumentConverter` + Heron layout pipeline (default config) |
| **Upstream issue** | _not yet filed — this doc is the future bug report draft_ |

## Symptom

On a PDF page that has **(a)** a full-width region at the top (e.g. abstract
spillover, page header, an unbreakable figure) above **(b)** a two-column body,
Docling's reading-order postprocessor emits the **right column before the left
column** of region (b). The horizontal full-width region (a) is read correctly;
only the column order within (b) is wrong.

### Concrete example

Reproducer: [samples/archived/test-pdf-ai-manuscript.pdf](../../samples/archived/test-pdf-ai-manuscript.pdf) — *European Journal of Radiology*, two-column journal layout.

The H2 list of the generated markdown (`samples/archived/out/test-pdf-ai-manuscript/test-pdf-ai-manuscript.md`) starts:

```
## Reproducibility assessment of rapid strains in cardiac MRI: ...
## A R T I C L E  I N F O
## European Journal of Radiology
## A B S T R A C T
## 2.3. Image analysis            ← wrong — this is on page 2, right column
## 2.4. Statistical analysis      ← wrong — also page 2, right column
## 1. Introduction                ← page 2, left column top — should come first
## 2. Materials and methods
## 2.1. Study population
## 2.2. Cardiac MRI acquisition
## 3. Results
...
```

Correct order: `1 → 2 → 2.1 → 2.2 → 2.3 → 2.4 → 3 → …`.

## Diagnostic data

All affected headings are on **page 2**. Bounding-box top-left coordinates
(PDF points, bottom-left origin — higher `t` = closer to page top):

| order in MD | page | bbox.t | bbox.l | column | text |
|---|---|---|---|---|---|
| 0 | 2 | 570.5 | 306.6 | right | 2.3. Image analysis |
| 1 | 2 | 214.5 | 306.6 | right | 2.4. Statistical analysis |
| 2 | 2 | 675.5 | 37.6 | left | 1. Introduction |
| 3 | 2 | 298.8 | 37.6 | left | 2. Materials and methods |
| 4 | 2 | 225.3 | 37.6 | left | 2.1. Study population |
| 5 | 2 | 78.5 | 37.6 | left | 2.2. Cardiac MRI acquisition |

Probe used:

```python
out = PdfEngine().convert(Path("samples/archived/test-pdf-ai-manuscript.pdf"))
for item, _ in out.raw.document.iterate_items():
    if not hasattr(item, "text") or not item.text:
        continue
    prov = item.prov[0] if item.prov else None
    if prov: print(prov.page_no, prov.bbox.t, prov.bbox.l, item.text[:60])
```

## Root-cause hypothesis

Page 2's actual layout has three vertically-stacked regions:

1. **Full-width** — running page header (`M.C. Halfmann et al. | European Journal of Radiology …`).
2. **Full-width** — abstract continuation (`conclusion: Simplified rapid …`) ending with a horizontal rule.
3. **Two-column** — left = section 1 Intro + sections 2/2.1/2.2 stacking down; right = continuation of section 2's body from page 1 + sections 2.3 / 2.4 stacking down.

The postprocessor in [`docling/utils/layout_postprocessor.py`](../../docling/utils/layout_postprocessor.py)
handles regions (1) and (2) correctly (they appear at the right place in the
output), but for region (3) it emits the right column before the left. The
flip appears to happen because the right column's first cluster starts at a
*higher y* than the left column's first cluster (the right column begins
right under the abstract end-marker; the left column begins below that).

Cross-page reading order is a related second-order failure: section 2's body
should be read entirely in document order (page 1 right-col → page 2 right-col),
which is *only* correct if region (3) on page 2 is read column-by-column with
the right column already known to be a continuation. Today neither half is
reliable on this page.

## Workarounds (status)

| # | Approach | Tested? | Result |
|---|---|---|---|
| 1 | `PdfPipelineOptions(force_backend_text=True)` — use the PDF's embedded text stream order instead of layout-predicted order | ❌ not tested | Hypothesis: likely fixes this case because the publisher's text stream already encodes correct reading order |
| 2 | Switch from Heron to DocLayNet layout model via `LayoutOptions` | ❌ not tested | Hypothesis: less aggressive column-merging; may or may not help |
| 3 | Pre-segment page into "stripes" of consistent column count and walk stripes top-to-bottom (left→right within each stripe) | ❌ not implemented | This is the correct general fix; would require an upstream PR to `layout_postprocessor.py` |
| 4 | Document the limitation and live with it for Phase 1 (downstream consumers can re-sort by `(page_no, column_bin, y)` for two-column papers if reading order matters more than the layout model's section detection) | ✅ accepted for now | — |

## Decision (2026-05-21)

Phase 1 ships as-is. Reading-order is not the foundation Phase 1 was about
(the foundation is the wrapper + schema + viewer, all of which work). When
Phase 2 starts touching content extraction with hierarchy preserved, this
matters more — at that point we test workaround #1 (`force_backend_text`)
and decide whether to expose a `reading_order` knob on `PdfEngine` or file
upstream.

## Filing upstream — checklist for the future

When this gets escalated to a docling-project issue:

- [ ] Trim the reproducer to a 2-page sample (page 1 + page 2 of the manuscript only) to keep the upload small.
- [ ] Run with the exact upstream main (no fork patches) and confirm reproducible.
- [ ] Capture the layout-model raw clusters + the postprocessor's reordering, attach both.
- [ ] Reference the failing class of layout ("mixed full-width over two-column body") and link this doc.

## See also

- [.claude/REPO_CONTEXT.md](../REPO_CONTEXT.md) → `Where to plug Amir Engine in` — for which Docling primitive owns reading order.
- [.claude/AMIR_STAGE.md](../AMIR_STAGE.md) → Phase 1 log entries.
