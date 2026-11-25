<!-- last-reviewed: 2026-11-25 -->

# Docling-parse 7.20's text faults, the r8 repair, and the upgrade plan (2026-11-25)

Read this first in the session that upgrades docling-parse. It holds what
was found, what release r8 does about it (a temporary repair of our own),
and the plan for the upgrade at the project, architecture, component and
code levels. The numbers of the r8 reconversion are in §8. **The upgrade
was done the same day (r9): its results and what changed in the plan are
in §9**; §2-§7 describe r8 and the plan as written before it.

## 1. What was found

Random and full checks of the 416 bundles converted 2026-11-20 to 11-24
(`nirct_remaining127_out` 326, `nirct_validation22_out` 67, `aca-papers_out`
23; release r7, docling-parse 7.20.0) found two faults the bundle check did
not name (it saw low page recall only):

| Fault | Example | Where | Cause |
|---|---|---|---|
| Look-alike letters | "RepoƌtiŶg SuŵŵaƌǇ" for "Reporting Summary" | 1 bundle (`38760584` p13 and p21-25: eligibility criteria, an MRI protocol, a Nature reporting summary) | docling-parse gives a glyph number as the character for a Calibri-Light subset written by Word (code points 0x18C, 0x176... are Calibri glyph ids). pdfium reads the same characters right, so r6's text-layer detection (which asks pdfium) did not see it. |
| Fused words | "studiesandsmallrandomizedclinicaltrialssuggestthatCSPcan" | 27 bundles, 123 pages with runs the PDF's own text does not hold; r8 separates 82 pages of 17 (JAMA-style manuscripts mostly: `41811324` whole paper, `35881121`, `29297076`, `31237645`; none in aca) | Justified text without space characters; docling-parse puts a space where the gap exceeds a share (`line_space_width_factor_for_merge_with_space`, default 0.33) of a space width, and the tight gaps fall under it. The text is complete; keyword search, embeddings and quoting suffer. |

Measured on real pages (`$S/garbled/parser_versions.py`; fused = share of
18+ letter tokens; one-letter = single letters other than a/I, a sign of
words split):

| Page | 7.20 default | 7.20, space factor 0.20 | 7.28 default |
|---|---|---|---|
| 38760584 p21 (look-alikes) | 643 look-alikes, 58.5 % vocabulary | unchanged | 0 look-alikes, 99.2 % |
| 41811324 p2 / p4 (fused) | fused 4.6 % / 3.1 % | 0.0 % / 0.0 % | 1.3 % / 0.5 % |
| 35881121 p2, 29297076 p3, 31237645 p3 | 2.3 / 3.2 / 2.4 % | 0.0 % each | 0.0 / 0.3 / 0.0 % |
| controls: NEJM 36477458 p3, 38760584 p3, a 107-page supplement p101, AgentMD p2 | fused 0 %, one-letter 1.1 / 3.1 / 1.4 / 2.8 % | one-letter **5.5** / 3.2 / 2.2 / 2.8 % (0.20 splits words on NEJM) | one-letter 0.8 / 3.1 / 1.4 / 2.8 % |
| r6 cases: 29297076_supplement2 p5 (glyph order), 41910382_supplement1 p66 (unmapped) | garbled / empty | unchanged | **unchanged**: the PDF's own fault, r6 still needed |

In 7.28 the space-factor settings change nothing on these pages (its space
logic is new). 7.28 requires docling-core >= 2.99 (we pin 2.98.0).

A third kind, found while building the repair, is the PDF's own fault and
neither reader can fix it: a Calibri subset whose codes are its **glyph
numbers** (Identity-H without a Unicode map, glyph 3 for a space, which
pdfium gives as `\x03`): `34449183_supplement1` p374 reads "Ϯ͘ϲ ŝŶ ƐƵďũĞĐƚƐ"
for "2.6 in subjects" in both readers. r6 counts only the control
characters of such a font, so the page stays under its 2 % "partly
unreadable" line. `check.json` -> `text_quality.unmapped_pages` names such
pages since r8. A mechanical fix for a later release: decode the codes
through the embedded font's own `cmap` table (fontTools: glyph id -> code
point, inverted), exact as r6's glyph-order decoding; else OCR those lines.

