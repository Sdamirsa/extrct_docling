# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Which pages of which bundles the parser repair changes (or would).

    uv run --no-sync python scripts/text_quality/inspect_parser_faults.py \
        <report.jsonl> <output folder>:<source folder> [...]

Each bundle's source PDF (found by its hash in the source folder or in the
output's ``_converted`` folder) is decoded by the installed docling-parse as
the engine decodes it, and each page's text lines are judged by the rules of
``docling.utils.parser_repair``: fused words (decoded again with the repair's
space factor, kept or refused) and look-alike letters (pdfium's characters
paired by place: pages with letters repaired; cells that keep a letter of
the block, real ones like "ł" included). Pages that
``docling.utils.text_layer`` reads through their fonts (r6) are left out, as
in the engine. The report gets one line per bundle and is resumed when run
again; bundles with something found are printed.

On another docling-parse (an upgrade), the same run says whether the faults
are still there: no page should need respacing or hold look-alikes.
See ``.claude/reference/quality/2026-11-25-parser-faults-and-upgrade-plan.md``.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

from docling_parse.pdf_parser import DoclingPdfParser

from docling.utils.parser_repair import (
    LOOKALIKE,
    Respacer,
    letters_from_pdfium,
    lookalike_letters,
    needs_respacing,
    respacing_holds,
    spacing,
)
from docling.utils.text_layer import read_pages, read_pdf


def _pdfs_by_hash(out_dir: Path, src_dir: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for base in (src_dir, out_dir / "_converted"):
        if base.is_dir():
            for pdf in sorted(base.rglob("*.pdf")):
                found.setdefault(hashlib.sha256(pdf.read_bytes()).hexdigest(), pdf)
    return found


def _inspect(pdf: Path) -> dict:
    row: dict = {
        "respaced": [],
        "respacing_refused": [],
        "letter_pages": {},
        "letter_cells_unpaired": 0,
    }
    r6_pages = set(read_pdf(pdf))
    document = DoclingPdfParser().load(path_or_stream=pdf, lazy=True)
    respacer: Respacer | None = None
    try:
        for page_no in range(1, document.number_of_pages() + 1):
            if page_no in r6_pages:
                continue
            page = document.get_page(page_no)
            cells = page.textline_cells
            before = spacing(cell.text for cell in cells)
            if needs_respacing(before):
                respacer = respacer or Respacer(pdf)
                after = spacing(c.text for c in respacer.page(page_no).textline_cells)
                kept = row["respaced" if respacing_holds(before, after) else "respacing_refused"]
                kept.append(
                    [
                        page_no,
                        before.fused,
                        after.fused,
                        round(after.one_letter_share - before.one_letter_share, 4),
                    ]
                )
            found = lookalike_letters(cell.text for cell in cells)
            if found:
                layer = read_pages(pdf, [page_no])[page_no]
                repaired = 0
                for cell in cells:
                    if not LOOKALIKE.search(cell.text):
                        continue
                    cell.to_top_left_origin(page.dimension.height)
                    pdfium, _ = layer.read_box(cell.rect.to_bounding_box())
                    text, replaced = letters_from_pdfium(cell.text, pdfium)
                    repaired += replaced
                    if LOOKALIKE.search(text):
                        row["letter_cells_unpaired"] += 1
                if repaired:
                    row["letter_pages"][page_no] = [found, repaired]
    finally:
        document.unload()
        if respacer is not None:
            respacer.close()
    return row


def main(report: Path, pairs: list[str]) -> None:
    started = time.time()
    done = set()
    if report.is_file():
        done = {
            json.loads(line)["bundle_path"]
            for line in report.read_text().splitlines()
            if line.strip()
        }
    with report.open("a") as out:
        for pair in pairs:
            out_dir, src_dir = (Path(part) for part in pair.split(":"))
            by_hash = _pdfs_by_hash(out_dir, src_dir)
            for bundle in sorted(p.parent for p in out_dir.glob("*/run.json")):
                if str(bundle) in done:
                    continue
                run = json.loads((bundle / "run.json").read_text())
                pdf = by_hash.get(run["source"]["binary_hash"])
                row = {"bundle_path": str(bundle), "set": out_dir.name, "bundle": bundle.name}
                row |= {"error": "source PDF not found"} if pdf is None else _inspect(pdf)
                out.write(json.dumps(row) + "\n")
                out.flush()
                if row.get("respaced") or row.get("respacing_refused") or row.get("letter_pages"):
                    print(
                        f"{out_dir.name}/{bundle.name}: respaced "
                        f"{[p[0] for p in row['respaced']]}, refused "
                        f"{[p[0] for p in row['respacing_refused']]}, letter pages "
                        f"{row['letter_pages']}, unpaired cells {row['letter_cells_unpaired']}",
                        flush=True,
                    )
    print(f"done in {time.time() - started:.0f} s")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
