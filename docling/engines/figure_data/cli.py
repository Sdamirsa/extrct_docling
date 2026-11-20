# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""``amir-figdata``: the figure-to-data step on converted papers.

    # the whole step on an output folder (every bundle in it) or on bundles
    amir-figdata step samples/out --pdf-dir samples --method ollama
    amir-figdata step samples/out/AMIE-Mx --method agent

    # or phase by phase
    amir-figdata prepare samples/out --pdf-dir samples
    amir-figdata read samples/out --method cloud
    amir-figdata embed samples/out

    amir-figdata score truth/ runs/
    amir-figdata ps
    amir-figdata unload gemma4:26b-a4b-it-qat

Methods: ``ollama`` (a local model, nothing leaves the machine), ``cloud``
(one call per figure to a model's API endpoint: OpenRouter by default, key
in ``OPENROUTER_API_KEY`` or ``.env``), ``agent`` (one agent session per
figure, through the Claude Code CLI). ``--out DIR`` keeps the step's
folders under
``DIR/<bundle>/figure-to-data`` and leaves the bundles untouched (benchmarks,
trying a method); without it they sit inside each bundle.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from docling.engines.figure_data.evidence import find_source_pdf
from docling.engines.figure_data.methods import build_reader
from docling.engines.figure_data.methods.ollama import OllamaReader
from docling.engines.figure_data.prepare import (
    PREPARE_FILENAME,
    STEP_DIRNAME,
    PrepareManifest,
)
from docling.engines.figure_data.readers.vlm import OllamaClient, OllamaError
from docling.engines.figure_data.schema import (
    Backend,
    FigureDataOptions,
    FigureDataResult,
    FigureMethod,
    PanelSplit,
)
from docling.engines.figure_data.scoring import markdown_report, score_dirs
from docling.engines.figure_data.step import (
    FigureOutcome,
    StepRun,
    embed_step,
    needs_step,
    prepare_step,
    read_step,
)
from docling.engines.run_snapshot import read_run_record

_log = logging.getLogger(__name__)

# The keys of a step config (configs/figure-to-data/*.toml): the options of
# ``amir-figdata step`` that say how the figures are read. amir-batch takes
# the same file (``--figure-data-config``) under its own option names.
STEP_CONFIG_KEYS = {
    "method": "figure_data",
    "model": "figure_data_model",
    "backend": "figure_data_backend",
    "base_url": "figure_data_base_url",
    "api_key_env": "figure_data_key_env",
    "ollama_url": "figure_data_ollama_url",
    "effort": "figure_data_effort",
    "workers": "figure_data_workers",
}


