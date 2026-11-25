# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Per-PDF ``run.json`` snapshot: environment, timing, models, and config.

Written alongside ``document.json`` / ``nodes.jsonl`` so any downstream agent
or reviewer can reproduce *which* pipeline produced *this* output and on
which environment, without needing to re-read the source code.
"""

from __future__ import annotations

import datetime as _dt
import functools
import importlib.util
import json
import logging
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from docling.datamodel.base_models import ConversionStatus

_log = logging.getLogger(__name__)

RUN_JSON_FILENAME = "run.json"
_SCHEMA_VERSION = "1"

# This fork's release: the upstream Docling version it is built on plus
# "-r<n>", the fork's revision on that base. Matches the git tag
# ``extrct_docling-v<ENGINE_VERSION>``; restart at -r1 on a new Docling base.
ENGINE_NAME = "extrct_docling"
ENGINE_VERSION = "2.131.0-r8"
ENGINE_REPOSITORY = "https://github.com/Sdamirsa/extrct_docling"

_TRACKED_PACKAGES = (
    "docling",
    "docling-slim",
    "docling-core",
    "docling-ibm-models",
    "docling-parse",
    "onnxruntime",
    "onnxruntime-gpu",
    "open-clip-torch",
    "pypdfium2",
    "torch",
    "transformers",
)


def build_run_snapshot(
    *,
    source: str,
    source_kind: str,
    file_name: str | None,
    file_size: int | None,
    binary_hash: str | None,
    status: str,
    complete: bool,
    started_at: _dt.datetime,
    finished_at: _dt.datetime,
    engine_config: dict[str, Any],
    pipeline_options: dict[str, Any] | None,
    page_count: int,
    pictures_extracted: int,
    tables_extracted: int,
    errors: list[dict[str, Any]],
    document_role: str = "manuscript",
    related: list[dict[str, Any]] | None = None,
    structure_version: str | None = None,
    quality: dict[str, Any] | None = None,
    converted_from: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``run.json`` content, without writing it. ``complete`` says the
    engine ran every step of the bundle; *binary_hash* is Docling's SHA-256
    of the source file (``InputDocument.document_hash``). *converted_from*
    is the file the PDF was made from or taken out of, when it is not the
    file the user gave (:mod:`docling.engines.sources`). *related* names the
    PDFs this one belongs with (its manuscript, its supplements);
    *structure_version* is the version of the labelling rules, which changes
    when a label, a heading level or a link can come out differently;
    *quality* is the :class:`~docling.engines.structure.QualityReport`."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "engine": engine_provenance(),
        "source": _source_block(
            source,
            source_kind,
            file_name=file_name,
            file_size=file_size,
            binary_hash=binary_hash,
            converted_from=converted_from,
        ),
        "status": status,
        "complete": complete,
        "document_role": document_role,
        "related": related or [],
        "structure_version": structure_version,
        "quality": quality,
        "timing": _timing_block(started_at, finished_at),
        "engine_config": engine_config,
        "pipeline_options": pipeline_options,
        "models": _models_summary(pipeline_options),
        "environment": _environment_block(),
        "output_summary": {
            "page_count": page_count,
            "pictures_extracted": pictures_extracted,
            "tables_extracted": tables_extracted,
            "error_count": len(errors),
        },
        "errors": errors,
    }


def write_run_snapshot(pdf_dir: Path, snapshot: dict[str, Any]) -> Path:
    """Write *snapshot* (from :func:`build_run_snapshot`) to
    ``<pdf_dir>/run.json`` and return its path."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    target = pdf_dir / RUN_JSON_FILENAME
    write_text_atomic(
        target, json.dumps(snapshot, ensure_ascii=False, indent=2, default=str)
    )
    _log.info("Wrote run snapshot to %s", target)
    return target


