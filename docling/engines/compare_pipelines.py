# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Side-by-side comparison: standard PdfEngine vs full-page VlmPipeline.

Runs the same PDF through two pipelines:

* ``standard/`` — the regular :class:`PdfEngine` (layout + OCR + tables +
  optional VLM picture description), producing the full artifact bundle
  (markdown, document.json, nodes.jsonl, chunks.jsonl, tables.jsonl,
  figures.jsonl, run.json, preview.html).
* ``full_page_vlm/`` — Docling's :class:`VlmPipeline` driven by a single
  full-page VLM. Default is **GraniteDocling** (DocTags response →
  produces a full :class:`DoclingDocument`, so all the downstream artifact
  writers run too). If you override to a markdown-only VLM (Qwen,
  Pixtral…), the resulting ``DoclingDocument`` is a single text node and
  ``nodes.jsonl`` / ``tables.jsonl`` / ``figures.jsonl`` will be sparse —
  this caveat is logged into the comparison summary.

Writes ``<output_dir>/<stem>/comparison.md`` with side-by-side stats so a
human (or another agent) can compare the two without re-running anything.
"""

from __future__ import annotations

import datetime as _dt
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.engines.pdf_engine import PdfEngine, bundle_dir_name, resolve_pdf_dir
from docling.engines.schemas import PdfConversionOutput
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.utils.utils import create_file_hash

_log = logging.getLogger(__name__)

_DOCTAGS_PRESETS = frozenset({"granite_docling", "smoldocling"})


@dataclass
class ComparisonResult:
    """Paths and outputs from one comparison run."""

    pdf_dir: Path
    standard: PdfConversionOutput
    full_page_vlm: PdfConversionOutput
    standard_dir: Path
    full_page_vlm_dir: Path
    comparison_md: Path


def run_comparison(
    pdf_path: Path | str,
    output_dir: Path,
    *,
    vlm_preset: str = "granite_docling",
    standard_kwargs: dict[str, Any] | None = None,
    make_html_preview: bool = True,
    standard_engine: PdfEngine | None = None,
    vlm_engine: PdfEngine | None = None,
    pdf_dir: Path | None = None,
) -> ComparisonResult:
    """Run both pipelines on *pdf_path* and write ``comparison.md``.

    Parameters
    ----------
    pdf_path
        Local PDF path or ``http(s)://`` URL.
    output_dir
        Parent directory; this function writes to
        ``<output_dir>/<pdf-stem>/{standard,full_page_vlm,comparison.md}``.
    vlm_preset
        Docling VlmConvert preset id for the full-page VLM. Defaults to
        ``"granite_docling"`` because its DocTags response yields a real
        DoclingDocument (so both subfolders produce comparable bundles).
        Other presets work but markdown-only VLMs produce only ``markdown``
        in the second folder.
    standard_kwargs
        Forwarded to :class:`PdfEngine` for the ``standard/`` run; ignored
        when ``standard_engine`` is given.
    make_html_preview
        Whether to render ``preview.html`` for each side. Default True.
    standard_engine, vlm_engine
        Engines to reuse (a batch loads the models once); built here when
        None — the VLM one by :func:`build_full_page_vlm_engine`.
    pdf_dir
        The comparison folder; default ``<output_dir>/<sanitised stem>``, or
        that stem with a ``_2``... suffix when the folder holds the comparison
        of another PDF (see :func:`resolve_pdf_dir`).
    """
    pdf_path = (
        Path(pdf_path)
        if not str(pdf_path).startswith(("http://", "https://"))
        else pdf_path
    )
    stem = bundle_dir_name(pdf_path.name if isinstance(pdf_path, Path) else "document")
    if pdf_dir is None:
        pdf_dir = (
            resolve_pdf_dir(
                output_dir,
                pdf_path.name,
                file_size=pdf_path.stat().st_size,
                binary_hash=create_file_hash(pdf_path),
                bundle_subdir="standard",
            )
            if isinstance(pdf_path, Path)
            else output_dir / stem
        )
    standard_dir = pdf_dir / "standard"
    full_page_dir = pdf_dir / "full_page_vlm"
    standard_dir.mkdir(parents=True, exist_ok=True)
    full_page_dir.mkdir(parents=True, exist_ok=True)

    # ---- Standard pipeline -------------------------------------------------
    _log.info("[comparison] running standard pipeline → %s", standard_dir)
    standard_t0 = _dt.datetime.now(_dt.timezone.utc)
    if standard_engine is None:
        standard_engine = PdfEngine(**(standard_kwargs or {}))
    # Written to <pdf_dir>/<stem>/ so its files are named <stem>.md etc., then
    # moved to standard/.
    standard_out = _rename_pdf_dir(
        standard_engine.convert(
            pdf_path, pdf_dir=pdf_dir / stem, make_html_preview=make_html_preview
        ),
        standard_dir,
    )
    standard_t1 = _dt.datetime.now(_dt.timezone.utc)

    # ---- Full-page VLM pipeline -------------------------------------------
    _log.info("[comparison] running full-page VLM (%s) → %s", vlm_preset, full_page_dir)
    vlm_t0 = _dt.datetime.now(_dt.timezone.utc)
    if vlm_engine is None:
        vlm_engine = build_full_page_vlm_engine(
            vlm_preset,
            figure_types=(standard_kwargs or {}).get("figure_types", True),
        )
    vlm_out = _rename_pdf_dir(
        vlm_engine.convert(
            pdf_path, pdf_dir=pdf_dir / stem, make_html_preview=make_html_preview
        ),
        full_page_dir,
    )
    vlm_t1 = _dt.datetime.now(_dt.timezone.utc)

    # ---- Summary ----------------------------------------------------------
    comparison_md = pdf_dir / "comparison.md"
    comparison_md.write_text(
        _render_comparison_md(
            pdf_path=pdf_path,
            standard=standard_out,
            full_page=vlm_out,
            vlm_preset=vlm_preset,
            standard_duration_s=(standard_t1 - standard_t0).total_seconds(),
            vlm_duration_s=(vlm_t1 - vlm_t0).total_seconds(),
        ),
        encoding="utf-8",
    )
    _log.info("[comparison] wrote %s", comparison_md)

    return ComparisonResult(
        pdf_dir=pdf_dir,
        standard=standard_out,
        full_page_vlm=vlm_out,
        standard_dir=standard_dir,
        full_page_vlm_dir=full_page_dir,
        comparison_md=comparison_md,
    )


def build_full_page_vlm_engine(preset: str, *, figure_types: bool = True) -> PdfEngine:
    """The ``full_page_vlm/`` side's engine: Docling's VlmPipeline driven by
    the full-page VLM *preset*."""
    return PdfEngine(
        converter=_build_vlm_converter(preset),
        save_artifacts=True,
        embed_images=False,
        figure_types=figure_types,
    )


def _build_vlm_converter(preset: str) -> DocumentConverter:
    vlm_options = VlmConvertOptions.from_preset(preset)
    pipeline_options = VlmPipelineOptions(vlm_options=vlm_options)
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline, pipeline_options=pipeline_options
            )
        },
    )


def _rename_pdf_dir(
    output: PdfConversionOutput, target_dir: Path
) -> PdfConversionOutput:
    """Move the bundle ``PdfEngine`` wrote to *target_dir* (replacing an
    earlier one there) and return *output* with every path in it re-pointed."""
    src = output.output_dir
    if src is None or src == target_dir:
        return output
    if target_dir.exists():
        shutil.rmtree(target_dir)
    src.rename(target_dir)

    def moved(path: Path) -> Path:
        return target_dir / path.relative_to(src) if path.is_relative_to(src) else path

    updates: dict[str, Path | list[Path]] = {}
    for name, value in output:
        if isinstance(value, Path):
            updates[name] = moved(value)
        elif (
            value
            and isinstance(value, list)
            and all(isinstance(v, Path) for v in value)
        ):
            updates[name] = [moved(v) for v in value]
    return output.model_copy(update=updates)


def _render_comparison_md(
    *,
    pdf_path: Path | str,
    standard: PdfConversionOutput,
    full_page: PdfConversionOutput,
    vlm_preset: str,
    standard_duration_s: float,
    vlm_duration_s: float,
) -> str:
    def _md_size(path: Path | None) -> int:
        return path.stat().st_size if path is not None and path.exists() else 0

    def _first_lines(path: Path | None, n: int = 8) -> str:
        if path is None or not path.exists():
            return "_(no markdown produced)_"
        lines = path.read_text(encoding="utf-8").splitlines()[:n]
        return "\n".join(f"> {line}" for line in lines)

    standard_md = standard.markdown_path
    full_md = full_page.markdown_path

    caveat = ""
    if vlm_preset not in _DOCTAGS_PRESETS:
        caveat = (
            f"\n> ⚠ The full-page VLM preset `{vlm_preset}` emits markdown, not "
            "DocTags. The `full_page_vlm/` folder will have a markdown export "
            "but a sparse `nodes.jsonl` / `tables.jsonl` / `figures.jsonl` "
            "because the document graph couldn't be reconstructed from "
            "markdown.\n"
        )

    return f"""# Pipeline comparison — {Path(str(pdf_path)).name}