def load_step_config(path: Path) -> dict[str, Any]:
    """A step config, TOML (Python 3.11 and later) or JSON; a key that is not
    a step option is an error."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import tomllib
        except ImportError:  # Python 3.10
            raise typer.BadParameter(
                "a TOML config needs Python 3.11 or later; give a .json file"
            ) from None
        data = tomllib.loads(text)
    unknown = sorted(set(data) - set(STEP_CONFIG_KEYS))
    if unknown:
        raise typer.BadParameter(
            f"{path.name}: not an option of the figure-to-data step: "
            f"{', '.join(unknown)} (known: {', '.join(STEP_CONFIG_KEYS)})"
        )
    return data


def _step_config(ctx: typer.Context, value: Path | None) -> Path | None:
    """``--config``: the file's values become the defaults of the step's
    options, so an option given on the command line wins."""
    if value is not None:
        ctx.default_map = {**(ctx.default_map or {}), **load_step_config(value)}
    return value


_ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        exists=True,
        dir_okay=False,
        is_eager=True,
        callback=_step_config,
        help=(
            "A step config (configs/figure-to-data/recommended-cloud.toml, "
            "recommended-local.toml); options given here win."
        ),
    ),
]

app = typer.Typer(
    add_completion=False,
    help="Figure-to-data on converted papers: prepare, read, embed; score; Ollama.",
    rich_markup_mode="rich",
)

_Folders = Annotated[
    list[Path] | None,
    typer.Argument(help="Bundle folders, or folders that hold bundles."),
]
_PdfDir = Annotated[
    Path | None,
    typer.Option(help="Folder of the source PDFs (else the path run.json records)."),
]
_Out = Annotated[
    Path | None,
    typer.Option(
        help="Keep the step's folders under DIR/<bundle>/ and leave the bundles as they are."
    ),
]
_Method = Annotated[
    FigureMethod,
    typer.Option(help="ollama (local), cloud (a model behind an API) or agent."),
]
_Model = Annotated[
    str | None,
    typer.Option(help="Model; default: the method's (see FigureDataOptions)."),
]
_BackendOption = Annotated[
    Backend | None,
    typer.Option(
        help="Where the model runs: ollama, openai-compatible (an API endpoint, "
        "see --base-url) or claude-cli (the agent's runtime). Default: the "
        "method's."
    ),
]
_BaseUrl = Annotated[
    str,
    typer.Option(
        help="cloud: the chat-completions endpoint (OpenAI-compatible); "
        "OpenRouter by default, a local Ollama is http://127.0.0.1:11434/v1."
    ),
]
_KeyEnv = Annotated[
    str,
    typer.Option(
        help="cloud: the environment variable (also read from .env) that holds "
        "the endpoint's API key."
    ),
]


class _TestsetFigure(BaseModel):
    id: str
    bundle: Path
    pdf: Path | None = None
    self_ref: str


class _Testset(BaseModel):
    figures: list[_TestsetFigure]


@app.command()
def prepare(
    folders: _Folders = None,
    testset: Annotated[
        Path | None,
        typer.Option(
            help="extrct.figure-data-testset/1 JSON: bundle, pdf, self_ref per figure."
        ),
    ] = None,
    refs: Annotated[
        list[str] | None,
        typer.Option(
            "--refs",
            help="Picture self_refs (#/pictures/N); default: chart candidates.",
        ),
    ] = None,
    pdf_dir: _PdfDir = None,
    out: _Out = None,
    panel_split: Annotated[
        PanelSplit,
        typer.Option(
            help="auto or rules (the same here), gutters (no axes step), off."
        ),
    ] = "auto",
    force: Annotated[
        bool, typer.Option(help="Prepare again what is already prepared.")
    ] = False,
) -> None:
    """Phase 1: capture each chart candidate and its context (no model)."""
    console = Console()
    options = FigureDataOptions(panel_split=panel_split)
    targets: list[tuple[Path, Path | None, list[str] | None]] = []
    if testset is not None:
        spec = _Testset.model_validate_json(testset.read_text(encoding="utf-8"))
        grouped: dict[Path, tuple[Path | None, list[str]]] = {}
        for fig in spec.figures:
            grouped.setdefault(fig.bundle, (fig.pdf, []))[1].append(fig.self_ref)
        targets += [(bundle, pdf, wanted) for bundle, (pdf, wanted) in grouped.items()]
    for bundle in _bundles(folders or []):
        targets.append((bundle, find_source_pdf(bundle, pdf_dir), refs))
    if not targets:
        console.print("[red]No bundles given.[/red]")
        raise typer.Exit(code=2)
    for bundle, pdf, wanted in targets:
        manifest = prepare_step(
            bundle,
            pdf,
            options,
            step_dir=_step_dir(bundle, out),
            refs=wanted,
            force=force,
        )
        console.print(_prepared_line(bundle, pdf, manifest), soft_wrap=True)


@app.command()
def read(
    folders: _Folders = None,
    method: _Method = "ollama",
    model: _Model = None,
    backend: _BackendOption = None,
    only: Annotated[
        list[str] | None,
        typer.Option("--only", help="Figure folders to read (pictures_N)."),
    ] = None,
    base_url: _BaseUrl = FigureDataOptions().cloud_base_url,
    api_key_env: _KeyEnv = FigureDataOptions().cloud_api_key_env,
    ollama_url: Annotated[str, typer.Option()] = FigureDataOptions().ollama_url,
    time_budget: Annotated[
        float, typer.Option(help="Seconds one figure may take.")
    ] = FigureDataOptions().time_budget_s_per_figure,
    call_budget: Annotated[
        float, typer.Option(help="ollama: a call is cut after this many seconds.")
    ] = FigureDataOptions().time_budget_s_per_call,
    panel_split: Annotated[
        PanelSplit,
        typer.Option(
            help="auto: the model lists the charts and the rules cut by its "
            "list (ollama, cloud). rules: the rule splitter alone. ollama "
            "also: gutters, off, vlm."
        ),
    ] = "auto",
    effort: Annotated[
        str,
        typer.Option(
            help="cloud, agent: how hard the model is asked to think "
            "(low, medium, high)."
        ),
    ] = FigureDataOptions().claude_effort,
    unload_after: Annotated[
        bool, typer.Option(help="ollama: unload the model at the end.")
    ] = False,
) -> None:
    """Phase 2: read every prepared figure with one method."""
    console = Console()
    # Model and backend left out take the method's own.
    options = FigureDataOptions.model_validate(
        {
            "method": method,
            "model": model,
            "backend": backend,
            "cloud_base_url": base_url,
            "cloud_api_key_env": api_key_env,
            "ollama_url": ollama_url,
            "time_budget_s_per_figure": time_budget,
            "time_budget_s_per_call": call_budget,
            "panel_split": panel_split,
            "claude_effort": effort,
            "cloud_reasoning_effort": effort,
        }
    )
    step_dirs = _step_dirs(folders or [])
    if not step_dirs:
        console.print("[red]Nothing prepared here; run amir-figdata prepare.[/red]")
        raise typer.Exit(code=2)
    reader = build_reader(options)
    runs: list[StepRun] = []
    try:
        for step_dir in step_dirs:
            console.rule(
                f"{escape(step_dir.parent.name)} · {options.method} · "
                f"{escape(options.model)} ({options.backend})"
            )
            run, _ = read_step(
                step_dir,
                options,
                reader=reader,
                only=only,
                on_result=outcome_printer(console, step_dir.parent.name),
            )
            runs.append(run)
        if unload_after and isinstance(reader, OllamaReader):
            reader.unload()
    finally:
        reader.close()
    console.print(runs_table(runs))


@app.command()
def embed(
    folders: _Folders = None,
    pdf_dir: _PdfDir = None,
    min_confidence: Annotated[
        float,
        typer.Option(
            help="Charts under this median confidence stay out of the exports."
        ),
    ] = FigureDataOptions().min_confidence_for_markdown,
) -> None:
    """Phase 3: write the readings into each bundle's exports."""
    console = Console()
    options = FigureDataOptions(min_confidence_for_markdown=min_confidence)
    for bundle in _bundles(folders or []):
        if not (bundle / STEP_DIRNAME / PREPARE_FILENAME).is_file():
            console.print(f"{escape(bundle.name)}: not prepared, skipped")
            continue
        count = embed_step(bundle, options, pdf_path=find_source_pdf(bundle, pdf_dir))
        console.print(
            f"{escape(bundle.name)}: the records of {count} figure(s) written "
            "into the exports"
        )


