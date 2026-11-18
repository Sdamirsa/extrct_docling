# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""``amir-batch`` CLI — run :class:`PdfEngine` over one or more PDFs.

Usage:

    uv run amir-batch samples/              # every *.pdf in samples/
    uv run amir-batch samples/foo.pdf bar.pdf
    uv run amir-batch samples/ -o out/      # custom output root
    uv run amir-batch samples/ --compare    # full-page VLM A/B per PDF
    uv run amir-batch samples/ --check-only # re-check existing bundles
    uv run amir-batch samples/ --figure-data ollama   # + the numbers behind the charts

``--figure-data`` adds the figure-to-data step
(:mod:`docling.engines.figure_data.step`) on the finished bundles: once the
batch is converted (``--figure-data-when end``, the default: the conversion
models are released first and the reading model loads once) or after each
PDF (``each``). A bundle that already had the step with the same method and
model is left alone, so an interrupted batch picks up where it stopped. The
step never changes a conversion's status; ``amir-figdata step`` runs it on
an output folder at any later time.

The terminal report shows one row per PDF: status, duration, page count,
extracted figures (with noise count), tables, chunks, the components of the
engine errors, the bundle check (``check.json``) and the per-PDF output
folder. Exit code: 1 when a row failed (FAILURE, PARTIAL_SUCCESS, EXCEPTION,
SUCCESS* with failed steps, a MISSING or INCOMPLETE bundle), else 3 when only
bundle checks found issues, else 0; 130 on Ctrl-C.
"""

from __future__ import annotations

import functools
import gc
import logging
import re
import sys
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markup import escape
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from docling.datamodel.base_models import ConversionStatus
from docling.engines.compare_pipelines import (
    ComparisonResult,
    build_full_page_vlm_engine,
    run_comparison,
)
from docling.engines.export_check import (
    CHECK_FILENAME,
    BundleCheck,
    check_bundle,
    write_bundle_check,
)
from docling.engines.figure_data.cli import outcome_printer, runs_table
from docling.engines.figure_data.methods import FigureReader, build_reader
from docling.engines.figure_data.schema import (
    Backend,
    FigureDataChoice,
    FigureDataOptions,
    StepTiming,
)
from docling.engines.figure_data.step import StepRun, needs_step, run_step
from docling.engines.pdf_engine import PdfEngine, bundle_dir_name, resolve_pdf_dir
from docling.engines.run_snapshot import ENGINE_VERSION, RunRecord, read_run_record
from docling.engines.schemas import PdfConversionOutput, RelatedDocument
from docling.engines.structure import DocumentRole
from docling.engines.vlm_specs import PictureDescriptionPreset
from docling.utils.utils import create_file_hash

app = typer.Typer(
    add_completion=False,
    help="Batch-process PDFs through PdfEngine (Amir Engine).",
    rich_markup_mode="rich",
)

_log = logging.getLogger(__name__)

PictureDescriptionChoice = Literal[PictureDescriptionPreset, "off"]


class RowStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"
    EXCEPTION = "EXCEPTION"
    SKIPPED = "SKIPPED"
    INCOMPLETE = "INCOMPLETE"
    MISSING = "MISSING"


class BatchRow(BaseModel):
    """One PDF of the summary table."""

    name: str
    status: RowStatus
    duration_s: float | None = None
    pages: int | None = None
    figures: int | None = None
    noise_figures: int | None = None
    tables: int | None = None
    chunks: int | None = None
    errors: list[str] = Field(
        default_factory=list,
        description="Components of the engine errors, or the exception.",
    )
    check_summary: str | None = None
    check_ok: bool | None = None
    output: Path | None = None

    @property
    def failed(self) -> bool:
        """Not converted cleanly, or no complete bundle to show for it."""
        return self.status not in {RowStatus.SUCCESS, RowStatus.SKIPPED} or bool(
            self.errors
        )


class _FigureRow(BaseModel):
    is_noise: bool | None = None


class PlannedPdf(BaseModel):
    """A PDF of the batch and its bundle folder."""

    path: Path
    pdf_dir: Path
    file_size: int
    binary_hash: str = Field(description="Docling's SHA-256 of the file.")
    document_role: DocumentRole = "manuscript"
    related: list[RelatedDocument] = Field(default_factory=list)

    def as_related(self, role: DocumentRole, pairing: str) -> RelatedDocument:
        return RelatedDocument(
            role=role,
            file_name=self.path.name,
            file_size_bytes=self.file_size,
            binary_hash=self.binary_hash,
            bundle=self.pdf_dir.name,
            pairing=pairing,
        )


_DONE_STATUSES = {ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS}


@app.command()
def main(
    inputs: Annotated[
        list[Path],
        typer.Argument(
            help=(
                "One or more PDF paths or directories. Directories are "
                "scanned (non-recursive) for ``*.pdf`` files (any case)."
            )
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Root output directory."),
    ] = Path("samples/out"),
    compare: Annotated[
        bool,
        typer.Option(
            "--compare/--no-compare",
            "-c",
            help="Run the standard-vs-full-page-VLM comparison per PDF.",
        ),
    ] = False,
    preview: Annotated[
        bool,
        typer.Option(
            "--preview/--no-preview",
            help="Render the clickable HTML bbox viewer per PDF.",
        ),
    ] = True,
    vlm_preset: Annotated[
        str,
        typer.Option(
            "--vlm-preset",
            help=(
                "Full-page VLM preset for the comparison mode (default "
                "``granite_docling`` — DocTags response yields a comparable "
                "DoclingDocument)."
            ),
        ),
    ] = "granite_docling",
    images_scale: Annotated[
        float,
        typer.Option(
            "--images-scale", help="Scale factor for rendered page / crop images."
        ),
    ] = 1.5,
    granite_vision_tables: Annotated[
        bool,
        typer.Option(
            "--granite-vision-tables/--no-granite-vision-tables",
            help=(
                "Use Granite-Vision VLM (4.1-4b) for table structure. "
                "Default on; turn off for plain TableFormer."
            ),
        ),
    ] = True,
    picture_description: Annotated[
        PictureDescriptionChoice,
        typer.Option(
            "--picture-description",
            help=(
                "VLM preset for figure captions. Default 'granite_vision_4b' "
                "(Granite-Vision 4.1-4b); 'off' skips captions."
            ),
        ),
    ] = "granite_vision_4b",
    picture_area_threshold: Annotated[
        float,
        typer.Option(
            "--picture-area-threshold",
            min=0.0,
            max=1.0,
            help=(
                "Smallest picture, as a fraction of the page area, that gets a "
                "VLM caption."
            ),
        ),
    ] = 0.03,
    figure_types: Annotated[
        bool,
        typer.Option(
            "--figure-types/--no-figure-types",
            help=(
                "Type every figure (ct, angiography, ecg, bar_chart, ...) with "
                "BiomedCLIP. Default on; ~0.8 GB GPU, ~15 ms per figure."
            ),
        ),
    ] = True,
    figure_data: Annotated[
        FigureDataChoice,
        typer.Option(
            "--figure-data",
            help=(
                "Read the numbers behind chart figures, as a step on the "
                "finished bundles: 'ollama' (a local model, nothing leaves "
                "the machine), 'cloud' (one call per figure to a model's "
                "API endpoint, OpenRouter by default, key in "
                "OPENROUTER_API_KEY or .env) or 'agent' (one agent session "
                "per figure, through the Claude Code CLI). Default off."
            ),
        ),
    ] = "off",
    figure_data_model: Annotated[
        str | None,
        typer.Option(
            "--figure-data-model",
            help="Model for --figure-data; default: the method's own.",
        ),
    ] = None,
    figure_data_backend: Annotated[
        Backend | None,
        typer.Option(
            "--figure-data-backend",
            help=(
                "Where the --figure-data model runs: ollama, "
                "openai-compatible (an API endpoint) or claude-cli (the "
                "agent's runtime). "
                "Default: the method's own."
            ),
        ),
    ] = None,
    figure_data_base_url: Annotated[
        str,
        typer.Option(
            "--figure-data-base-url",
            help=(
                "--figure-data cloud: the chat-completions endpoint "
                "(OpenAI-compatible). OpenRouter by default."
            ),
        ),
    ] = FigureDataOptions().cloud_base_url,
    figure_data_key_env: Annotated[
        str,
        typer.Option(
            "--figure-data-key-env",
            help=(
                "--figure-data cloud: the environment variable (also read "
                "from .env) that holds the endpoint's API key."
            ),
        ),
    ] = FigureDataOptions().cloud_api_key_env,
    figure_data_when: Annotated[
        StepTiming,
        typer.Option(
            "--figure-data-when",
            help=(
                "'end': read the figures once the whole batch is converted "
                "(the reading model loads once, beside no conversion "
                "model). 'each': after each PDF."
            ),
        ),
    ] = "end",
    skip_existing: Annotated[
        bool,
        typer.Option(
            "--skip-existing/--no-skip-existing",
            help=(
                "Skip a PDF whose bundle is a finished run of it (run.json: "
                "complete, SUCCESS or PARTIAL_SUCCESS, no errors, same file, "
                "engine version and options)."
            ),
        ),
    ] = True,
    retries: Annotated[
        int,
        typer.Option(
            "--retries",
            min=0,
            help="Rerun a PDF this many more times when the engine raises.",
        ),
    ] = 1,
    check_only: Annotated[
        bool,
        typer.Option(
            "--check-only",
            help=(
                "Convert nothing: re-check each PDF's existing bundle and "
                "rewrite its check.json."
            ),
        ),
    ] = False,
    pair_supplements: Annotated[
        bool,
        typer.Option(
            "--pair-supplements/--no-pair-supplements",
            help=(
                "Record a PDF named like another of the batch plus "
                "'Supplementary' ('supplement', 'supp', 'SI', 'appendix') as "
                "that manuscript's supplement: run.json of both gets "
                "'related', the supplement 'document_role'."
            ),
        ),
    ] = True,
    supplement: Annotated[
        list[str] | None,
        typer.Option(
            "--supplement",
            help=(
                "SUPPLEMENT.pdf=MANUSCRIPT.pdf (file names of two PDFs of the "
                "batch): record the first as the supplement of the second "
                "when their names do not say so. Repeatable."
            ),
        ),
    ] = None,
) -> None:
    """Run ``PdfEngine`` (or the comparison runner) on every PDF found."""
    console = Console()
    if check_only and compare:
        console.print(
            "[red]--check-only checks standard bundles; drop --compare.[/red]"
        )
        raise typer.Exit(code=2)
    pdf_paths = _collect_pdfs(inputs, console)
    if not pdf_paths:
        console.print("[red]No PDF files found.[/red]")
        raise typer.Exit(code=2)

    mode = "check-only" if check_only else "compare" if compare else "single"
    console.rule(
        f"[bold]amir-batch[/bold] · mode=[cyan]{mode}[/cyan] · "
        f"{len(pdf_paths)} PDF{'s' if len(pdf_paths) != 1 else ''} -> "
        f"[green]{escape(str(output_dir))}[/green]"
    )
    plan = _plan_bundles(pdf_paths, output_dir, console, compare=compare)
    try:
        pairs = _pair_named_supplements(plan, supplement or [])
    except ValueError as exc:
        console.print(f"[red]--supplement: {escape(str(exc))}[/red]")
        raise typer.Exit(code=2) from None
    if pair_supplements:
        pairs += _pair_supplements(plan)
    for manuscript, paired in pairs:
        console.print(
            f"[cyan]supplement[/cyan] {escape(paired.path.name)} of "
            f"{escape(manuscript.path.name)}"
        )

    if check_only:
        rows = [_check_row(item.path, item.pdf_dir) for item in plan]
        _render_summary(console, rows, mode=mode)
        _exit(rows)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    # One engine per batch: Docling loads the models at an engine's first PDF.
    engine = PdfEngine(
        images_scale=images_scale,
        granite_vision_tables=granite_vision_tables,
        picture_description=(
            None if picture_description == "off" else picture_description
        ),
        picture_area_threshold=picture_area_threshold,
        figure_types=figure_types,
    )
    figure_step = (
        _FigureStep(
            # Model and backend left out take the method's own.
            FigureDataOptions.model_validate(
                {
                    "method": figure_data,
                    "model": figure_data_model,
                    "backend": figure_data_backend,
                    "cloud_base_url": figure_data_base_url,
                    "cloud_api_key_env": figure_data_key_env,
                }
            ),
            console,
        )
        if figure_data != "off" and not compare
        else None
    )
    if figure_data != "off" and compare:
        console.print(
            "[yellow]--figure-data is skipped with --compare; run "
            "amir-figdata step on the bundle you keep.[/yellow]"
        )
    vlm_engine = (
        build_full_page_vlm_engine(vlm_preset, figure_types=figure_types)
        if compare
        else None
    )
    # The run.json engine_config of each bundle of a PDF, by subfolder.
    expected: dict[str | None, dict[str, Any]] = (
        {
            "standard": engine.engine_config(make_html_preview=preview),
            "full_page_vlm": vlm_engine.engine_config(make_html_preview=preview),
        }
        if vlm_engine is not None
        else {None: engine.engine_config(make_html_preview=preview)}
    )

    rows: list[BatchRow] = []
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task("processing", total=len(plan))
            for item in plan:
                pdf_path, pdf_dir = item.path, item.pdf_dir
                progress.update(
                    task_id, description=f"[cyan]{escape(pdf_path.name)}[/cyan]"
                )
                if skip_existing and _is_done(item, expected, console):
                    bundle = pdf_dir / "standard" if compare else pdf_dir
                    rows.append(_bundle_row(pdf_path, bundle, status=RowStatus.SKIPPED))
                else:
                    run = (
                        functools.partial(
                            _run_compare,
                            pdf_path,
                            pdf_dir,
                            output_dir,
                            engine=engine,
                            vlm_engine=vlm_engine,
                            vlm_preset=vlm_preset,
                            preview=preview,
                        )
                        if vlm_engine is not None
                        else functools.partial(
                            _run_single, item, engine=engine, preview=preview
                        )
                    )
                    rows.append(
                        _with_retries(
                            pdf_path, pdf_dir, run, retries=retries, console=console
                        )
                    )
                    del run
                if figure_step is not None and figure_data_when == "each":
                    figure_step.run(pdf_dir, pdf_path)
                progress.advance(task_id)
    except KeyboardInterrupt:
        console.print(
            f"[red]Interrupted[/red] after {len(rows)} of {len(plan)} PDFs; "
            "the PDF in progress has no complete bundle."
        )
        _render_summary(console, rows, mode=mode)
        raise typer.Exit(code=130) from None

    if figure_step is not None:
        try:
            if figure_data_when == "end":
                # Let go of the conversion engine and its models before a
                # reading model is loaded beside them.
                del engine
                _release_gpu_memory()
                for item in plan:
                    figure_step.run(item.pdf_dir, item.path)
        except KeyboardInterrupt:
            console.print(
                "[red]Interrupted[/red] during figure-to-data; the bundles "
                "are complete, rerun to read the remaining figures."
            )
        finally:
            figure_step.close()
        if figure_step.runs:
            console.print(runs_table(figure_step.runs))
    _render_summary(console, rows, mode=mode)
    _exit(rows)


def _release_gpu_memory() -> None:
    """Collect what is no longer referenced and hand torch's cached GPU
    memory back, when torch was loaded at all."""
    gc.collect()
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available():
        torch.cuda.empty_cache()


class _FigureStep:
    """The figure-to-data step on the bundles of a batch, with one reader
    for all of them."""

    def __init__(self, options: FigureDataOptions, console: Console) -> None:
        self.options = options
        self.console = console
        self.runs: list[StepRun] = []
        self._reader: FigureReader | None = None

    def run(self, bundle: Path, pdf_path: Path) -> None:
        if not (bundle / "document.json").is_file():
            return
        if not needs_step(bundle, self.options):
            return
        if self._reader is None:
            self._reader = build_reader(self.options)
        try:
            self.runs.append(
                run_step(
                    bundle,
                    pdf_path,
                    self.options,
                    reader=self._reader,
                    on_result=outcome_printer(self.console, bundle.name),
                )
            )
        except Exception as exc:
            # The step reads finished bundles; whatever goes wrong in it
            # leaves the conversion as it was.
            _log.exception("figure-to-data failed on %s", bundle)
            self.console.print(
                f"[red]figure-to-data failed[/red] on {escape(bundle.name)}: "
                f"{escape(type(exc).__name__)}: {escape(str(exc)[:200])}"
            )

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()


def _exit(rows: list[BatchRow]) -> None:
    """1 when a row failed, else 3 when a bundle check found issues; a batch
    of ordinary papers often has a few, which must not stop ``&& next``."""
    if any(row.failed for row in rows):
        raise typer.Exit(code=1)
    if any(row.check_ok is False for row in rows):
        raise typer.Exit(code=3)


def _collect_pdfs(inputs: list[Path], console: Console) -> list[Path]:
    paths: list[Path] = []
    for entry in inputs:
        if entry.is_dir():
            paths.extend(
                p for p in entry.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
            )
        elif entry.is_file() and entry.suffix.lower() == ".pdf":
            paths.append(entry)
        else:
            console.print(
                f"[yellow]skipping[/yellow] {escape(str(entry))} (not a PDF or dir)"
            )
    return sorted({p.resolve() for p in paths})


def _plan_bundles(
    pdf_paths: list[Path], output_dir: Path, console: Console, *, compare: bool
) -> list[PlannedPdf]:
    """Each PDF with its bundle folder, resolved for the whole batch so that
    two PDFs never share one (see :func:`resolve_pdf_dir`)."""
    plan: list[PlannedPdf] = []
    taken: set[Path] = set()
    for pdf_path in pdf_paths:
        size, binary_hash = pdf_path.stat().st_size, create_file_hash(pdf_path)
        pdf_dir = resolve_pdf_dir(
            output_dir,
            pdf_path.name,
            file_size=size,
            binary_hash=binary_hash,
            taken=taken,
            bundle_subdir="standard" if compare else None,
        )
        taken.add(pdf_dir)
        if pdf_dir.name != bundle_dir_name(pdf_path.name):
            console.print(
                f"[yellow]name clash[/yellow] {escape(str(pdf_path))} -> "
                f"{escape(str(pdf_dir))}"
            )
        plan.append(
            PlannedPdf(
                path=pdf_path, pdf_dir=pdf_dir, file_size=size, binary_hash=binary_hash
            )
        )
    return plan


_SUPPLEMENT_SUFFIX = re.compile(
    r"[\s_.\-]+(?:supp(?:l(?:ement(?:ary|al)?)?)?\.?|si|appendix)"
    r"(?:[\s_.\-]+(?:materials?|information|info|data|files?|appendix))?"
    r"(?:[\s_.\-]*\d+)?$",
    re.IGNORECASE,
)
_NAME_SEPARATORS = re.compile(r"[\s_\-]+")


def _mark_pair(manuscript: PlannedPdf, supplement: PlannedPdf, pairing: str) -> None:
    supplement.document_role = "supplement"
    supplement.related.append(manuscript.as_related("manuscript", pairing))
    manuscript.related.append(supplement.as_related("supplement", pairing))


def _pair_named_supplements(
    plan: list[PlannedPdf], specs: list[str]
) -> list[tuple[PlannedPdf, PlannedPdf]]:
    """Pair the PDFs of *plan* named in ``SUPPLEMENT.pdf=MANUSCRIPT.pdf``
    *specs*; ValueError for a spec that does not name two PDFs of the plan."""
    by_name: dict[str, list[PlannedPdf]] = {}
    for item in plan:
        by_name.setdefault(item.path.name, []).append(item)
    pairs: list[tuple[PlannedPdf, PlannedPdf]] = []
    for spec in specs:
        names = [name.strip() for name in spec.split("=")]
        if len(names) != 2:
            raise ValueError(f"{spec!r} is not SUPPLEMENT.pdf=MANUSCRIPT.pdf")
        found = [by_name.get(name, []) for name in names]
        for name, items in zip(names, found, strict=True):
            if len(items) != 1:
                raise ValueError(f"{name!r} names {len(items)} PDFs of the batch")
        supplement, manuscript = found[0][0], found[1][0]
        _mark_pair(manuscript, supplement, "explicit")
        pairs.append((manuscript, supplement))
    return pairs


def _pair_supplements(plan: list[PlannedPdf]) -> list[tuple[PlannedPdf, PlannedPdf]]:
    """Mark each PDF of *plan* whose name is another's plus a supplement
    suffix ("AMIE-Mx Supplementary.pdf" beside "AMIE-Mx.pdf") as that
    manuscript's supplement and return the (manuscript, supplement) pairs. A
    name that fits two manuscripts, and a PDF already paired, are left."""

    def key(stem: str) -> str:
        return _NAME_SEPARATORS.sub(" ", stem).strip().casefold()

    by_key: dict[str, list[PlannedPdf]] = {}
    for item in plan:
        by_key.setdefault(key(item.path.stem), []).append(item)
    pairs: list[tuple[PlannedPdf, PlannedPdf]] = []
    for item in plan:
        match = _SUPPLEMENT_SUFFIX.search(item.path.stem)
        if match is None or item.document_role == "supplement":
            continue
        manuscripts = by_key.get(key(item.path.stem[: match.start()]), [])
        if len(manuscripts) != 1:
            continue
        manuscript = manuscripts[0]
        _mark_pair(manuscript, item, "file-name")
        pairs.append((manuscript, item))
    return pairs


def _is_done(
    item: PlannedPdf, expected: dict[str | None, dict[str, Any]], console: Console
) -> bool:
    """Whether each bundle of *item* (subfolder -> the engine_config this
    batch writes) is a finished run of this PDF by this engine release with
    these options; prints why a bundle that is not gets converted again."""
    for subdir, engine_config in expected.items():
        bundle = item.pdf_dir / subdir if subdir is not None else item.pdf_dir
        record = read_run_record(bundle)
        if record is None:
            return False
        reason = _stale_reason(record, item, engine_config)
        if reason is not None:
            label = bundle.relative_to(item.pdf_dir.parent).as_posix()
            console.print(
                f"[yellow]reconverting[/yellow] {escape(label)}: {escape(reason)}"
            )
            return False
    return True


def _stale_reason(
    record: RunRecord, item: PlannedPdf, engine_config: dict[str, Any]
) -> str | None:
    if record.complete is not True:
        return "previous run did not finish"
    if record.conversion_status not in _DONE_STATUSES:
        return f"previous run ended {record.status}"
    if record.errors:
        return "previous run had errors"
    if record.engine.version != ENGINE_VERSION:
        return f"engine version differs ({record.engine.version} -> {ENGINE_VERSION})"
    if not record.is_source(item.path.name, item.file_size, item.binary_hash):
        return "different file"
    if differences := record.config_differences(engine_config):
        return f"options differ ({', '.join(differences)})"
    return None


def _with_retries(
    pdf_path: Path,
    pdf_dir: Path,
    run: Callable[[], BatchRow],
    *,
    retries: int,
    console: Console,
) -> BatchRow:
    attempts = retries + 1
    failure = ""
    for attempt in range(1, attempts + 1):
        try:
            return run()
        except Exception as exc:
            _log.exception(
                "processing %s failed (attempt %d of %d)",
                pdf_path.name,
                attempt,
                attempts,
            )
            failure = f"{type(exc).__name__}: {exc}"
            console.print(
                f"[red]attempt {attempt}/{attempts} failed[/red] "
                f"{escape(pdf_path.name)}: {escape(failure)}"
            )
    return BatchRow(
        name=pdf_path.name,
        status=RowStatus.EXCEPTION,
        errors=[failure[:200]],
        output=pdf_dir,
    )


def _run_single(item: PlannedPdf, *, engine: PdfEngine, preview: bool) -> BatchRow:
    started = time.monotonic()
    out = engine.convert(
        item.path,
        pdf_dir=item.pdf_dir,
        make_html_preview=preview,
        document_role=item.document_role,
        related=item.related,
    )
    return _converted_row(item.path.name, out, time.monotonic() - started)


def _run_compare(
    pdf_path: Path,
    pdf_dir: Path,
    output_dir: Path,
    *,
    engine: PdfEngine,
    vlm_engine: PdfEngine,
    vlm_preset: str,
    preview: bool,
) -> BatchRow:
    started = time.monotonic()
    res = run_comparison(
        pdf_path,
        output_dir,
        vlm_preset=vlm_preset,
        make_html_preview=preview,
        standard_engine=engine,
        vlm_engine=vlm_engine,
        pdf_dir=pdf_dir,
    )
    return _compare_row(pdf_path.name, res, time.monotonic() - started)


def _row_status(status: ConversionStatus) -> RowStatus:
    if status == ConversionStatus.SUCCESS:
        return RowStatus.SUCCESS
    if status == ConversionStatus.PARTIAL_SUCCESS:
        return RowStatus.PARTIAL_SUCCESS
    return RowStatus.FAILURE


def _converted_row(name: str, out: PdfConversionOutput, duration_s: float) -> BatchRow:
    figures, noise = _count_figures(out.figures_jsonl)
    return BatchRow(
        name=name,
        status=_row_status(out.status),
        duration_s=duration_s,
        pages=out.page_count,
        figures=figures,
        noise_figures=noise,
        tables=_count_lines(out.tables_jsonl),
        chunks=_count_lines(out.chunks_jsonl),
        errors=[e.component for e in out.errors],
        check_summary=out.check.summary_line() if out.check is not None else None,
        check_ok=out.check.ok if out.check is not None else None,
        output=out.output_dir,
    )


def _compare_row(name: str, res: ComparisonResult, duration_s: float) -> BatchRow:
    standard = _converted_row(name, res.standard, duration_s)
    vlm = _converted_row(name, res.full_page_vlm, duration_s)
    statuses = {standard.status, vlm.status}
    status = next(
        s
        for s in (RowStatus.FAILURE, RowStatus.PARTIAL_SUCCESS, RowStatus.SUCCESS)
        if s in statuses
    )
    return standard.model_copy(
        update={
            "name": f"{name} · cmp",
            "status": status,
            "errors": standard.errors + [f"vlm:{c}" for c in vlm.errors],
            "check_summary": (
                f"standard: {standard.check_summary or 'n/a'} | "
                f"full_page_vlm: {vlm.check_summary or 'n/a'}"
            ),
            "check_ok": (
                False
                if False in (standard.check_ok, vlm.check_ok)
                else standard.check_ok
            ),
            "output": res.pdf_dir,
        }
    )


def _check_row(pdf_path: Path, pdf_dir: Path) -> BatchRow:
    if not (pdf_dir / "document.json").is_file():
        return BatchRow(name=pdf_path.name, status=RowStatus.MISSING, output=pdf_dir)
    # Bundles of earlier releases may not load; one must not end the batch.
    try:
        check = check_bundle(pdf_dir, pdf_path=pdf_path)
    except Exception as exc:
        _log.exception("checking %s failed", pdf_dir)
        return BatchRow(
            name=pdf_path.name,
            status=RowStatus.EXCEPTION,
            errors=[f"{type(exc).__name__}: {exc}"[:200]],
            output=pdf_dir,
        )
    write_bundle_check(pdf_dir, check)
    return _bundle_row(pdf_path, pdf_dir, check=check)


def _bundle_row(
    pdf_path: Path,
    pdf_dir: Path,
    *,
    status: RowStatus | None = None,
    check: BundleCheck | None = None,
) -> BatchRow:
    """A row for a bundle already on disk (skipped, or re-checked)."""
    record = read_run_record(pdf_dir)
    no_check = "no check.json"
    if check is None and (pdf_dir / CHECK_FILENAME).is_file():
        try:
            check = BundleCheck.model_validate_json(
                (pdf_dir / CHECK_FILENAME).read_text(encoding="utf-8")
            )
        except ValueError:
            _log.warning("%s does not parse", pdf_dir / CHECK_FILENAME)
            no_check = "unreadable check.json"
    figures, noise = _count_figures(pdf_dir / "figures.jsonl")
    return BatchRow(
        name=pdf_path.name,
        status=status if status is not None else _record_status(record),
        pages=record.output_summary.page_count if record is not None else None,
        figures=figures,
        noise_figures=noise,
        tables=_count_lines(pdf_dir / "tables.jsonl"),
        chunks=_count_lines(pdf_dir / "chunks.jsonl"),
        errors=[e.component for e in record.errors] if record is not None else [],
        check_summary=check.summary_line() if check is not None else no_check,
        check_ok=check.ok if check is not None else None,
        output=pdf_dir,
    )


def _record_status(record: RunRecord | None) -> RowStatus:
    if record is None or record.complete is False:
        return RowStatus.INCOMPLETE
    status = record.conversion_status
    return _row_status(status) if status is not None else RowStatus.INCOMPLETE


def _count_figures(figures_jsonl: Path | None) -> tuple[int, int]:
    """Pictures and noise pictures in ``figures.jsonl`` — one row per
    picture, with or without a crop."""
    if figures_jsonl is None or not figures_jsonl.is_file():
        return 0, 0
    rows = [
        _FigureRow.model_validate_json(line)
        for line in figures_jsonl.read_text(encoding="utf-8").splitlines()
        if line
    ]
    return len(rows), sum(1 for row in rows if row.is_noise)


def _count_lines(path: Path | None) -> int:
    if path is None or not path.is_file():
        return 0
    with path.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


_STATUS_STYLE = {RowStatus.SUCCESS: "green", RowStatus.SKIPPED: "cyan"}


def _render_summary(console: Console, rows: list[BatchRow], *, mode: str) -> None:
    table = Table(
        title=f"amir-batch summary ({mode})",
        show_lines=False,
        header_style="bold",
    )
    table.add_column("PDF", overflow="fold")
    table.add_column("status")
    table.add_column("dur", justify="right")
    table.add_column("pages", justify="right")
    table.add_column("figures")
    table.add_column("tables", justify="right")
    table.add_column("chunks", justify="right")
    table.add_column("errs", overflow="fold")
    table.add_column("check", overflow="fold")
    table.add_column("output", overflow="fold")
    for row in rows:
        # Red is what makes the exit code 1; check issues alone (exit 3) are
        # yellow in the check column.
        status = row.status.value
        if row.status == RowStatus.SUCCESS and row.errors:
            status = "SUCCESS*"
        style = "red" if row.failed else _STATUS_STYLE[row.status]
        check_style = "yellow" if row.check_ok is False else "default"
        table.add_row(
            escape(row.name),
            f"[{style}]{status}[/{style}]",
            f"{row.duration_s:.1f}s" if row.duration_s is not None else "—",
            _cell(row.pages),
            f"{row.figures} ({row.noise_figures} noise)"
            if row.figures is not None
            else "—",
            _cell(row.tables),
            _cell(row.chunks),
            escape(", ".join(row.errors)) if row.errors else "0",
            f"[{check_style}]{escape(row.check_summary or '—')}[/{check_style}]",
            escape(str(row.output)) if row.output is not None else "—",
        )
    console.print(table)


def _cell(value: int | None) -> str:
    return str(value) if value is not None else "—"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
