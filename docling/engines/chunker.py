# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Chunked text view of a converted PDF, written as ``chunks.jsonl``.

Wraps :class:`docling_core.transforms.chunker.HybridChunker` so an agent or
RAG pipeline can consume per-PDF chunks without rebuilding the chunker
configuration each time. The output sits next to ``nodes.jsonl`` and
``document.json`` in the per-PDF output folder.

Each line in ``chunks.jsonl`` is one chunk:

```json
{
  "index": 0,
  "text": "1. Introduction\\n...",
  "token_count": 487,
  "headings": ["1. Introduction"],
  "page_nos": [2, 3],
  "self_refs": ["#/texts/12", "#/texts/13"]
}
```

The text follows the markdown policy of :mod:`docling.engines.serializers`
(marked VLM descriptions, a table's PDF text after it); chunks without text
are not written.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from docling_core.transforms.chunker import DocChunk, HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

from docling.engines.serializers import build_serializer_provider

if TYPE_CHECKING:
    from docling_core.types.doc import DoclingDocument

    from docling.datamodel.document import ConversionResult

_log = logging.getLogger(__name__)

_CHUNKS_FILENAME = "chunks.jsonl"

DEFAULT_TOKENIZER = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MAX_TOKENS = 512  # matches MiniLM model_max_length; bump alongside tokenizer.


class ChunkerError(RuntimeError):
    """Raised when chunking cannot complete."""


@dataclass
class ChunkPaths:
    """Path bundle returned by :func:`write_chunks`."""

    chunks_jsonl: Path
    chunk_count: int
    tokenizer_repo: str
    max_tokens: int


def write_chunks(
    result: ConversionResult,
    pdf_dir: Path,
    *,
    tokenizer_repo: str = DEFAULT_TOKENIZER,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    merge_peers: bool = True,
) -> ChunkPaths:
    """Run HybridChunker over the DoclingDocument and persist ``chunks.jsonl``."""
    if result.document is None:
        raise ChunkerError("ConversionResult has no document.")
    return write_document_chunks(
        result.document,
        pdf_dir,
        tokenizer_repo=tokenizer_repo,
        max_tokens=max_tokens,
        merge_peers=merge_peers,
    )


def write_document_chunks(
    document: DoclingDocument,
    pdf_dir: Path,
    *,
    tokenizer_repo: str = DEFAULT_TOKENIZER,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    merge_peers: bool = True,
) -> ChunkPaths:
    """``chunks.jsonl`` of *document*: at conversion, and again by a step
    that changes the document of a finished bundle (figure-to-data)."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    target = pdf_dir / _CHUNKS_FILENAME

    tokenizer = HuggingFaceTokenizer.from_pretrained(
        model_name=tokenizer_repo, max_tokens=max_tokens
    )
    chunker = HybridChunker(
        tokenizer=tokenizer,
        merge_peers=merge_peers,
        serializer_provider=build_serializer_provider(),
    )

    rows: list[dict] = []
    dropped = 0
    for chunk in chunker.chunk(dl_doc=document):
        doc_chunk = DocChunk.model_validate(chunk)
        # A caption split off its table (to fit the token budget) serializes
        # to nothing: the table's own chunk renders it.
        if not doc_chunk.text.strip():
            dropped += 1
            continue
        rows.append(_chunk_to_dict(len(rows), doc_chunk, tokenizer))
    with target.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    if dropped:
        _log.info("Dropped %d chunk(s) without text (headings only)", dropped)
    _log.info(
        "Chunks written: %s (%d chunks, tokenizer=%s, max_tokens=%d)",
        target,
        len(rows),
        tokenizer_repo,
        max_tokens,
    )
    return ChunkPaths(
        chunks_jsonl=target,
        chunk_count=len(rows),
        tokenizer_repo=tokenizer_repo,
        max_tokens=max_tokens,
    )


def _chunk_to_dict(
    index: int, chunk: DocChunk, tokenizer: HuggingFaceTokenizer
) -> dict:
    """Serialise a HybridChunker chunk for JSONL."""
    meta = chunk.meta
    return {
        "index": index,
        "text": chunk.text,
        "token_count": tokenizer.count_tokens(text=chunk.text),
        "headings": meta.headings or [],
        # DocMeta.captions is deprecated and never set by HybridChunker; the
        # captions are in the chunk text. The key stays for existing readers.
        "captions": [],
        "page_nos": sorted(
            {prov.page_no for item in meta.doc_items for prov in item.prov}
        ),
        "self_refs": [item.self_ref for item in meta.doc_items],
    }