@app.command()
def step(
    folders: _Folders = None,
    config: _ConfigOption = None,
    pdf_dir: _PdfDir = None,
    method: _Method = "ollama",
    model: _Model = None,
    backend: _BackendOption = None,
    base_url: _BaseUrl = FigureDataOptions().cloud_base_url,
    api_key_env: _KeyEnv = FigureDataOptions().cloud_api_key_env,
    ollama_url: Annotated[str, typer.Option()] = FigureDataOptions().ollama_url,
    embed_readings: Annotated[
        bool,
        typer.Option(
            "--embed/--no-embed", help="Write the readings into the bundles' exports."
        ),
    ] = True,
    force: Annotated[
        bool,
        typer.Option(
            help="Prepare and read again a bundle this method and model already read."
        ),
    ] = False,
    effort: Annotated[
        str | None,
        typer.Option(
            help="cloud, agent: how hard the model is asked to think "
            "(low, medium, high). Default: the method's own."
        ),
    ] = None,
    workers: Annotated[
        int,
        typer.Option(
            min=1,
            help="cloud, agent: bundles read at the same time, each in a "
            "process of its own (ollama reads one figure at a time).",
        ),
    ] = 1,
    unload_after: Annotated[
        bool, typer.Option(help="ollama: unload the model at the end.")
    ] = False,
) -> None:
    """The whole step on finished bundles: prepare, read, embed."""
    console = Console()
    options = FigureDataOptions.model_validate(
        {
            "method": method,
            "model": model,
            "backend": backend,
            "cloud_base_url": base_url,
            "cloud_api_key_env": api_key_env,
            "ollama_url": ollama_url,
            **(
                {"cloud_reasoning_effort": effort, "claude_effort": effort}
                if effort is not None
                else {}
            ),
        }
    )
    bundles = _bundles(folders or [])
    if not bundles:
        console.print("[red]No bundles given.[/red]")
        raise typer.Exit(code=2)
    if not force:
        # A run that stopped is started again without paying twice.
        done = [bundle for bundle in bundles if not _needs_reading(bundle, options)]
        for bundle in done:
            console.print(
                f"{escape(bundle.name)}: already read by {options.method} "
                f"{escape(options.model)}, left alone (--force reads it again)"
            )
        bundles = [bundle for bundle in bundles if bundle not in done]
    runs = run_on_bundles(
        [(bundle, find_source_pdf(bundle, pdf_dir)) for bundle in bundles],
        options,
        console,
        embed=embed_readings,
        force=force,
        unload_after=unload_after,
        workers=workers,
    )
    console.print(runs_table(runs))