The danger met on the way: a Symbol font prints Greek letters from ASCII
codes, so pdfium reads "81-91* mm" where the page prints "81-91* μm" and
Docling reads it right (`34735004_supplement1` p5; "[c] μM", a proportion
"π"). A repair that takes pdfium's ASCII for a Greek letter turns one unit
into another, so the Greek letters U+0386-U+03D7 are not look-alikes.

## 2. What release r8 does (temporary repair of our own)

`docling/utils/parser_repair.py`, called by the page preprocessing stage
right after r6's text-layer reading, on the parser's text cells, so layout,
TableFormer (word cells), the chunks and every export get the repaired text:

- **Fused words:** a page with 3+ runs of 18+ letters is decoded again by
  docling-parse with space factor 0.20 (`Respacer`); the new line and word
  cells replace the old ones only when the characters are the same (0.5 %),
  the runs at least halve and the one-letter share rises by at most 1 point.
- **Look-alike characters:** on a page whose cells hold any character of
  U+0100-U+0385 or U+03D8-U+04FF (Latin Extended-A/B for letters and
  brackets, the Coptic forms for digits: the same Calibri subset printed
  "8500" as "ϴϱϬϬ" and "(1)" as "śłŜ"; the Greek letters are left out, see
  §1), each such character that pdfium (`text_layer.read_pages`
  + `PageTextLayer.read_box`) reads as a printable ASCII character at the
  same place takes pdfium's. The places come from an alignment of the two
  texts without spaces and pdfium's non-ASCII marks, where a look-alike
  against an ASCII character costs nothing (`_aligned`): `difflib` left
  "śŃa)" unpaired against "(2a)". A real "ł" or "μ" reads the same in
  pdfium and stays.
- Pages r6 reads through their fonts are left to r6. Switch:
  `PdfPipelineOptions.repair_parser_text` (default on).
- Recorded: `run.json` -> `quality.parser_repair` (`respaced_pages`,
  `letter_pages`, `letters`) and warning `parser_text_repaired`;
  `check.json` -> `text_quality` names pages that still show either fault
  (`fused_pages`, `lookalike_pages`) whether or not the repair ran, counting
  only what the PDF's own text of the page (pdfium's) does not hold: 3+
  runs of 18+ letters, 3+ look-alike characters. That keeps
  "electrophysiological" and Czech author names out (38760584 p7, p13 were
  false alarms before), and found the digits of p13 and p24 the first rule
  missed. Its limit: a run pdfium also reads together is not named (the
  synthetic test page; on the JAMA pages pdfium has most spaces).
- Also in r8: a PDF made from a Word file named like a PDF of the batch is
  bundled as `<name>_docx` (it was `<name>_2`, and took the plain name from
  the original PDF because `_converted/` sorts first).

## 3. Project level

- **Goal:** the trial-paper bundles the team uses read as printed, with the
  fork carrying as little parser code as possible.
- **Decision:** fix each fault in the layer that owns it. Parser faults ->
  upstream (upgrade docling-parse); faults of the PDF itself (no Unicode
  map: r6) -> our `text_layer.py`; naming the residue -> our check. r8's
  repair is a bridge so today's bundles can be used, to be removed once the
  upgrade is proven.
- **Not done, on purpose:** no LLM in the conversion engine (a model that
  rewrites trial text can invent a number; model reading stays an opt-in,
  labelled post-step like figure-to-data); no word-segmentation code (the
  measured residue does not need it); no rebase onto a newer Docling in the
  same step (one change at a time).
