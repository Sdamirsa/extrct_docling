<!-- last-reviewed: 2026-11-16 -->
# Structure pass: where each element of a converted paper sits

Code: `docling/engines/structure.py` (`structure_document`, `quality_report`),
typography reader `docling/engines/text_repair.py::pdf_text_styles`, layout
patch `docling/utils/layout_postprocessor.py::_find_overlay_cells`. Tests:
`tests/test_engines/test_structure.py`, `tests/test_watermark_overlay.py`.
Origin: a downstream extraction pipeline's findings on 18 papers (2026-11-16).

`STRUCTURE_VERSION` (in `run.json` → `structure_version`, `structure.json`,
the HTML manifest) names the rule set. Bump it whenever a rule below, or a
layout stage it builds on, can change a label, a heading level or a link:
locators a consumer made against an older bundle may then no longer hold.
`self_ref`s never change in the pass; an item's label, layer and parent can.

## Order of the pass (runs before every export)

| Step | Rule | Marked as |
|---|---|---|
| Furniture | A `text` / `section_header` of ≤ 150 chars whose text repeats in the top or bottom 10 % of ≥ `noise_repeat_threshold` (3) pages → `page_header` / `page_footer`, furniture layer. A page number at either end of the line is ignored ("12 Z. Arow et al."); other digits are not ("SI.1.2 Example 3"). | `label_source = rule:repeated-text`, `repeat_count` |
| Captions | A `section_header` that reads `Table S11. …` / `Fig. 2` / `Algorithm 1 …`, or a `text` that does so with `.` `:` `|` after the number → `caption`. | `rule:caption-pattern` |
| Missed headings | A `text` that is only a standard section name (short list, no trailing colon: "Funding:" is a run-in label) → `section_header`. | `rule:standard-section-name` |
| Title | Among first-page headings of ≥ 4 words set larger than the section headings: the longest of those within 75 % of the largest size (a journal name is as large and shorter) → `title`. | `rule:largest-heading-on-first-page` |
| Levels | See below; written to `SectionHeaderItem.level`. | `level_source` |
| Caption links | A caption no table/figure owns is tied to the nearest one of its kind on its page that has none (and re-parented under it, as Docling's own captions are). | `caption_ref` / `caption_for` |

## Heading levels

1. **Numbering**: `2.1` → depth, when its first number is at most the count
   of distinct section numbers in the document plus 3 ("75 commonly asked
   questions" is not section 75); `A.1`, `A.`, `Appendix B`, and bare `A Title`
   when the headings run A, B, … → depth, zone `supplement`; `IV.` → 1 when the
   document also has a multi-letter numeral (then `A.` is level 2); `1)` → one
   below the numbered heading before it.
2. **Standard names** (Abstract, Introduction, Methods, Results, Discussion,
   References, Acknowledgements, Data availability, Supplementary …) → 1, and
   they set the zone. Before the Introduction, body names are the parts of a
   structured abstract: level 2 under Abstract, zone `abstract`.
3. **Type** (`level_source = font-size`): font size, weight and slant read
   from the PDF text layer. Used when the document marks levels by type: a
   sub-heading is set lighter than the sections, or numbered sub-sections
   are, or sections are numbered (≥ 3). A heading set like the sections is
   then a section.
4. **Position** (`position`): where every heading is set alike (the SSRN and
   accepted-manuscript layouts), an unnamed heading is a part of the named
   section it follows.

Measured on the 52 sample PDFs (2026-11-16, fast pipeline): 776 headings —
213 by numbering, 181 by standard name, 261 by type, 121 by position; title
found in 47. Box-derived sizes vary ±10 % between headings set alike, so
without the PDF (URL sources, old bundles) only size steps > 15 % count.

Known limits: a heading the layout model invents (an author name, a sentence
tail like "Supplementary Information .") stays a heading; in a document with
lighter sub-sub-headings but sections and sub-sections set alike, the
sub-sections come out as sections.

## Roles and zones

`role`: title, front-matter, abstract, section, body, reference, back-matter,
supplement, figure, table, `<kind>`-caption (figure, table, algorithm, box,
scheme, listing), figure-text, table-text, footnote, formula, code, form,
page-header, page-footer, watermark. Running text takes the zone of its
level-1 section; before the first numbered or named section it is
front-matter.

`first_mention_ref`: first running-text item citing the float's number
(`Fig. 3`, `Tables 2`, prefix-aware: `Supplementary Table 1` ≠ `Table 1`);
`section_ref` is always the physical position.

## Quality warnings (`run.json` → `quality.warnings`)

| Code | Blocking | Raised when |
|---|---|---|
| `no_body_text` | yes | no characters in body text or tables |
| `few_text_blocks` | yes | fewer body text items than pages while the body holds ≥ 200 chars per page (the page collapsed into a few blocks) |
| `no_headings` | no (a `check.json` issue) | > 5 pages, no section header |
| `repeated_heading_text` | no | a heading text ≥ 3 times after the furniture rule |
| `text_mostly_in_tables` | no | > 50 % of characters in table cells |
| `pages_without_content` | no | pages with no body text, table or figure |

A blocking warning adds a `quality` entry to `errors` and sets `status` to
`PARTIAL_SUCCESS`.

## Watermarks (layout stage)

A text cell off the page axes by > 5° whose upright box covers ≥ 10 % of the
page, on a page where upright text is the majority, is an overlay: kept out
of cell assignment and overlap resolution (it used to fold the page into one
block), never a child of a table or figure it lies over, out of the reading
order, and written as a `text` item in the `background` layer. A/B on 52 PDFs: 50 unchanged, the two watermarked ones
fixed. See `.claude/issues-with-docling/watermark-cell-swallows-page.md`.
