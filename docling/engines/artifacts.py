# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Persist DoclingDocument nodes + extracted images to per-PDF artifact folders.

The artifact writer turns a single :class:`ConversionResult` into a directory
of inspectable, agent-readable files:

* ``document.json`` — full :class:`DoclingDocument` serialisation.
* ``nodes.jsonl`` — one JSON object per node from ``iterate_items()`` with
  the item's serialised fields plus ``_kind``, ``_level`` and (for
  pictures/tables) ``image_path`` pointing at the extracted PNG.
* ``images/picture_NNN.png`` / ``images/table_NNN.png`` — image crops from
  :class:`PictureItem` / :class:`TableItem` ``get_image()``. ``NNN`` is the
  item's 1-based position among the pictures (tables) of ``iterate_items()``,
  so a picture without an image leaves a gap: match crops to items with
  :func:`crops_by_self_ref`, not by list position.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from docling_core.types.doc import DoclingDocument, NodeItem, PictureItem, TableItem

if TYPE_CHECKING:
    from docling.datamodel.document import ConversionResult

_log = logging.getLogger(__name__)

_DOCUMENT_JSON_FILENAME = "document.json"
_NODES_FILENAME = "nodes.jsonl"
IMAGES_SUBDIR = "images"


class ArtifactsError(RuntimeError):
    """Raised when artifact extraction cannot complete."""


@dataclass
class ArtifactPaths:
    """Paths to artifacts written by :func:`write_artifacts`."""

    document_json: Path
    nodes_jsonl: Path
    picture_images: list[Path] = field(default_factory=list)
    table_images: list[Path] = field(default_factory=list)


def write_artifacts(result: ConversionResult, pdf_dir: Path) -> ArtifactPaths:
    """Persist the structured outputs of a single PDF conversion.

    The image-extraction step requires the pipeline to have generated page
    images (for tables) and picture images (for figures). The PdfEngine sets
    those flags automatically when ``save_artifacts=True``.
    """
    if result.document is None:
        raise ArtifactsError("ConversionResult has no document.")

    pdf_dir.mkdir(parents=True, exist_ok=True)
    images_dir = pdf_dir / IMAGES_SUBDIR
    images_dir.mkdir(exist_ok=True)

    document_json = pdf_dir / _DOCUMENT_JSON_FILENAME
    result.document.save_as_json(document_json)

    nodes_jsonl = pdf_dir / _NODES_FILENAME
    picture_images: list[Path] = []
    table_images: list[Path] = []
    stems = {item.self_ref: stem for item, stem in _crop_stems(result.document)}

    with nodes_jsonl.open("w", encoding="utf-8") as fh:
        for item, level in result.document.iterate_items():
            node = _node_to_dict(item, level)

            stem = stems.get(item.self_ref)
            if stem is not None:
                img_path = _save_item_image(item, result.document, images_dir, stem)
                if img_path is not None:
                    node["image_path"] = str(img_path.relative_to(pdf_dir))
                    if isinstance(item, PictureItem):
                        picture_images.append(img_path)
                    else:
                        table_images.append(img_path)

            fh.write(json.dumps(node, ensure_ascii=False) + "\n")

    _log.info(
        "Artifacts written: %s (%d pictures, %d tables)",
        pdf_dir,
        len(picture_images),
        len(table_images),
    )

    return ArtifactPaths(
        document_json=document_json,
        nodes_jsonl=nodes_jsonl,
        picture_images=picture_images,
        table_images=table_images,
    )


def crop_stem(kind: Literal["picture", "table"], position: int) -> str:
    """File stem of the crop of the *position*-th (0-based) picture or table
    of ``iterate_items()``: ``picture_001`` for the first picture."""
    return f"{kind}_{position + 1:03d}"


def crops_by_self_ref(doc: DoclingDocument, crops: list[Path]) -> dict[str, Path]:
    """Match crops written by :func:`write_artifacts` (pictures, tables or
    both) to the ``self_ref`` of their item."""
    by_stem = {path.stem: path for path in crops}
    matched: dict[str, Path] = {}
    for item, stem in _crop_stems(doc):
        path = by_stem.get(stem)
        if path is not None:
            matched[item.self_ref] = path
    return matched


def _crop_stems(doc: DoclingDocument) -> Iterator[tuple[PictureItem | TableItem, str]]:
    pictures = tables = 0
    for item, _level in doc.iterate_items():
        if isinstance(item, PictureItem):
            yield item, crop_stem("picture", pictures)
            pictures += 1
        elif isinstance(item, TableItem):
            yield item, crop_stem("table", tables)
            tables += 1


def _node_to_dict(item: NodeItem, level: int) -> dict:
    """Serialise a document item to a JSON-friendly dict.

    The ``image`` field (when present) is excluded — it carries an inlined
    base64 data URI that would bloat the JSONL; the extracted PNG on disk is
    referenced via ``image_path`` instead.
    """
    dumped = item.model_dump(mode="json", exclude={"image"})
    dumped["_kind"] = type(item).__name__
    dumped["_level"] = level
    return dumped


def _save_item_image(item, doc, images_dir: Path, stem: str) -> Path | None:
    """Extract an item's image and write it as ``<stem>.png``."""
    try:
        image = item.get_image(doc)
    except Exception as exc:
        _log.warning("get_image failed for %s: %s", stem, exc)
        return None
    if image is None:
        return None
    target = images_dir / f"{stem}.png"
    image.save(target, format="PNG")
    return target
