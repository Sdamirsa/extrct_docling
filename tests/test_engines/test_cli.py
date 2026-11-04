# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for the ``amir-batch`` CLI and the bundle bookkeeping around it."""

from __future__ import annotations

import io
import json
import re
import shutil
from pathlib import Path

import pytest
from click.testing import Result
from rich.console import Console
from typer.testing import CliRunner

from docling.datamodel.base_models import ConversionStatus
from docling.engines import pdf_engine
from docling.engines.cli import (
    RowStatus,
    _collect_pdfs,
    _compare_row,
    _plan_bundles,
    app,
)
from docling.engines.compare_pipelines import (
    ComparisonResult,
    _rename_pdf_dir,
    _render_comparison_md,
)
from docling.engines.html_export import MANIFEST_ID
from docling.engines.pdf_engine import PdfEngine
from docling.engines.schemas import PdfConversionOutput, SourceKind
from docling.utils.utils import create_file_hash

FIXTURE_PDF = Path("tests/data/pdf/sources/2305.03393v1-pg9.pdf")
_NO_MODELS = [
    "--picture-description",
    "off",
    "--no-granite-vision-tables",
    "--no-figure-types",
]
needs_fixture = pytest.mark.skipif(
    not FIXTURE_PDF.exists(), reason=f"fixture {FIXTURE_PDF} not available"
)


def _batch(*args: str, preview: bool = False) -> Result:
    return CliRunner().invoke(
        app,
        [*args, *_NO_MODELS, "--preview" if preview else "--no-preview"],
        env={"COLUMNS": "250"},
    )


def _record(folder: Path, pdf: Path, **source: object) -> None:
    """A run.json in *folder* recording *pdf* as its source."""
    folder.mkdir(parents=True, exist_ok=True)
    recorded = {
        "file_name": pdf.name,
        "file_size_bytes": pdf.stat().st_size,
        "binary_hash": create_file_hash(pdf),
        **source,
    }
    (folder / "run.json").write_text(json.dumps({"source": recorded}), encoding="utf-8")


def _manifest(html_path: Path) -> dict:
    match = re.search(
        rf'<script type="application/json" id="{MANIFEST_ID}">(.*?)</script>',
        html_path.read_text(encoding="utf-8"),
        re.S,
    )
    assert match is not None
    return json.loads(match.group(1))


@needs_fixture
def test_second_batch_skips_the_complete_bundle(tmp_path: Path) -> None:
    """A rerun with the same options leaves a complete bundle alone;
    ``--check-only`` rewrites its check.json, naming the PDF without its
    absolute path; turning the preview on converts it again. The name has an
    upper-case suffix and rich markup in it, which the summary must print as
    is."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    shutil.copyfile(FIXTURE_PDF, inputs / "Scan [b] 2020.PDF")
    out = tmp_path / "out"

    first = _batch(str(inputs), "-o", str(out))
    assert first.exit_code == 0, first.output
    assert "Scan [b] 2020.PDF" in first.output
    pdf_dir = out / "Scan_b_2020"
    run_json = (pdf_dir / "run.json").read_text(encoding="utf-8")
    assert json.loads(run_json)["complete"] is True

    second = _batch(str(inputs), "-o", str(out))
    assert second.exit_code == 0, second.output
    assert "SKIPPED" in second.output
    assert (pdf_dir / "run.json").read_text(encoding="utf-8") == run_json

    (pdf_dir / "check.json").unlink()
    checked = _batch(str(inputs), "-o", str(out), "--check-only")
    assert checked.exit_code == 0, checked.output
    check = json.loads((pdf_dir / "check.json").read_text(encoding="utf-8"))
    assert check["ok"]
    assert check["pdf"] == "Scan [b] 2020.PDF"

    with_preview = _batch(str(inputs), "-o", str(out), preview=True)
    assert with_preview.exit_code == 0, with_preview.output
    assert "reconverting Scan_b_2020: options differ (make_html_preview)" in (
        with_preview.output
    )
    assert "SKIPPED" not in with_preview.output
    assert (pdf_dir / "preview.html").is_file()
    run = json.loads((pdf_dir / "run.json").read_text(encoding="utf-8"))
    assert run["engine_config"]["make_html_preview"] is True
    assert run["source"]["binary_hash"] == create_file_hash(FIXTURE_PDF)


@needs_fixture
def test_check_issues_exit_3_and_a_missing_bundle_exits_1(tmp_path: Path) -> None:
    """A bundle whose check finds issues but that converted cleanly is not a
    failed row: the batch exits 3, skipped or re-checked, so ``&& next``
    can tell it from a failure (exit 1), such as a PDF without a bundle in
    ``--check-only``."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    shutil.copyfile(FIXTURE_PDF, inputs / "paper.pdf")
    out = tmp_path / "out"
    assert _batch(str(inputs), "-o", str(out)).exit_code == 0
    html_path = out / "paper" / "paper.html"
    html_path.write_text(
        re.sub(
            r' data-self-ref="[^"]+"',
            "",
            html_path.read_text(encoding="utf-8"),
            count=1,
        ),
        encoding="utf-8",
    )

    checked = _batch(str(inputs), "-o", str(out), "--check-only")
    assert checked.exit_code == 3, checked.output
    assert "1 issues" in checked.output
    skipped = _batch(str(inputs), "-o", str(out))
    assert skipped.exit_code == 3, skipped.output
    assert "SKIPPED" in skipped.output

    (inputs / "unconverted.pdf").write_bytes(b"%PDF-1.4\n")
    missing = _batch(str(inputs), "-o", str(out), "--check-only")
    assert missing.exit_code == 1, missing.output
    assert "MISSING" in missing.output


