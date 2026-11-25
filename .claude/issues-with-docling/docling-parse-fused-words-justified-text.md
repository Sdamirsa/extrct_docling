# docling-parse joins the words of tightly justified text set without space characters

| | |
|---|---|
| **Severity** | Medium: the text is complete, but words run together ("studiesandsmallrandomizedclinicaltrials"), so keyword search, embeddings, quoting and the check's page recall suffer |
| **Status** | Open upstream; worked around in this fork since r8 (rebuilt for 7.28 in r9: `docling/utils/parser_repair.py`, tested, temporary). Report below drafted 2026-11-25, not filed |
| **First-seen** | 2026-11-24 on docling-parse 7.20.0 (JAMA papers of the nirct sets); still there on 7.28.0, 2026-11-25 |
| **Affects** | docling-parse's decision where a space goes between the glyphs of a run (line and word cells), as Docling's default PDF backend gives them; docling-parse 7.28.0 with docling-core 2.99.0 (7.20.0 for comparison), Python 3.13, Linux aarch64 |
| **Upstream issue** | _not filed_ (docling-project/docling-parse) |

## Symptom

Journals that set justified text by moving the words apart (TJ shifts)
instead of writing space characters come out with some words joined. On
7.28.0 the line cells of one JAMA paper (doi:10.1001/jamacardio.2026.0101)
hold "tionanddeathinpatientswithheartfailurewithreducedejection" on p2. 7.28
joins fewer words than 7.20 (that page: 1.3 % of the words in runs of 18 or
more letters, 4.6 % on 7.20), but not all.

Since 7.25 (docling-parse PR #437) the gaps of a run are judged in em of the
run's own letter spacing, so the `DecodeConfig` space factors
(`line_space_width_factor_for_merge_with_space`,
`word_space_width_factor_for_merge`) no longer change the result. On 7.20 a
second decode with both at 0.20 separated these words (the fork's r8
repair); on 7.28 it does nothing.

## Reproducer

`tests/test_engines/test_parser_repair.py`: `_tight_pdf()` builds the page,
`test_docling_parse_runs_the_words_of_tight_text_together` asserts the fault
(it fails once docling-parse separates these words). The page: one
612 × 792 pt page, the standard Type1 font Helvetica (`WinAnsiEncoding`,
not embedded) at 10 pt, leading 14 pt, five lines of ordinary English, each
line one `TJ` array whose words are strings separated by a shift of `-110`
(thousandths of an em), with no space character anywhere in those lines.

Measured on 7.28.0 (2026-11-25, same page, the shift varied, default
`DecodeConfig`), text of the first line cell:

| Shift between words (1/1000 em) | 7.28.0 line cell |
|---|---|
| 100, 110, 125, 128 | `studiesandsmallrandomizedclinicaltrialssuggestthat` |
| 130, 140, 150, 200 | `studies and small randomized clinical trials suggest that` |

At 110 and 125, both space factors at 0.20 or at 0.05 give the same joined
line. 7.20.0 with its default settings joined the same page's words up to
0.125 em too (measured 2026-11-24); with both factors at 0.20 it separated
them from 0.100 em.

## What the glyphs say

Decoded with glyph cells, the runs of the fused pages measured
(doi:10.1001/jamacardio.2026.0101 p2 and p4, doi:10.1001/jama.2017.19132
p3) have a gap between two glyphs at a word's end of 0.107 to 0.145 of the
line's height; inside a word the gap is at most -0.003 (the glyph boxes
overlap). Real long words printed as one ("electrophysiological", German
compounds in a supplement) have no such gap.

## Workaround (tested, in the fork)