- **Costs and risks:** the upgrade changes the environment (needs the
  user's go-ahead: the session rule is `uv run --no-sync`); a parser change
  moves every page's cells, so it is proven on a sample before a release;
  docling-core moves too (HANDOFF: rerun
  `test_document_html_keeps_everything_docling_extracted` first).
- **Done when:** (1) on the five sample documents (§7) the upgraded parser
  with the repair off has no fused or look-alike page that r8 fixes, and
  nothing else in the checks is worse; (2) the repair is removed or kept
  by that evidence; (3) a release (r9) and the reconversion policy are
  decided by the diff of normal pages.

## 4. Architecture level

```
PDF -> docling-parse (cells: line, word, char) -> page preprocessing
        [r6 text_layer: fonts without a Unicode map; r8 parser_repair]
     -> OCR (pages r6 leaves) -> layout -> TableFormer (word cells) /
        Granite-Vision (r7 routing) -> assemble -> exports -> check.json
```

- Repairs live at the cell level, before any model: one place, every
  consumer sees the same text. Exports are never patched afterwards.
- Every repair is recorded in `run.json`; the check measures the result
  independently of whether a repair ran (so it catches a regression of the
  parser after an upgrade, and the repair being switched off).
- Dependencies: docling 2.131.0 (fork base) -> docling-parse 7.20.0
  (`pyproject.toml` `>=7.20.0,<8`) and docling-core 2.98.0 (`>=2.98,<3`);
  7.28.0 needs docling-core >= 2.99. pdfium (pypdfium2 5.13.0) is the
  second reader for r6 and r8.
- What depends on the parser's cells and must be re-measured on an upgrade:
  r6's glyph-order replacement (`read_box` by cell box), r7's table routing
  (`MIN_PDF_WORDS_HELD`, PDF words of a box), TableFormer's cell matching
  (`MatchingPostProcessor`), the check's page recall and ligature repair,
  chunk sizes.

## 5. Component level

| Component | Role | On the upgrade |
|---|---|---|
| `docling/utils/parser_repair.py` | the two repairs, `ParserRepairSummary` | measure with the switch off and on; remove the module, `Page.parser_*`, the option, the record and its warning if it changes nothing |
| `docling/utils/text_layer.py` | r6, PDF faults; `read_pages` (r8) for any page | keep; recheck the r6 tests and the two r6 PDFs (unchanged in 7.28) |
| `page_preprocessing_model.py` | calls r6 then r8 per page | `_repair_parser_text`, `_document_respacer` go with the module |
| `datamodel/base_models.py` `Page` | `parser_respaced`, `parser_letters_repaired` | go with the module |
| `datamodel/pipeline_options.py` | `repair_parser_text` | goes with the module (keep the check) |
| `engines/structure.py` / `pdf_engine.py` | `quality.parser_repair`, `parser_text_repaired` | go with the module |
| `engines/export_check.py` `TextQualityCheck` | names fused / look-alike pages | **keep**: it is how a future parser regression shows |
| `engines/cli.py` `_plan_bundles`, `pdf_engine.resolve_pdf_dir(base=)` | `_docx` naming | keep (independent of the parser) |
| tests `test_engines/test_parser_repair.py` | the fault, the repair, the check | `test_docling_parse_runs_the_words_of_tight_text_together` fails once the parser no longer joins those words: expected on 7.28, then delete with the module |

## 6. Code level

- Thresholds and why: `FUSED_RUN_LETTERS = 18` and `MIN_FUSED_RUNS = 3` (no
  control page held one such run, fused pages 2.3-4.6 % of their words);
  `RESPACED_SPACE_FACTOR = 0.20` (separates every fused page measured;
  0.10 splits words); `MAX_ONE_LETTER_RISE = 0.01` (fused pages rise 0-0.1
  points, the NEJM control 4.4); `MAX_CHAR_DIFFERENCE = 0.005`;
  `LOOKALIKE = [U+0100-U+0385 U+03D8-U+04FF]`; `_GLYPH_NUMBERS` (the check's
  unmapped characters: Latin Extended-B but for Romanian, Vietnamese and
  Pinyin letters, IPA, Greek signs, Coptic forms; 10 on a page); the repair
  looks at any page with one such
  character (one pdfium page read); `MIN_PAGE_LOOKALIKES = 3` is the check's,
  counted beyond what the PDF's text holds.
- On 38760584 the repair went from 3,459 letters (ASCII letters only, pairing
  by count) to 3,726 (alignment, digits and brackets, Greek and Coptic), and
  the check from 2 false alarms plus a missed page to none.
- `Respacer` uses docling-parse's non-threaded `DoclingPdfParser` with
  `DecodeConfig(line_space_width_factor_for_merge_with_space=0.2,
  word_space_width_factor_for_merge=0.2)`, other settings default (the
  backend's `enforce_same_font` default is the same), cells turned to
  top-left origin as the backend does; one per document, opened on the
  first fused page. In 7.28 these two fields still exist but do not change
  the output on the pages measured: the repair would be a no-op there.
- Pairing: pdfium's line-end hyphen marks (U+0002, U+FFFE) count as "-";
  its non-ASCII punctuation and symbols (a bullet) are left out of the
  alignment; only a look-alike becomes an ASCII character.
- Known residue: two words whose letters stand on their stems ("and left")
  stay joined at 0.20 (the test page shows it); 7.28 keeps 1.3 % on
  41811324 p2. The check names such pages.
- Measured gaps (test PDF, Helvetica 10 pt, TJ shifts without spaces):
  7.20 default joins words up to 125/1000 em apart, 0.20 separates from 100.

## 7. Next session: the plan

1. Baseline on 7.20 (r8 tag): tests green;
   `scripts/text_quality/inspect_parser_faults.py` gives the pages the
   repair changes per bundle; `scripts/text_quality/compare_parsers.py`
   scores chosen pages for the installed docling-parse (run it in a
   throwaway environment for another version, as in §1).
2. Branch `parser-upgrade`; with the user's go-ahead: `uv add
   "docling-parse==7.28.0"` (pulls docling-core >= 2.99; take the lowest
   that resolves) and `uv sync`. Run the HTML-completeness test first, then
   the whole suite, `make validate`.
3. Five sample documents, each converted three ways (r8 on 7.20; 7.28 with
   `repair_parser_text` on; 7.28 off):
   `41811324.pdf` (fused, JAMA, 9 p), `38760584.pdf` (look-alikes p21-25,
   25 p), `29297076_supplement2.pdf` (r6 glyph order), `41910382_supplement1.pdf`
   (r6 unmapped + OCR), `36477458_supplement1.pdf` (normal control, 107 p,
   28 tables; NEJM-style manuscript `36477458.pdf` is the over-split
   control if a sixth is wanted). Compare: `check.json` ok and issues,
   page recall, `text_quality`, `text_layer`, tables (count, structure
   model, low recall, degenerate), chunks, seconds per page, crashes; and a
   word diff of the markdown of the normal pages.
4. Decide: repair off is as good as on -> remove it (keep the check);
   on is better -> keep and adapt; anything worse -> stay on 7.20 and report
   upstream. Then release r9 and choose the reconversion (all sets if
   normal pages change, else only the bundles r8 repaired).
5. Report the residue upstream (docling-parse) with the papers' DOIs, not
   the files.
6. Small engine fix, any release: `public_source_path` keeps a linked path
   under the current directory instead of the file name only (§8).
7. Then the next fix (separate from the upgrade): fonts whose codes are
   glyph numbers of the embedded font (§1, `text_quality.unmapped_pages`):
   decode through the font's `cmap` in `text_layer.py`, measured on the
   pages the check names, before any OCR fallback.

## 8. The r8 reconversion of 2026-11-25

- **Inspected:** all 416 bundles, with the repair's own rules on
  docling-parse's cells (`scripts/text_quality/inspect_parser_faults.py`,
  19 min) and with the check's `text_quality` on the bundles' text against
  the PDFs' (the same function, ~15 min).
- **Converted again with r8** from a worktree at the tag (`--only`): 24
  bundles, 16.5 min in all. r7 copies are kept in
  `samples/archived/r7_before_r8/` (444 MB). Figure readings: kept aside,
  put back (7 bundles, no picture moved) and embedded again; none read again.

| Set | Bundles redone | Why | check ok of the set, r7 -> now |
|---|---|---|---|
| nirct_remaining127 | 17 | 10 respaced (59 pages), 38760584 look-alikes (3,726 characters, 6 pages), 6 for the `_docx` names | 249 -> 256 of 326 |
| nirct_validation22 | 5 | respaced (24 pages) | 46 -> 50 of 67 |
| aca-papers | 2 | respaced (AgentMD p5, p7; Dynamic-Specialist-MAS p6) | 18 of 23 (both passed before) |

  Document recall of the repaired bundles: 0.85-0.95 -> 0.98-0.99 (e.g.
  41811324 0.888 -> 0.981, 38760584 0.849 -> 0.991, 41060665 0.906 -> 0.991).
  The `_docx` pairs hold the same as before under their new names.
- **Residue** (named by `text_quality`, text complete but joined): fused
  runs that decoding again did not separate on 30 pages of 8 bundles of
  nirct_remaining127 (21 in the scanner manual `30883058_supplement1`), 12
  pages of 3 in nirct_validation22 (`41849741_supplement1` 10 of them), aca
  `AMIE-Mx` p20; glyph numbers in both readers: `34449183_supplement1` p374.
- **Found on the way: input paths from a worktree.** A batch run from a
  worktree whose `samples/` folders are links records `run.json` ->
  `source.input` as the file name only (`public_source_path` resolves the
  link to the main checkout, outside the worktree's directory, and keeps
  the name for privacy). The checks written at conversion were right (the
  engine passes the path); a later `amir-figdata embed` re-checked without
  the PDF and skipped page recall, and the figure-to-data step on another
  machine would not find the PDFs. All 333 such records (the whole
  nirct_remaining127 set, converted from the r7 worktree, and the 7 r8
  bundles of the other sets) were given their path from the repository
  root in place (that field only, PDF found by hash and name), and the 7
  re-checked. Engine fix for the next release: keep the path as given
  (`os.path.abspath`, not `resolve`) when it lies under the current
  directory, or run batches from the repository root at the tag.
- **Transfer:** `samples/nirct_remaining127-r8-2026-11-25.zip` (the output
  and source folders at their `samples/` paths, with
  `README-nirct_remaining127.md` at its root). The disk had 23-26 GB free;
  the other two sets were not zipped (not needed).

## 9. The upgrade, 2026-11-25 (release r9)

docling-parse 7.20.0 -> 7.28.0 and docling-core 2.98.0 -> 2.99.0 (the lowest
that 7.28 accepts; one change at a time), on branch `parser-upgrade`, with the
user's go-ahead. Installed with `uv pip install` of the two exact versions,
not `uv sync`: only those two packages changed, the CUDA torch stayed.

**Does the upgrade fix the faults?** Half of them.

| Page (docling-parse's own line cells) | 7.20 | 7.28 |
|---|---|---|
| 38760584 p21, look-alikes | 649 look-alikes, 38.5 % dictionary words | 0, 97.7 % |
| 41811324 p2 / p4, fused | 4.6 % / 3.1 % of words fused | 1.3 % / 0.5 % |
| 41910382_supplement1 p66 (unmapped), 34449183_supplement1 p374 (glyph numbers) | the PDF's own faults | unchanged |

- 7.28 also clears r8's residue that the 0.20 decode could not: the scanner
  manual `30883058_supplement1` (21 pages) and AMIE-Mx p20 hold no fused page.
- **r8's fused-word repair does nothing on 7.28.** Since 7.25 (docling-parse
  PR #437) a run's gaps are judged in em of the run's own letter spacing, so
  the `DecodeConfig` space factors no longer move them (the config does reach
  the C++ decoder). On the test's synthetic Helvetica page 7.28 joins words up
  to 0.129 em apart and separates them from 0.130 em (7.20 by default: up to
  0.125 em, measured in coarser steps).
  pdfium is no fallback: it also misses many of these spaces
  ("inpatientswithheart").
- **The glyphs say where the words are.** In the runs of 41811324 p2, p4 and
  29297076 p3, the gap between two glyphs at a word's end is 0.107-0.145 of
  the line's height; inside a word it is at most -0.003 (glyph boxes
  overlap). The test's char-gap measurement: `$S/parser-upgrade/char_gaps.py`
  in the session's scratch (not kept).

**Decision (plan §7 step 4, "on is better -> keep and adapt"):** upgrade;
keep the repair, rebuilt on the glyph gaps; remove the look-alike part and
its pdfium per-page read (7.28 reads those fonts right); keep the check.

**What r9's repair does** (`docling/utils/parser_repair.py`): a page with 3+
runs of 18+ letters is decoded again with its glyphs (the backend keeps no
glyph cells: they are materialized only for `text_cell_unit == CHAR`), and on
each line holding such a run, a gap between two glyphs wider than 0.06 of the
line's height with no space there becomes one; word cells on that line are
cut at the gap. Letters never change. Guards as r8 (characters the same
within 0.5 %, runs at least halved, one-letter share up at most 1 point).
Taking every gap of such a line, not only those inside the runs, also
separates "(LBBB).It", "12months", "P2Y12inhibitors" with no rise in
one-letter words. Cost: 0.1-0.7 s per fused page.

Measured on page cells (fused runs before -> after, letters always the same):
41811324 p2 11 -> 0, p7 6 -> 1; 31237645 p8 14 -> 1; 29297076 p2 6 -> 1; the
synthetic page 5 -> 0. Left alone: 38760584 p7 ("electrophysiological",
Czech names; the guard refuses), 41849741_supplement1 p47 (German compounds,
real words; no gap).

**Four PDFs converted four ways** (picture descriptions off, everything else
default; `amir-batch`):

| PDF | r8 on 7.20 | 7.28, repair off | 7.28, r8 repair | r9 |
|---|---|---|---|---|
| 41811324 (JAMA, 9 p) | ok, recall 0.981, respaced 6 p | 4 issues (fused p2, p3, p7), recall 0.978 | same as off (respaced none) | ok, recall 0.985, respaced p2-p4, p7 |
| 38760584 (25 p) | 1 issue (p8 recall 0.92), recall 0.991, 3,726 letters replaced | same issue, 0.991, nothing to repair | same | same |
| 29297076_supplement2 (352 p, r6 glyph order, 176 tables) | 25 issues, recall 0.974, 19 flagged p, 76 low-recall tables | 14 issues, 0.991, 8 flagged p (all among the 19), 16 low-recall tables | same | same; ~2 s/p in all |
| 36477458 (NEJM control, 11 p) | ok, 0.9908 | ok, 0.9915 | same | same |

A word diff of the text by page (document.json) shows 7.28 reading better
beyond the two faults: words 7.20 split ("I mplantation", "o f", "( n",
"L VEF", "42 ,"), a figure label 7.20 garbled ("phsng en n an em w-em" ->
"Sphere-9(TM) with Affera(TM) Mapping and Ablation System"), fused text r8
never touched ("JAMACardiology", "Atotal", 41811324 p6). Text that seemed
lost on 41811324 p3/p5 is there, in another place of the reading order. Left:
"bundlebranch" (a join across a line break, in r8 too).

**Tests.** Engine suite on 7.28: the fault test
(`test_docling_parse_runs_the_words_of_tight_text_together`) still passes (the
fault is there); r8's re-decode tests failed and were rewritten for the glyph
gaps (a long word set whole as control); the look-alike repair test went.
Upstream: `test_e2e_conversion` and `test_interfaces` compare with 7.20's
output; their PDF groundtruth was regenerated and reviewed by word diff
(mostly spacing 7.28 gets right; not better: a line of U+FFFD in
`redp5110_sampled`, underscores lost in a file name of `2305.03393v1`, the
Arabic and Persian samples reordered by 7.25's right-to-left fix).
`test_e2e_ocr_conversion` fails on both versions: `tesserocr` is not
installed.

**Also in r9:** `public_source_path` keeps a path given under the current
directory as given (worktree batches, §8); every bundle gets
`provenance.html` and `methods.md` (`docling/engines/provenance.py`).

**Next** (unchanged from §7 steps 5 and 7): report the fused-words residue
upstream (draft: `.claude/issues-with-docling/docling-parse-fused-words-justified-text.md`);
fonts whose codes are the embedded font's glyph numbers, through the font's
`cmap`. Remove the repair when a docling-parse release separates these
words: the fault test above then fails. Reconversion: the bundles r8
repaired or flagged first (they gain the most), then the rest when convenient
(7.28 changes normal pages too, for the better on the four measured).
