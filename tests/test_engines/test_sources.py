# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Inputs of ``amir-batch`` that are not PDF files: a Word file becomes a
PDF through Docling's own LibreOffice helper, a ZIP archive stands for the
PDF and Word files inside it."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pypdfium2
import pytest

from docling.backend.docx.drawingml.utils import get_docx_to_pdf_converter
from docling.engines.sources import SourceError, expand_source
from docling.utils.utils import create_file_hash

from .test_cli import FIXTURE_PDF, _batch, needs_fixture

needs_libreoffice = pytest.mark.skipif(
    get_docx_to_pdf_converter() is None, reason="LibreOffice is not installed"
)


@needs_fixture
def test_an_archive_stands_for_the_pdf_and_word_files_inside_it(tmp_path: Path) -> None:
    """Members keep their name behind the archive's, lose their folders (a
    path in an archive cannot leave the work folder), and two with one name
    are numbered. Hidden files and other kinds are left out."""
    pdf = FIXTURE_PDF.read_bytes()
    archive = tmp_path / "12345_supplements.zip"
    with zipfile.ZipFile(archive, "w") as made:
        made.writestr("a/Protocol.pdf", pdf)
        made.writestr("b/Protocol.pdf", pdf)
        made.writestr("../../escape.pdf", pdf)
        made.writestr("__MACOSX/a/._Protocol.pdf", b"x")
        made.writestr(".hidden.pdf", pdf)
        made.writestr("table.csv", "a,b\n")
    work = tmp_path / "work"

    sources = expand_source(archive, work)

    assert sorted(s.pdf.relative_to(work).as_posix() for s in sources) == [
        "12345_supplements/12345_supplements__Protocol.pdf",
        "12345_supplements/12345_supplements__Protocol_3.pdf",
        "12345_supplements/12345_supplements__escape.pdf",
    ]
    assert not (tmp_path / "escape.pdf").exists()
    for source in sources:
        origin = source.converted_from
        assert origin is not None and source.pair_stem == "12345_supplements"
        assert (origin.archive, origin.converter) == ("12345_supplements.zip", None)
        assert origin.binary_hash == create_file_hash(FIXTURE_PDF)
        assert source.pdf.read_bytes() == pdf

    with pytest.raises(SourceError, match="not a readable ZIP archive"):
        broken = tmp_path / "broken.zip"
        broken.write_bytes(b"not a zip")
        expand_source(broken, work)
    with pytest.raises(SourceError, match="not a PDF, a Word file"):
        expand_source(tmp_path / "notes.txt", work)


@needs_libreoffice
def test_a_word_file_is_turned_into_a_pdf_once(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("Statistical analysis plan", level=1)
    document.add_paragraph("The primary outcome is all-cause mortality at 90 days.")
    word = tmp_path / "12345_supplement1.docx"
    document.save(str(word))
    work = tmp_path / "work"

    (source,) = expand_source(word, work)

    assert source.pdf == work / "12345_supplement1.pdf"
    page = pypdfium2.PdfDocument(str(source.pdf))[0]
    assert "all-cause mortality at 90 days" in page.get_textpage().get_text_range()
    origin = source.converted_from
    assert origin is not None and origin.file_name == "12345_supplement1.docx"
    assert origin.binary_hash == create_file_hash(word)
    assert "libreoffice" in (origin.converter or "")

    made_at = source.pdf.stat().st_mtime_ns
    (again,) = expand_source(word, work)
    assert again.pdf.stat().st_mtime_ns == made_at


@needs_fixture
def test_a_batch_takes_archives_and_pairs_their_files_with_the_manuscript(
    tmp_path: Path,
) -> None:
    """The files of ``<name>_supplements.zip`` are converted like any PDF,
    recorded with where they came from, paired with ``<name>.pdf`` as its
    supplements, and skipped by a second batch. A file the batch cannot
    take is named and left."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    (inputs / "12345.pdf").write_bytes(FIXTURE_PDF.read_bytes())
    with zipfile.ZipFile(inputs / "12345_supplements.zip", "w") as made:
        made.write(FIXTURE_PDF, "Appendix.pdf")
    (inputs / "FILES.csv").write_text("pmid,file\n", encoding="utf-8")
    out = tmp_path / "out"

    result = _batch(str(inputs), "-o", str(out))

    assert result.exit_code == 0, result.output
    assert "Appendix.pdf in 12345_supplements.zip" in result.output
    member = out / "12345_supplements__Appendix"
    record = json.loads((member / "run.json").read_text(encoding="utf-8"))
    assert record["source"]["converted_from"] == {
        "file_name": "Appendix.pdf",
        "file_size_bytes": FIXTURE_PDF.stat().st_size,
        "binary_hash": create_file_hash(FIXTURE_PDF),
        "archive": "12345_supplements.zip",
    }
    assert record["document_role"] == "supplement"
    assert [(r["role"], r["bundle"]) for r in record["related"]] == [
        ("manuscript", "12345")
    ]
    manuscript = json.loads((out / "12345" / "run.json").read_text(encoding="utf-8"))
    assert "converted_from" not in manuscript["source"]
    assert [r["bundle"] for r in manuscript["related"]] == [
        "12345_supplements__Appendix"
    ]

    second = _batch(str(inputs), "-o", str(out))
    assert second.exit_code == 0 and second.output.count("SKIPPED") == 2
