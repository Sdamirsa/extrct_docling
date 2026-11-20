<!-- last-reviewed: 2026-11-20 -->

# What the r5 bundles lose: tables and text (2026-11-20)

Three investigations of the bundles release r5 wrote for 88 documents
(65 trial papers and supplements, 4,107 pages, 1,705 tables; plus 23 papers
on medical AI agents, 398 pages, 135 tables). Each was done by an
independent agent on the bundles and the source PDFs, the second with
re-runs of the table models on single pages. Nothing in the engine was
changed by them. The garbled text layers found on the way are fixed in r6
(`docling/utils/text_layer.py`, HANDOFF §9).

**Measured** = counted or re-run. **Inferred** = a reading of the numbers.

## 1. Tables

The check flags a table when its cells hold less than 95 % of the words the
PDF prints in its box: 546 of 1,705 tables (33.6 % of the 1,626 that have
text in their box). For a flagged table the PDF's text is kept beside the
grid, in every export.

### Who made the flagged tables (measured)

| Path | All | Flagged |
|---|---:|---:|
| Granite-Vision alone | 1,660 | 538 |
| Granite-Vision kept after TableFormer's grid was also unusable | 13 | 6 |
| TableFormer after Granite-Vision hit its budget | 12 | 2 |
| TableFormer after a degenerate Granite-Vision grid | 20 | 0 |

The bundles do not record which model made a table. It was recovered from
two traces that agree: TableFormer's cells have boxes and Granite-Vision's
have none, and the batch logs name every fallback.

### Why words are missing (measured on 30,436 missing words)

| Cause | Share |
|---|---:|
| Granite-Vision leaves printed content out: continuation rows, rows, columns, bullets, later paragraphs of a cell | 78 % |
| Two words glued where a cell's line breaks ("Pvalue") | 13 % |
| A word or number misread | 4 % |
| A letter with an accent dropped (umlauts) | 3 % |
| A superscript glued to its word | 2 % |

- **A parser bug, not the model.** `docling/utils/otsl.py` (`_TAG_PATTERN`)
  reads a cell's text as `[^<]*`: a printed `<` ends the cell ("p<0.001",
  "Age < 18", "CrCl <30"), and `<ul><li>` inside a cell becomes columns. 305
  tables print `<`; no Granite-Vision cell in the corpus holds one. 208 of
  the flagged tables print it. Re-parsing the same model output with a
  corrected parser moved two sampled tables from 0.22 and 0.34 to 0.99. 178
  cells in 76 tables that pass the check are cut the same way, with no PDF
  text kept beside them.
- **About one flag in five is an artefact.** At least 101 flagged tables
  (18.5 %) hold all their content: lines glued without a space, accents,
  superscripts. 351 (64 %) have real content dropped.
- **No truncation by the generation budget** was found in the sample.

### What the check cannot see (measured)

- **Wrong numbers in tables that pass.** Granite-Vision retypes the cells
  from an image at 72 dpi. 31 of the 76 manuscript tables with text hold a
  number the page does not print; 10 of those pass the check. Read against
  the page: a JAMA baseline table gives 177 for 172, 210 for 230, 769 for
  749 and "Pacelizumab" for paclitaxel, and passes at 0.9502; a Lancet
  baseline table gives 118/1379 (8.5 %) for 1178/1379 (85.4 %); an outcomes
  table gives a hazard ratio of 0.76 for 0.26 and p 0.025 for 0.076.
- The measure counts words of two characters or more: 38 to 48 % of the
  printed numbers ("3", "0.5") produce no token, and a value in the wrong
  cell counts as found.
- 79 tables are images without text: never measured.
- 72 flagged tables have a number in the grid that differs from the kept
  PDF text, and nothing says which is right. The PDF text is.

### TableFormer on the same pages (measured)

TableFormer takes the cell text from the PDF. Each page was converted
alone with both models, the layout being the same.

| | n | Granite-Vision at 0.95 or more | TableFormer at 0.95 or more |
|---|---:|---:|---:|
| Flagged tables, stratified sample | 18 | 0 | 17 |
| Flagged tables, random | 80 | 0 | 70 |
| Tables that pass, random | 40 | 40 | 38 |

- Structure, judged by eye against the page on 22 tables: TableFormer
  better in 11, Granite-Vision in 1, both right in 9, mixed in 1.
- TableFormer never wrote a number the page does not print.
- Time of the table stage on the 22 pages: 826 s against 7.9 s.
- Where TableFormer is worse: tables of contents (Granite-Vision gives a
  clean number, title, page grid); it splits spanning headers, adds a
  footnote or caption line inside the box as a row, splits a word where
  the font changes ("S afety"), and once moved text between rows. On a
  garbled text layer it copies the garbage (r6 decodes or drops that text
  first). A table without text depends on OCR.