`docling/utils/parser_repair.py`, switch `PdfPipelineOptions.repair_parser_text`
(default on): a page with 3 or more runs of 18 or more letters is decoded
again with its glyphs (the backend keeps no glyph cells), and on each line
holding such a run a gap between two glyphs wider than 0.06 of the line's
height, with no space there, becomes a space; word cells are cut there;
letters never change. Kept only when the runs at least halve, the share of
one-letter words rises by at most 1 point and the characters stay the same
within 0.5 %. Recorded in `run.json` → `quality.parser_repair.respaced_pages`
(warning `parser_text_repaired`). Measured on the first paper below (9
pages): on 7.28 without the repair the bundle check names fused pages p2, p3
and p7 (4 issues, document recall 0.978); with it the check is ok (recall
0.985), pages p2, p3, p4 and p7 respaced. Remove the workaround when a
docling-parse release separates these words: the fault test then fails.

## Affected public papers

Fused runs (18+ letters) in docling-parse 7.28.0's line cells, measured
2026-11-25; all three are JAMA Network papers:

| Paper | Pages, runs on 7.28.0 | Example run (7.28.0) |
|---|---|---|
| doi:10.1001/jamacardio.2026.0101 | p2 11 (1.3 % of 873 words), p3 5, p4 3, p7 6 | "tionanddeathinpatientswithheartfailurewithreducedejection" |
| doi:10.1001/jama.2019.8146 | p8 14 (of 1,188 words) | "monotherapyisinadequatetopreventrecurrentischemicevents" |
| doi:10.1001/jama.2017.19132 | p2 6, p3 3 | "manentpacemakerimplantationisanotherimportantlimitation" |

A run of 18+ letters can be a real word ("electrocardiographic"); the counts
include those.

## Issue text

**Title:** Words of tightly justified text without space characters are
joined (7.28.0; `DecodeConfig` space factors no longer help since 7.25)

**Versions:** docling-parse 7.28.0, docling-core 2.99.0, Python 3.13, Linux
aarch64 (7.20.0 for comparison).

**What happens:** In PDFs that justify text by TJ shifts between words and
write no space characters (JAMA Network papers, e.g.
doi:10.1001/jamacardio.2026.0101, doi:10.1001/jama.2019.8146,
doi:10.1001/jama.2017.19132), some words come out joined in the line and
word cells: "tionanddeathinpatientswithheartfailurewithreducedejection".
7.28.0 joins fewer than 7.20.0 (1.3 % against 4.6 % of the words on one
page), but since 7.25 (#437) a run's gaps are judged in em of the run's own
letter spacing, and `line_space_width_factor_for_merge_with_space` /
`word_space_width_factor_for_merge` no longer change the result (0.20 and
0.05 give the same text). On 7.20.0, factor 0.20 separated these words.

**Minimal reproducer:** a one-page PDF, Helvetica (standard Type1,
WinAnsiEncoding) 10 pt, each line one TJ array of words with `-110` between
them and no space character:

```python
from pathlib import Path

from docling_parse.pdf_parser import DoclingPdfParser

def tight_pdf(shift: int) -> bytes:
    line = "studies and small randomized clinical trials suggest that"
    shown = "[" + f" -{shift} ".join(f"({w})" for w in line.split()) + "] TJ"
    stream = f"BT /F 10 Tf 14 TL 72 720 Td\n{shown}\nET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out, offsets = bytearray(b"%PDF-1.7\n"), []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)

for shift in (110, 125, 128, 130, 150):
    pdf = Path(f"tight_{shift}.pdf")
    pdf.write_bytes(tight_pdf(shift))
    for _, page in DoclingPdfParser().load(path_or_stream=pdf).iterate_pages():
        print(shift, [cell.text for cell in page.textline_cells])
```

7.28.0 returns `studiesandsmallrandomizedclinicaltrialssuggestthat` up to a
shift of 128 and `studies and small randomized clinical trials suggest that`
from 130 (measured at 100, 110, 125, 128, 130, 140, 150, 200).

**What the glyphs show:** on the real pages the gap between two glyphs at a
word's end is 0.107 to 0.145 of the line's height, inside a word at most
-0.003 (boxes overlap). Splitting a line that holds a long run at gaps wider
than 0.06 of the line's height separates these words and leaves real long
words ("electrophysiological") whole.

**Expected:** a gap between glyphs that is clearly wider than the gaps inside
the run's words (or a `DecodeConfig` setting that still moves the threshold)
gives a space in the line and word cells.