def _needs_reading(bundle: Path, options: FigureDataOptions) -> bool:
    """Whether *bundle* has no reading by this step version, method and
    model, or its last one left figures failed (an endpoint that refused,
    a reply that broke off)."""
    if needs_step(bundle, options):
        return True
    record = read_run_record(bundle)
    block = record.figure_to_data if record is not None else None
    return bool(block and (block.get("figures") or {}).get("failed"))


def run_in_processes(
    bundles: list[tuple[Path, Path | None]],
    options: FigureDataOptions,
    console: Console,
    *,
    workers: int,
    embed: bool = True,
    force: bool = False,
) -> list[StepRun]:
    """The step on each (bundle, PDF), *workers* bundles at a time, each in
    a process of its own: pdfium, which renders the crops, is not
    thread-safe. A bundle the step fails on is reported and left as it was."""
    runs: list[StepRun] = []
    settings = options.model_dump_json()
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context("spawn")
    ) as pool:
        futures = {
            pool.submit(
                _one_bundle,
                str(bundle),
                str(pdf) if pdf is not None else None,
                settings,
                embed,
                force,
            ): bundle
            for bundle, pdf in bundles
        }
        for future in as_completed(futures):
            bundle = futures[future]
            try:
                runs.append(future.result())
            except Exception as exc:
                _log.exception("figure-to-data failed on %s", bundle)
                console.print(
                    f"[red]figure-to-data failed[/red] on {escape(bundle.name)}: "
                    f"{escape(type(exc).__name__)}: {escape(str(exc)[:200])}"
                )
    return runs


def _one_bundle(
    bundle: str, pdf: str | None, settings: str, embed: bool, force: bool
) -> StepRun:
    """The step on one bundle, in a worker process."""
    options = FigureDataOptions.model_validate_json(settings)
    console = Console()
    bundle_dir, pdf_path = Path(bundle), Path(pdf) if pdf is not None else None
    manifest = prepare_step(bundle_dir, pdf_path, options, force=force)
    console.print(_prepared_line(bundle_dir, pdf_path, manifest), soft_wrap=True)
    run, _ = read_step(
        bundle_dir / STEP_DIRNAME,
        options,
        on_result=outcome_printer(console, bundle_dir.name),
    )
    if embed:
        run.embedded = embed_step(bundle_dir, options, pdf_path=pdf_path)
    return run


def run_on_bundles(
    bundles: list[tuple[Path, Path | None]],
    options: FigureDataOptions,
    console: Console,
    *,
    embed: bool = True,
    force: bool = False,
    unload_after: bool = False,
    workers: int = 1,
) -> list[StepRun]:
    """The step on each (bundle, PDF) with one reader, so that a local
    model is loaded once for all of them; with several *workers* (not for
    ollama) each bundle in a process of its own."""
    if workers > 1 and options.method != "ollama" and len(bundles) > 1:
        return run_in_processes(
            bundles, options, console, workers=workers, embed=embed, force=force
        )
    reader = build_reader(options)
    runs: list[StepRun] = []
    try:
        for bundle, pdf in bundles:
            manifest = prepare_step(bundle, pdf, options, force=force)
            console.print(_prepared_line(bundle, pdf, manifest), soft_wrap=True)
            run, _ = read_step(
                bundle / STEP_DIRNAME,
                options,
                reader=reader,
                on_result=outcome_printer(console, bundle.name),
            )
            if embed:
                run.embedded = embed_step(bundle, options, pdf_path=pdf)
            runs.append(run)
        if unload_after and isinstance(reader, OllamaReader):
            reader.unload()
    finally:
        reader.close()
    return runs