Two pipelines, same input. See `standard/` and `full_page_vlm/` for the full artifact bundles.
{caveat}
| Metric | standard | full_page_vlm ({vlm_preset}) |
|---|---|---|
| Status | `{standard.status}` | `{full_page.status}` |
| Duration | {standard_duration_s:.2f}s | {vlm_duration_s:.2f}s |
| Page count | {standard.page_count} | {full_page.page_count} |
| Pictures extracted | {len(standard.picture_images)} | {len(full_page.picture_images)} |
| Tables extracted | {len(standard.table_images)} | {len(full_page.table_images)} |
| Chunks | {_count_lines(standard.chunks_jsonl)} | {_count_lines(full_page.chunks_jsonl)} |
| Tables in JSONL | {_count_lines(standard.tables_jsonl)} | {_count_lines(full_page.tables_jsonl)} |
| Figures in JSONL | {_count_lines(standard.figures_jsonl)} | {_count_lines(full_page.figures_jsonl)} |
| Errors | {len(standard.errors)} | {len(full_page.errors)} |
| Markdown size | {_md_size(standard_md):,} bytes | {_md_size(full_md):,} bytes |
| HTML preview | `{_rel(standard.preview_html)}` | `{_rel(full_page.preview_html)}` |

## Standard — first lines of markdown

{_first_lines(standard_md)}

## Full-page VLM — first lines of markdown

{_first_lines(full_md)}
"""


def _count_lines(path: Path | None) -> int:
    if path is None or not path.exists():
        return 0
    with path.open(encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def _rel(p: Path | None) -> str:
    return str(p) if p is not None else "(none)"
