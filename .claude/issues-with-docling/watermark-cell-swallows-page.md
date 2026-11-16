# A diagonal watermark folds every page into one text block

| | |
|---|---|
| **Severity** | High: the text survives, the structure does not — no headings, no paragraphs, captions and list items gone |
| **Status** | Patched in this fork (after `extrct_docling-v2.131.0-r3`); upstream PR not yet opened |
| **First-seen** | 2026-11-02 batch; root cause found 2026-11-16 on `samples/4new_for_aca/Eunjung Lee ssrn-7427517 (2).pdf` (SSRN "Preprint not peer reviewed") and `Wang_et_al_2026_…pdf` (accepted manuscript, "ARTICLE IN PRESS") |
| **Affects** | `docling/utils/layout_postprocessor.py` (`_process_regular_clusters`), `docling/models/stages/reading_order/readingorder_model.py` |
| **Upstream issue** | _not filed_ |

## Symptom

A 20-page paper comes out as 5 `text` items, 0 `section_header`, with
`ConversionStatus.SUCCESS`. Each item has the same box (29–582 × 52–741 pt)
and holds the text of several pages.

## Cause

The layout model's raw output is fine (`section_header` 0.82–0.93,
paragraphs ≈ 0.9). The watermark is one text cell rotated −52°, so its
upright bounding box covers 79 % of the page. In `LayoutPostprocessor`:

1. where a paragraph is large, the cell is assigned to it (> 20 % of the
   cell's box lies inside), `_adjust_cluster_bboxes` stretches the paragraph
   to the cell's box, and `_remove_overlapping_clusters` merges every cluster
   that box now contains;
2. otherwise the cell becomes an orphan cluster with confidence 1.0 and the
   largest area, which wins the same merge.

The reading-order stage then joins the page-sized blocks across pages.

## Fix (fork patch, upstream-ready)

- `_find_overlay_cells`: a cell off the page axes by > 5° whose upright box
  takes ≥ 10 % of the page is an overlay, unless most of the page's text is
  skewed (a scan fed in at an angle). Overlay cells are not assigned to
  predicted clusters; each becomes a cluster with `Cluster.overlay = True`
  that stays out of overlap resolution and is never made a child of a table
  or picture it lies over (a full-page table used to take it, and the
  watermark text then appeared nowhere).
- `ReadingOrderModel`: overlay elements are kept out of the predictor
  (ordered with the rest, a watermark sits between a paragraph and its
  continuation on the next page) and are written after their page's elements
  with `content_layer = ContentLayer.BACKGROUND` (docling-core: "eg
  watermarks").

Measured: A/B over 52 sample PDFs with the fast pipeline, rule on vs off —
50 identical text items; the SSRN paper 5 → 89 `text`, 0 → 20
`section_header`, 15 `list_item`, 9 `caption`; the accepted manuscript
40 → 52 `section_header` (Methods, Discussion, References appear), all 34
watermark instances in the background layer. Run-to-run variation of the
pipeline itself showed up once in three sweeps (one paper, one text item,
no skewed cell in it; not reproduced in seven reruns).

A first version singled out every skewed cell; it split 1–5 short cells per
paper off their paragraphs in 12 papers (a word with a raised citation number
is tilted in the parser's geometry), hence the page-share condition.

Tests: `tests/test_layout_postprocessor.py` (overlay kept out; small tilted
cell and a page of skewed text unchanged), `tests/test_watermark_overlay.py`
(synthetic two-page PDF through the layout model: fails on the unpatched
code).

## Not covered

An upright watermark in huge type across the text ("DRAFT", not rotated) is
still assigned to the paragraph it overlaps. No sample at hand; `run.json` →
`quality.warnings` (`few_text_blocks`) flags the collapse it would cause.