def write_text_atomic(target: Path, text: str) -> None:
    """Write *text* to *target* through a temporary file in its folder, so a
    process killed mid-write leaves the previous file, never half of one."""
    partial = target.with_name(f".{target.name}.partial")
    partial.write_text(text, encoding="utf-8")
    partial.replace(target)


def public_source_path(path: Path) -> str:
    """*path* relative to the current directory, or its file name when it is
    outside it: absolute paths leak usernames and machine layout into shared
    bundles. A path given under the current directory stays as given when a
    link in it leads elsewhere (a worktree whose ``samples/`` links to the
    main checkout), so the bundle names the PDF from where it was run."""
    cwd = Path.cwd()
    for candidate in (path.absolute(), path.resolve()):
        if ".." not in candidate.parts and candidate.is_relative_to(cwd):
            return candidate.relative_to(cwd).as_posix()
    return path.name


class RunSource(BaseModel):
    input: str | None = None
    source_kind: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    binary_hash: str | None = Field(
        None, description="None in bundles written before the field existed."
    )
    converted_from: dict[str, Any] | None = Field(
        None, description="The Word file or archive member the PDF was made from."
    )


class RunEngine(BaseModel):
    version: str | None = None


class RunOutputSummary(BaseModel):
    page_count: int = 0
    tables_extracted: int = 0


class RunError(BaseModel):
    component: str
    message: str = ""


class RunRecord(BaseModel):
    """The fields of an existing ``run.json`` that are read back: by the
    batch CLI, the bundle check and the bundle-folder resolution."""

    status: str | None = None
    complete: bool | None = Field(
        None, description="None in bundles written before the field existed."
    )
    engine: RunEngine = RunEngine()
    source: RunSource = RunSource()
    engine_config: dict[str, Any] = Field(default_factory=dict)
    output_summary: RunOutputSummary = RunOutputSummary()
    errors: list[RunError] = Field(default_factory=list)
    # Written by the figure-to-data step when it has run on the bundle.
    figure_to_data: dict[str, Any] | None = None

    @property
    def conversion_status(self) -> ConversionStatus | None:
        # Written as str(ConversionStatus.X): "ConversionStatus.SUCCESS".
        if self.status is None:
            return None
        return ConversionStatus(self.status.rsplit(".", 1)[-1].lower())

    @property
    def chunk_max_tokens(self) -> int | None:
        value = self.engine_config.get("chunk_max_tokens")
        return value if isinstance(value, int) else None

    def is_source(
        self,
        file_name: str,
        file_size: int | None,
        binary_hash: str | None = None,
    ) -> bool:
        """Whether the bundle was converted from this PDF: the same file name,
        and the same size and binary hash where both sides know them. A
        bundle that records no file name (an unreadable ``run.json``) is taken
        to be this PDF's."""
        recorded = self.source
        if recorded.file_name is None:
            return True
        return (
            recorded.file_name == file_name
            and _agree(recorded.file_size_bytes, file_size)
            and _agree(recorded.binary_hash, binary_hash)
        )

    def config_differences(self, engine_config: dict[str, Any]) -> list[str]:
        """The keys of *engine_config* whose value the bundle records
        differently. A key the bundle does not record (it was written before
        the key existed) is not compared."""
        current = json.loads(json.dumps(engine_config, default=str))
        return [
            key
            for key, value in current.items()
            if key in self.engine_config and self.engine_config[key] != value
        ]


def _agree(recorded: object, current: object) -> bool:
    return recorded is None or current is None or recorded == current


def read_run_record(pdf_dir: Path) -> RunRecord | None:
    """``<pdf_dir>/run.json`` as a :class:`RunRecord`, or None without one.
    One that does not parse (a process killed while writing it) reads as an
    incomplete run of an unknown file."""
    path = pdf_dir / RUN_JSON_FILENAME
    if not path.is_file():
        return None
    try:
        return RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        _log.warning(
            "%s does not parse (%s); taking it for an incomplete run",
            path,
            str(exc).splitlines()[0],
        )
        return RunRecord(complete=False)