- Granite-Vision at 144 dpi with the corrected parser removed every wrong
  number in two tables (one went to 1.0) and none of the omissions, at 1.5
  times the time.

### Built in r7

Points 1 to 3 below, and footnotes in markdown and chunks (section 2). The routing adds a check of Granite-Vision's own tables: under 0.8 of the box's PDF words, TableFormer redoes the table (it caught the two contents fragments). Measured on single pages of the r5 bundles (2026-11-20): of 18 flagged and 4 passing tables chosen by recall and size, 17 and 4 hold 0.95 of their printed words (Granite-Vision alone: 0 and 4); of 80 random flagged and 40 random passing tables, 68 and 38 (Granite-Vision alone: 0 and 40); 110 of 120 are made by TableFormer. The table stage of the 22 pages took 8 s instead of 826 s.

### Recommendation (as made before r7)

1. TableFormer for a table box that has PDF text; Granite-Vision for a box
   the layout calls a table of contents and for a box without text. On 80
   random flagged tables this rule takes 64 to 0.95 or more.
2. Correct the OTSL parser whatever is decided: only the real tags count as
   tags. To be filed upstream.
3. Record in each table which model made it.
4. In the check: a flag for numbers in the cells that the box does not
   print, and a comparison that ignores spaces.

Either of 1 and 2 changes table output, so the sets have to be converted
again to gain from it.

## 2. Text

### From the PDF to the document (measured, 1,314,930 PDF words)

38,934 words are counted as missing. No sentence of the running text is
among them.

| Kind | Words |
|---|---:|
| Table cells, kept as the PDF text beside the table | 29,939 |
| Table cells with no such text: lost from every export | 2,137 |
| Spacing and tokens (the text is there, glued or split) | 4,353 |
| List markers (in the markdown all the same) | 1,608 |
| Formulas that were not decoded | 408 |
| Other (furniture spacing, fragments) | 489 |

- Running headers and footers, stamps and watermarks all reach the document
  as furniture.
- Glued words in six documents (a journal's justified text): the markdown
  reads "cautionsweretakentomaximizeadherence".
- One main paper has no text layer at all: its text is OCR, and no check
  can compare it with anything.

### From the document to markdown and chunks (measured)

- **Footnotes of tables and figures are missing from the markdown and the
  chunks**: 350 items, 5,840 words, 31 documents, 9 of them main papers.
  They explain every markdown finding under 0.99. docling-core's table and
  picture serializers never write a floating item's footnotes, and the tree
  walk leaves them to the item. They hold analysis populations ("No valve
  deployed in 7 patients"), missing data ("Data are missing for 91
  patients"), definitions. The HTML has them.
- **Text printed inside figures is in the HTML only**: 156 data figures
  (flow diagrams, survival curves, forest plots) hold 16,813 words, and 30
  to 38 % of their distinctive numbers appear nowhere in the markdown:
  patients per arm, numbers at risk, hazard ratios of subgroups. No check
  measures this.
- **Chunks drop some headings**: the chunker does not emit a heading that
  a later heading of the same or a higher level replaces before any text
  came. Ten lines of content that the layout took for headings are lost
  that way (137 words), among them "Data available: No".
- 136 formulas are a placeholder in the markdown; the HTML has their text.
- The check's chunk measure counts a repeated heading once: 2,280 words of
  its chunk "loss" are that, not a loss.

### Can it harm a reader? (inferred from the above)

Yes, when the reader takes the markdown or the chunks: numbers that are
printed only inside a figure, the footnotes of tables, and some thresholds
of tables (the 2,137 words) are not there. The HTML is the only export that
holds everything Docling extracted. Read it without the embedded images,
with the table rows and the collapsed blocks. What it still lacks: the
2,137 table words, the structure of formulas, the spaces of glued words.

### Fixes, by harm avoided (not built)

1. Write the text inside data figures into markdown and chunks, marked, and
   measure it in the check.
2. Write the footnotes of tables and figures in the markdown and chunk
   serializers.
3. Keep the PDF text beside a table also when a number or a `<`, `>`, `%`
   is missing from its cells, whatever its recall.
4. Chunker: emit every heading; check: count repeated headings.
5. Write the formula's text instead of the placeholder.
6. Put the spaces back into glued words from the PDF text, as the ligature
   repair does.

## 3. Garbled text layers

Found by all three, fixed in r6: see HANDOFF §9. In the r5 bundles the
markdown of such a document passes its export check at 1.0, since the
exports hold what the document holds.

## Where the numbers come from

Agent scripts and outputs were in the session's scratch folder and are not
kept. The tables can be measured again from the bundles: the check's own
functions (`attach_table_pdf_text`, `_check_tables`), cell boxes to tell
the two table models apart, and a single-page conversion
(`page_range=(n, n)`) with `granite_vision_tables` on and off.
