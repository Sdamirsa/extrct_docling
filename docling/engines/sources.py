# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Inputs of ``amir-batch`` that are not PDF files.

The engine converts PDFs: a bundle has pages, boxes on them, a page viewer,
checks against the PDF's own text and figure data read from the PDF. A
Word file is therefore turned into a PDF first and then goes through the
same pipeline, so its bundle is like any other. The conversion is Docling's
own: the helper its DOCX backend renders drawings with (LibreOffice in a
throwaway profile, macros and link updates off, a timeout). A ZIP archive,
the form in which journals hand out supplements, stands for the PDF and
Word files inside it.

What was made is kept under ``<output dir>/_converted/``: the checks and
the figure-to-data step need the PDF again, and an unchanged source is not
converted twice.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field

from docling.backend.docx.drawingml.utils import get_docx_to_pdf_converter
from docling.utils.utils import create_file_hash

CONVERTED_DIRNAME = "_converted"
OFFICE_SUFFIXES = frozenset({".docx"})
ARCHIVE_SUFFIXES = frozenset({".zip"})
INPUT_SUFFIXES = frozenset({".pdf"}) | OFFICE_SUFFIXES | ARCHIVE_SUFFIXES
CONVERTER = "libreoffice (docling.backend.docx.drawingml.utils)"


class SourceError(RuntimeError):
    """A source file could not be turned into a PDF."""


class ConvertedFrom(BaseModel):
    """``run.json`` → ``source.converted_from``: the file a bundle's PDF was
    made from, when the PDF is not the file the user gave."""

    file_name: str
    file_size_bytes: int
    binary_hash: str = Field(description="Docling's SHA-256 of that file.")
    archive: str | None = Field(
        default=None, description="The ZIP archive the file was taken out of."
    )
    converter: str | None = Field(
        default=None, description="What turned it into a PDF; None for a PDF."
    )


class SourceFile(BaseModel):
    """One document of a batch: the PDF the engine converts."""

    pdf: Path
    converted_from: ConvertedFrom | None = None
    # The name supplements are paired by: for a member of an archive the
    # archive's own ("12345_supplements" for every file inside it).
    pair_stem: str | None = None


def office_to_pdf(source: Path, target: Path) -> None:
    """Write *source* (a Word file) as the PDF *target* with LibreOffice."""
    convert = get_docx_to_pdf_converter()
    if convert is None:
        raise SourceError(
            f"{source.name}: LibreOffice is needed to turn a Word file into a "
            "PDF (install it, or set DOCLING_LIBREOFFICE_CMD)"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        convert(source, target)
    except Exception as exc:
        raise SourceError(f"{source.name}: LibreOffice failed: {exc}") from exc
    if not target.is_file():
        raise SourceError(f"{source.name}: LibreOffice wrote no PDF")


def expand_source(path: Path, work_dir: Path) -> list[SourceFile]:
    """The PDFs *path* stands for: itself, the PDF made from a Word file, or
    the PDF and Word files of an archive. Made files go under *work_dir*."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return [SourceFile(pdf=path)]
    if suffix in OFFICE_SUFFIXES:
        return [_converted(path, work_dir / f"{path.stem}.pdf", file_name=path.name)]
    if suffix in ARCHIVE_SUFFIXES:
        return _archive_members(path, work_dir / path.stem)
    raise SourceError(f"{path.name}: not a PDF, a Word file (.docx) or a ZIP archive")


def _converted(
    source: Path, target: Path, *, file_name: str, archive: str | None = None
) -> SourceFile:
    """*source* as the PDF *target*, made unless it is there and newer."""
    origin = ConvertedFrom(
        file_name=file_name,
        file_size_bytes=source.stat().st_size,
        binary_hash=create_file_hash(source),
        archive=archive,
        converter=CONVERTER,
    )
    if not target.is_file() or target.stat().st_mtime < source.stat().st_mtime:
        office_to_pdf(source, target)
    return SourceFile(pdf=target, converted_from=origin)


def _archive_members(archive: Path, folder: Path) -> list[SourceFile]:
    """The PDF and Word files of *archive*, taken out into *folder* as
    ``<archive stem>__<member name>``. A member's own folders are dropped,
    so a path in the archive cannot leave *folder*; two members that would
    get one name are numbered."""
    wanted = frozenset({".pdf"}) | OFFICE_SUFFIXES
    sources: list[SourceFile] = []
    taken: set[str] = set()
    try:
        opened = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise SourceError(f"{archive.name}: not a readable ZIP archive") from exc
    with opened:
        for member in sorted(opened.infolist(), key=lambda m: m.filename):
            inner = Path(member.filename)
            hidden = inner.name.startswith((".", "~$")) or "__MACOSX" in inner.parts
            if member.is_dir() or hidden or inner.suffix.lower() not in wanted:
                continue
            stem = f"{archive.stem}__{inner.stem}"
            if stem.casefold() in taken:
                stem = f"{stem}_{len(taken) + 1}"
            taken.add(stem.casefold())
            extracted = folder / f"{stem}{inner.suffix.lower()}"
            if not extracted.is_file() or extracted.stat().st_size != member.file_size:
                folder.mkdir(parents=True, exist_ok=True)
                with opened.open(member) as data, extracted.open("wb") as out:
                    shutil.copyfileobj(data, out)
            if extracted.suffix == ".pdf":
                source = SourceFile(
                    pdf=extracted,
                    converted_from=ConvertedFrom(
                        file_name=inner.name,
                        file_size_bytes=member.file_size,
                        binary_hash=create_file_hash(extracted),
                        archive=archive.name,
                    ),
                )
            else:
                source = _converted(
                    extracted,
                    extracted.with_suffix(".pdf"),
                    file_name=inner.name,
                    archive=archive.name,
                )
            source.pair_stem = archive.stem
            sources.append(source)
    return sources