@functools.cache
def engine_provenance() -> dict[str, Any]:
    """Which release of this fork wrote the bundle. ``git_commit`` /
    ``git_dirty`` (uncommitted changes to tracked files) and ``release`` (the
    release tag HEAD is at; None past it) are filled when running from a git
    checkout; a wheel or ``git+https`` install has none.

    Cached for the process: :class:`~docling.engines.PdfEngine` calls it when
    built, before it writes anything, so a bundle regenerated inside the
    checkout does not flag its own files as uncommitted changes."""
    block: dict[str, Any] = {
        "name": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "release": None,
        "repository": ENGINE_REPOSITORY,
        "git_commit": None,
        "git_dirty": None,
    }
    root = Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        return block
    try:
        commit = _git(root, "rev-parse", "HEAD")
        changes = _git(root, "status", "--porcelain", "--untracked-files=no")
    except (OSError, subprocess.SubprocessError) as exc:
        _log.warning("run.json: git state unavailable: %s", exc)
        return block
    block["git_commit"] = commit
    block["git_dirty"] = bool(changes)
    block["release"] = _release_tag(root)
    return block


def _release_tag(root: Path) -> str | None:
    try:
        return _git(
            root, "describe", "--tags", "--exact-match", f"--match={ENGINE_NAME}-v*"
        )
    except subprocess.CalledProcessError:
        return None


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout.strip()


def _source_block(
    source: str,
    source_kind: str,
    *,
    file_name: str | None,
    file_size: int | None,
    binary_hash: str | None,
    converted_from: dict[str, Any] | None = None,
) -> dict[str, Any]:
    block = {
        "input": (
            public_source_path(Path(source)) if source_kind == "local_path" else source
        ),
        "source_kind": source_kind,
        "file_name": file_name,
        "file_size_bytes": file_size,
        "binary_hash": binary_hash,
    }
    if converted_from is not None:
        block["converted_from"] = converted_from
    return block


def _timing_block(
    started_at: _dt.datetime, finished_at: _dt.datetime
) -> dict[str, Any]:
    duration = (finished_at - started_at).total_seconds()
    return {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(duration, 3),
    }


def _models_summary(pipeline_options: dict[str, Any] | None) -> dict[str, Any]:
    """Flat per-stage summary for quick inspection — pipeline_options has the full data."""
    if not pipeline_options:
        return {}
    summary: dict[str, Any] = {}
    for key in (
        "layout_options",
        "ocr_options",
        "table_structure_options",
        "picture_description_options",
        "picture_classification_options",
        "code_formula_options",
        "chart_extraction_options",
        "accelerator_options",
    ):
        if key in pipeline_options:
            summary[key.removesuffix("_options")] = pipeline_options[key]
    summary["do_ocr"] = pipeline_options.get("do_ocr")
    summary["do_table_structure"] = pipeline_options.get("do_table_structure")
    summary["do_picture_classification"] = pipeline_options.get(
        "do_picture_classification"
    )
    summary["do_code_enrichment"] = pipeline_options.get("do_code_enrichment")
    summary["do_formula_enrichment"] = pipeline_options.get("do_formula_enrichment")
    summary["do_chart_extraction"] = pipeline_options.get("do_chart_extraction")
    return summary


def _environment_block() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system": platform.system(),
        **_torch_block(),
        "packages": _package_versions(),
    }


def _torch_block() -> dict[str, Any]:
    # torch comes with the models-local extra, which docling-slim can go without.
    if importlib.util.find_spec("torch") is None:
        return {"torch_cuda": None, "cuda_available": False, "device_name": None}
    import torch

    available = torch.cuda.is_available()
    return {
        "torch_cuda": torch.version.cuda,
        "cuda_available": available,
        "device_name": torch.cuda.get_device_name(0) if available else None,
    }


def _package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for pkg in _TRACKED_PACKAGES:
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = None
    return out