@app.command()
def score(
    truth_dir: Annotated[Path, typer.Argument(help="Ground-truth JSON files.")],
    pred_dir: Annotated[
        Path, typer.Argument(help="Folder of predicted figure-data JSON files.")
    ],
    out: Annotated[
        Path | None, typer.Option(help="Write score.json + score.md here.")
    ] = None,
) -> None:
    """Score predictions against ground truth."""
    report = score_dirs(truth_dir, pred_dir)
    text = markdown_report(report)
    typer.echo(text)
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "score.json").write_text(
            report.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (out / "score.md").write_text(text, encoding="utf-8")


@app.command()
def ps(
    ollama_url: Annotated[str, typer.Option()] = FigureDataOptions().ollama_url,
) -> None:
    """Models Ollama holds in memory (``ollama ps``)."""
    client = OllamaClient(ollama_url)
    try:
        models = client.ps()
    except OllamaError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    finally:
        client.close()
    for m in models:
        typer.echo(
            f"{m.name}\tsize {m.size / 1e9:.1f} GB\tvram {m.size_vram / 1e9:.1f} GB"
            f"\tctx {m.context_length}\tuntil {m.expires_at}"
        )


@app.command()
def unload(
    model: Annotated[str, typer.Argument()],
    ollama_url: Annotated[str, typer.Option()] = FigureDataOptions().ollama_url,
) -> None:
    """Unload a model from GPU memory (keep_alive 0)."""
    client = OllamaClient(ollama_url)
    try:
        client.unload(model)
    finally:
        client.close()


def _bundles(folders: list[Path]) -> list[Path]:
    """Each folder that is a bundle, else the bundles directly inside it."""
    found: list[Path] = []
    for folder in folders:
        if (folder / "document.json").is_file():
            found.append(folder)
        elif folder.is_dir():
            found += sorted(
                child
                for child in folder.iterdir()
                if (child / "document.json").is_file()
            )
    return found


def _step_dir(bundle: Path, out: Path | None) -> Path:
    return (out / bundle.name if out is not None else bundle) / STEP_DIRNAME


def _step_dirs(folders: list[Path]) -> list[Path]:
    """The prepared step folders at, in, or one level under each folder."""
    found: list[Path] = []
    for folder in folders:
        if (folder / PREPARE_FILENAME).is_file():
            found.append(folder)
        elif (folder / STEP_DIRNAME / PREPARE_FILENAME).is_file():
            found.append(folder / STEP_DIRNAME)
        elif folder.is_dir():
            found += sorted(
                child / STEP_DIRNAME
                for child in folder.iterdir()
                if (child / STEP_DIRNAME / PREPARE_FILENAME).is_file()
            )
    return found


def _prepared_line(bundle: Path, pdf: Path | None, manifest: PrepareManifest) -> str:
    return (
        f"{escape(bundle.name)}: {len(manifest.prepared)} figure(s) prepared of "
        f"{len(manifest.figures)} picture(s), pdf={'yes' if pdf else 'no (bundle crops)'}"
    )


def outcome_printer(
    console: Console, bundle: str
) -> Callable[[FigureOutcome, FigureDataResult], None]:
    def show(outcome: FigureOutcome, result: FigureDataResult) -> None:
        cost = f", ${outcome.cost_usd:.3f}" if outcome.cost_usd is not None else ""
        tools = (
            f", {outcome.tool_calls} tool call(s)"
            if outcome.tool_calls is not None
            else ""
        )
        console.print(
            f"{escape(bundle)} {outcome.folder}: {outcome.status}, "
            f"{outcome.charts} chart(s), {outcome.values} value(s), "
            f"{outcome.seconds:.1f}s, {outcome.calls} call(s){tools}, tokens "
            f"in {outcome.input_tokens}/out {outcome.output_tokens}{cost}, "
            f"{len(result.issues)} issue(s)"
            + (f" · {escape(outcome.reason[:120])}" if outcome.reason else ""),
            soft_wrap=True,
        )

    return show


def runs_table(runs: list[StepRun]) -> Table:
    table = Table(title="figure-to-data")
    for column in (
        "bundle",
        "method",
        "figures",
        "read",
        "no data",
        "not read",
        "failed",
        "values",
        "s",
        "cost $",
        "embedded",
    ):
        table.add_column(column)
    for run in runs:
        counts = run.counts()
        costs = [f.cost_usd for f in run.figures if f.cost_usd is not None]
        table.add_row(
            run.bundle,
            f"{run.method} ({run.model})",
            str(len(run.figures)),
            str(counts.get("read", 0)),
            str(counts.get("no_data", 0)),
            str(counts.get("not_read", 0)),
            str(counts.get("failed", 0)),
            str(sum(f.values for f in run.figures)),
            f"{run.seconds:.0f}",
            f"{sum(costs):.2f}" if costs else "-",
            "-" if run.embedded is None else str(run.embedded),
        )
    return table


if __name__ == "__main__":
    app()
