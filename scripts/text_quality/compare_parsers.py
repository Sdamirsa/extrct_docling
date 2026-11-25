# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Docling-parse's own text lines on chosen pages, scored: for comparing two
docling-parse versions (run it in each environment) and its space settings.

    uv run --no-sync python scripts/text_quality/compare_parsers.py \
        [--words <word list>] [--corpus <bundles folder>] <pdf>:<page>[:<tag>] [...]

Needs only docling_parse, so a throwaway environment with another version
runs it (``uv venv <dir>; uv pip install --python <dir>/bin/python
docling-parse==<version>``). Per page and setting: words, fused (share of
tokens of 18+ letters), one-letter tokens (other than a and I: a sign of
words split), share of 3+ letter tokens in the vocabulary (the word list,
default ``/usr/share/dict/american-english``, plus words seen 3+ times in
the corpus's markdown), look-alike letters (Latin Extended-A/B).
Measured with it: ``.claude/reference/quality/2026-11-25-parser-faults-and-upgrade-plan.md``.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from docling_parse.pdf_parser import DecodeConfig, DoclingPdfParser

LOOKALIKE = re.compile("[\u0100-\u024f]")
WORD = re.compile(r"[A-Za-z]+")
SETTINGS: dict[str, dict[str, float]] = {
    "default": {},
    "space 0.20": {
        "line_space_width_factor_for_merge_with_space": 0.20,
        "word_space_width_factor_for_merge": 0.20,
    },
    "space 0.10": {
        "line_space_width_factor_for_merge_with_space": 0.10,
        "word_space_width_factor_for_merge": 0.10,
    },
}


def vocabulary(words: Path | None, corpus: Path | None) -> set[str]:
    known: set[str] = set()
    if words is not None and words.is_file():
        known = {w.strip().lower() for w in words.read_text().splitlines() if w.strip().isalpha()}
    if corpus is not None:
        seen: Counter[str] = Counter()
        for md in corpus.glob("*/*.md"):
            seen.update(w.lower() for w in WORD.findall(md.read_text()) if len(w) < 18)
        known |= {w for w, n in seen.items() if n >= 3}
    return known


def score(text: str, known: set[str]) -> str:
    words = WORD.findall(text)
    if not words:
        return "no words"
    fused = sum(len(w) >= 18 for w in words) / len(words)
    single = sum(len(w) == 1 and w not in "aAI" for w in words) / len(words)
    longer = [w for w in words if len(w) >= 3]
    share = sum(w.lower() in known for w in longer) / max(len(longer), 1)
    return (
        f"{len(words):5d} words, fused {fused:5.1%}, one-letter {single:5.1%}, "
        f"vocabulary {share:5.1%}, look-alikes {len(LOOKALIKE.findall(text))}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--words", type=Path, default=Path("/usr/share/dict/american-english"))
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("pages", nargs="+")
    args = parser.parse_args()
    known = vocabulary(args.words, args.corpus)
    print("docling-parse", version("docling-parse"))
    for arg in args.pages:
        parts = arg.split(":")
        pdf, page_no = parts[0], int(parts[1])
        print(f"\n{Path(pdf).name} p{page_no} {parts[2] if len(parts) > 2 else ''}")
        for name, settings in SETTINGS.items():
            document = DoclingPdfParser().load(
                path_or_stream=pdf, decode_config=DecodeConfig(**settings)
            )
            cells = document.get_page(page_no).textline_cells
            print(f"   {name:10s} {score(chr(10).join(c.text for c in cells), known)}")
            document.unload()


if __name__ == "__main__":
    main()
