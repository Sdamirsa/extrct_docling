# Continuation of a cross-page paragraph gets its bbox from the wrong page height

| | |
|---|---|
| **Severity** | Low for content (the text is in the item, so every export has it); medium for provenance — the page highlight and `data-bbox` of the continuation point at the wrong region |
| **Status** | Patched in this fork (commit after `extrct_docling-v2.131.0-r3`); upstream PR not yet opened |
| **First-seen** | 2026-11-05, `showcase/Public-test-manuscript.pdf` page 6 (landscape, 612 pt high) → page 7 (portrait, 792 pt high), item `#/texts/44` |
| **Affects** | `docling/models/stages/reading_order/readingorder_model.py` — the merge loop in `_readingorder_elements_to_docling_doc` passes the first page's height into `_merge_elements` |
| **Upstream issue** | _not filed_ |

## Symptom

A paragraph that the reading-order model merges across two pages of different
height gets a second `ProvenanceItem` whose bbox was converted to BOTTOMLEFT
with the first page's height. With 612 → 792 pt the box is shifted by 180 pt:
the paragraph at the top of page 7 (t ≈ 717) is boxed at t = 537, so the
preview highlights the wrong region and the real text lies inside no box.

## Fix (fork patch, upstream-ready)

```python
merged_elem = id_to_elem[cid_to_rels[merged_cid].ref.cref]
# The continuation can lie on a page of another height.
merged_page_height = out_doc.pages[merged_elem.page_no].size.height
self._merge_elements(element, merged_elem, new_item, merged_page_height)
```

Test: `tests/test_readingorder_cross_page_merge.py` builds a landscape +
portrait PDF with pypdfium2 and asserts each prov box of the merged item
holds that page's lines (fails on the unpatched code: the page-2 box is empty).

Other call sites were checked: captions, footnotes and table-picture matches
only pair elements on the same page, so their page height is right.

## PR text

fix(reading-order): convert a merged continuation's bbox with its own page
height. `_readingorder_elements_to_docling_doc` passed the height of the page
where the paragraph starts into `_merge_elements`, which converts the
continuation's cluster bbox to BOTTOMLEFT with it. When a paragraph runs onto
a page of another height, the continuation's `ProvenanceItem` is shifted by
the height difference and no longer covers its text. Fix: look up
`out_doc.pages[merged_elem.page_no].size.height`.

## Related finding (not a Docling bug)

`check.json` now reports printed text outside every item box
(`uncovered_text`). It cannot see text in fonts without a Unicode map:
AMIE-Cardiology Supplementary pp. 15–17 (a Nature reporting-summary form in
an ArialMT subset) read as control codes in the text layer, got no layout box,
and are missing from the markdown. Catching those needs an "unmapped text
layer" flag or OCR of such regions.