@needs_fixture
def test_failed_step_is_recorded_and_fails_the_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The chunker hits a full disk: the bundle still gets its markdown,
    HTML, check.json and a complete run.json listing the error; the chunks
    and the images a previous run left are gone, from the folder and the HTML
    manifest; the row is SUCCESS* and the batch exits 1. The next batch
    converts the PDF again instead of skipping it."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    shutil.copyfile(FIXTURE_PDF, inputs / "paper.pdf")
    out = tmp_path / "out"
    pdf_dir = out / "paper"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "chunks.jsonl").write_text(
        json.dumps({"index": 0, "text": "stale", "self_refs": []}) + "\n",
        encoding="utf-8",
    )
    stale_crop = pdf_dir / "images" / "picture_099.png"
    stale_crop.parent.mkdir()
    stale_crop.write_bytes(b"stale")

    def full_disk(*args: object, **kwargs: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(pdf_engine, "write_chunks", full_disk)

    result = _batch(str(inputs), "-o", str(out))

    assert result.exit_code == 1, result.output
    assert "SUCCESS*" in result.output and "chunker" in result.output
    run = json.loads((pdf_dir / "run.json").read_text(encoding="utf-8"))
    assert run["complete"] is True
    assert run["errors"] == [
        {
            "component": "chunker",
            "message": "OSError: [Errno 28] No space left on device",
        }
    ]
    assert run["output_summary"]["error_count"] == 1
    assert (pdf_dir / "paper.md").read_text(encoding="utf-8").strip()
    assert not (pdf_dir / "chunks.jsonl").exists()
    assert not stale_crop.exists()
    manifest = _manifest(pdf_dir / "paper.html")
    assert manifest["chunks"] == []
    # Embedded before the check ran: the provisional run block.
    assert manifest["run"]["complete"] is False
    assert not json.loads((pdf_dir / "check.json").read_text(encoding="utf-8"))["ok"]

    monkeypatch.undo()
    rerun = _batch(str(inputs), "-o", str(out))

    assert rerun.exit_code == 0, rerun.output
    assert "reconverting paper: previous run had errors" in rerun.output
    assert (
        json.loads((pdf_dir / "run.json").read_text(encoding="utf-8"))["errors"] == []
    )
    assert (pdf_dir / "chunks.jsonl").is_file()


def test_engine_exception_is_retried_and_an_interrupt_ends_the_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = tmp_path / "in"
    inputs.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (inputs / name).write_bytes(b"%PDF-1.4\n")
    calls: list[str] = []

    def convert(self: PdfEngine, source: Path, **kwargs: object) -> None:
        calls.append(source.name)
        if source.name == "a.pdf":
            raise RuntimeError("CUDA out of memory")
        raise KeyboardInterrupt

    monkeypatch.setattr(PdfEngine, "convert", convert)

    result = _batch(str(inputs), "-o", str(tmp_path / "out"), "--retries", "2")

    assert result.exit_code == 130, result.output
    assert calls == ["a.pdf", "a.pdf", "a.pdf", "b.pdf"]
    assert "EXCEPTION" in result.output
    assert "RuntimeError: CUDA out of memory" in result.output


def test_bundle_folders_of_a_batch_never_collide(tmp_path: Path) -> None:
    """Names that sanitise alike, two folders' ``main.pdf`` and an earlier
    batch's bundle of another PDF each keep their own folder; non-ASCII
    names keep their letters."""

    def pdf(rel: str, data: bytes = b"%PDF-1.4\n") -> Path:
        path = tmp_path / "in" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    pdf("a/main.pdf", b"%PDF a")
    b_main = pdf("b/main.pdf", b"%PDF bb")
    for name in ("Smith 2020.pdf", "Smith_2020.pdf", "résumé.pdf", "論文.pdf"):
        pdf(name)
    out = tmp_path / "out"
    (out / "main").mkdir(parents=True)
    (out / "main" / "run.json").write_text(
        json.dumps(
            {
                "source": {
                    "file_name": "main.pdf",
                    "file_size_bytes": b_main.stat().st_size,
                }
            }
        ),
        encoding="utf-8",
    )
    console = Console(file=io.StringIO())
    inputs = [tmp_path / "in", tmp_path / "in" / "a", tmp_path / "in" / "b"]

    plan = _plan_bundles(_collect_pdfs(inputs, console), out, console, compare=False)

    folders = {
        item.path.relative_to(tmp_path / "in").as_posix(): item.pdf_dir.name
        for item in plan
    }
    assert folders == {
        "Smith 2020.pdf": "Smith_2020",
        "Smith_2020.pdf": "Smith_2020_2",
        "a/main.pdf": "main_2",
        "b/main.pdf": "main",
        "résumé.pdf": "résumé",
        "論文.pdf": "論文",
    }
    assert all(item.pdf_dir.parent == out for item in plan)


def test_a_pdf_keeps_its_bundle_folder_across_batches(tmp_path: Path) -> None:
    """An earlier batch put x.pdf in x_2 behind another x.pdf that is gone
    now: x.pdf keeps x_2, though x (an interrupted conversion, no run.json)
    comes first. A bundle of a PDF with the same name and size but other
    bytes is another PDF's. A comparison folder is identified by its
    standard/run.json. A run.json cut off mid-write does not stop the
    planning, and its folder is reused."""

    def pdf(name: str, data: bytes) -> Path:
        path = tmp_path / "in" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    x = pdf("x.pdf", b"%PDF x")
    same = pdf("same.pdf", b"%PDF 1")
    cut = pdf("cut.pdf", b"%PDF cut")
    compared = pdf("cmp.pdf", b"%PDF cmp")
    out = tmp_path / "out"
    (out / "x").mkdir(parents=True)
    _record(out / "x_2", x)
    _record(out / "same", same, binary_hash="0" * 64)
    (out / "cut").mkdir()
    (out / "cut" / "run.json").write_text('{"source": {"file_na', encoding="utf-8")
    _record(out / "cmp" / "standard", compared, file_size_bytes=1)
    console = Console(file=io.StringIO())

    def folders(pdfs: list[Path], *, compare: bool) -> dict[str, str]:
        plan = _plan_bundles(pdfs, out, console, compare=compare)
        return {item.path.name: item.pdf_dir.name for item in plan}

    assert folders([x, same, cut], compare=False) == {
        "x.pdf": "x_2",
        "same.pdf": "same_2",
        "cut.pdf": "cut",
    }
    assert folders([compared], compare=True) == {"cmp.pdf": "cmp_2"}


def test_compare_bundle_move_repoints_every_path(tmp_path: Path) -> None:
    """Moving the standard bundle to ``standard/`` re-points every path of the
    output; comparison.md reads ``standard/<stem>.md``; a failed side fails
    the row."""
    src = tmp_path / "paper" / "paper"
    names = (
        "paper.md",
        "paper.html",
        "run.json",
        "check.json",
        "preview.html",
        "preview.embedded.html",
        "images/picture_001.png",
    )
    files = {name: src / name for name in names}
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Standard title\n", encoding="utf-8")
    standard = PdfConversionOutput(
        status=ConversionStatus.SUCCESS,
        source="paper.pdf",
        source_kind=SourceKind.LOCAL_PATH,
        output_dir=src,
        markdown_path=files["paper.md"],
        html_path=files["paper.html"],
        run_json=files["run.json"],
        check_json=files["check.json"],
        preview_html=files["preview.html"],
        preview_html_embedded=files["preview.embedded.html"],
        picture_images=[files["images/picture_001.png"]],
    )
    target = tmp_path / "paper" / "standard"

    moved = _rename_pdf_dir(standard, target)

    paths = [
        path
        for _name, value in moved
        for path in (value if isinstance(value, list) else [value])
        if isinstance(path, Path)
    ]
    assert len(paths) == len(names) + 1  # + output_dir
    assert all(path.is_relative_to(target) and path.exists() for path in paths)

    failed = PdfConversionOutput(
        status=ConversionStatus.FAILURE,
        source="paper.pdf",
        source_kind=SourceKind.LOCAL_PATH,
    )
    comparison = _render_comparison_md(
        pdf_path=Path("paper.pdf"),
        standard=moved,
        full_page=failed,
        vlm_preset="granite_docling",
        standard_duration_s=1.0,
        vlm_duration_s=1.0,
    )
    assert "> # Standard title" in comparison
    assert "_(no markdown produced)_" in comparison

    row = _compare_row(
        "paper.pdf",
        ComparisonResult(
            pdf_dir=tmp_path / "paper",
            standard=moved,
            full_page_vlm=failed,
            standard_dir=target,
            full_page_vlm_dir=tmp_path / "paper" / "full_page_vlm",
            comparison_md=tmp_path / "paper" / "comparison.md",
        ),
        2.0,
    )
    assert row.status is RowStatus.FAILURE
    assert row.failed
