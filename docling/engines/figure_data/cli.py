# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""``amir-figdata`` — figure-to-data on existing bundles, scoring, Ollama.

    amir-figdata run samples/out/AMIE-Mx --pdf-dir samples --mode measured \\
        --model gemma4:26b-a4b-it-q8_0 --out /tmp/figdata
    amir-figdata run --testset tests/data/figure_data/testset-5.json --out /tmp/figdata
    amir-figdata score truth/ /tmp/figdata
    amir-figdata ps
    amir-figdata unload gemma4:26b-a4b-it-q8_0

``run`` reads bundles without changing them (``--publish`` writes the
results into the bundle instead): per figure ``<out>/<bundle>/pictures_N.json``
(``extrct.figure-data/1``), ``overlay_pictures_N.png`` and the work image,
and for the run ``timing.json`` / ``timing.md`` (seconds, Ollama durations
and tokens, ``ollama ps`` memory per figure).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from docling.engines.figure_data.evidence import (
    find_source_pdf,
    load_bundle,
)
from docling.engines.figure_data.pipeline import eligible_refs, read_bundle
from docling.engines.figure_data.publish import publish_to_bundle
from docling.engines.figure_data.readers.vlm import OllamaClient, OllamaError
from docling.engines.figure_data.schema import (
    FigureDataMode,
    FigureDataOptions,
    FigureDataResult,
    PanelSplit,
)
from docling.engines.figure_data.scoring import markdown_report, score_dirs

app = typer.Typer(
    add_completion=False,
    help="Figure-to-data on bundles: run, score, inspect Ollama.",
    rich_markup_mode="rich",
)


class TimingRow(BaseModel):
    bundle: str
    self_ref: str
    mode: str
    model: str | None
    source_kind: str
    panel_split: str | None
    panels: int
    rows: int
    seconds: float
    calls: int
    prompt_tokens: int
    eval_tokens: int
    load_s: float
    gpu_bytes: int | None
    model_bytes: int | None
    issues: int


class _TestsetFigure(BaseModel):
    id: str
    bundle: Path
    pdf: Path | None = None
    self_ref: str


class _Testset(BaseModel):
    figures: list[_TestsetFigure]


@app.command()
def run(
    bundles: Annotated[
        list[Path] | None, typer.Argument(help="Bundle folders (document.json).")
    ] = None,
    testset: Annotated[
        Path | None,
        typer.Option(
            help="extrct.figure-data-testset/1 JSON: bundle, pdf, self_ref per figure."
        ),
    ] = None,
    refs: Annotated[
        list[str] | None,
        typer.Option(
            "--refs", help="Picture self_refs (#/pictures/N); default: eligible charts."
        ),
    ] = None,
    pdf_dir: Annotated[
        Path | None,
        typer.Option(help="Folder of the source PDFs (else run.json's path)."),
    ] = None,
    mode: Annotated[
        FigureDataMode, typer.Option(help="simple or measured.")
    ] = "measured",
    model: Annotated[
        str, typer.Option(help="Ollama model.")
    ] = FigureDataOptions().model,
    samples: Annotated[
        int, typer.Option(min=1, help="Reads per panel; > 1 adds agreement.")
    ] = 1,
    out: Annotated[Path, typer.Option(help="Output folder.")] = Path("figure_data_out"),
    panel_split: Annotated[PanelSplit, typer.Option(help="auto, off or vlm.")] = "auto",
    keep_alive: Annotated[str, typer.Option(help="Ollama keep_alive.")] = "10m",
    time_budget: Annotated[
        float, typer.Option(help="Seconds of VLM calls per figure.")
    ] = 120.0,
    ollama_url: Annotated[str, typer.Option()] = FigureDataOptions().ollama_url,
    no_model: Annotated[
        bool,
        typer.Option("--no-model", help="Geometry only (vector reader), no VLM calls."),
    ] = False,
    publish: Annotated[
        bool, typer.Option(help="Also write the results into each bundle.")
    ] = False,
    unload_after: Annotated[
        bool, typer.Option(help="Unload the model at the end.")
    ] = False,
) -> None:
    """Read chart data from bundle figures."""
    console = Console()
    options = FigureDataOptions(
        mode=mode,
        model=model,
        samples=samples,
        panel_split=panel_split,
        keep_alive=keep_alive,
        time_budget_s_per_figure=time_budget,
        ollama_url=ollama_url,
    )
    targets: list[tuple[Path, Path | None, list[str] | None]] = []
    if testset is not None:
        spec = _Testset.model_validate_json(testset.read_text(encoding="utf-8"))
        grouped: dict[Path, tuple[Path | None, list[str]]] = {}
        for fig in spec.figures:
            grouped.setdefault(fig.bundle, (fig.pdf, []))[1].append(fig.self_ref)
        targets += [(b, pdf, r) for b, (pdf, r) in grouped.items()]
    for bundle in bundles or []:
        targets.append((bundle, find_source_pdf(bundle, pdf_dir), refs))
    if not targets:
        console.print("[red]No bundles given.[/red]")
        raise typer.Exit(code=2)

    client = (
        None
        if no_model
        else OllamaClient(ollama_url, timeout_s=options.request_timeout_s)
    )
    timing: list[TimingRow] = []
    try:
        for bundle_dir, pdf_path, wanted in targets:
            bundle = load_bundle(bundle_dir, pdf_path)
            figure_refs = wanted or eligible_refs(bundle, options)
            console.rule(
                f"{escape(bundle.name)} · {len(figure_refs)} figure(s) · "
                f"pdf={'yes' if pdf_path else 'no'} · {mode} · {model if client else 'no model'}"
            )

            def report(result: FigureDataResult, bundle_dir: Path = bundle_dir) -> None:
                row = _timing_row(bundle_dir, result, model if client else None)
                timing.append(row)
                console.print(_figure_line(row, result), soft_wrap=True)

            results = read_bundle(
                bundle,
                figure_refs,
                options,
                out_dir=out / bundle.name,
                client=client,
                on_result=report,
            )
            if publish:
                publish_to_bundle(
                    bundle_dir,
                    results,
                    min_confidence=options.min_confidence_for_markdown,
                    pdf_path=pdf_path,
                )
        if client is not None and unload_after:
            client.unload(model)
    finally:
        if client is not None:
            client.close()
    out.mkdir(parents=True, exist_ok=True)
    (out / "timing.json").write_text(
        json.dumps([r.model_dump() for r in timing], indent=2) + "\n", encoding="utf-8"
    )
    (out / "run_options.json").write_text(
        options.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (out / "timing.md").write_text(_timing_markdown(timing), encoding="utf-8")
    console.print(_timing_table(timing))
    console.print(
        f"Wrote {escape(str(out))}/<bundle>/pictures_N.json, overlays, timing.json"
    )


@app.command()
def score(
    truth_dir: Annotated[Path, typer.Argument(help="Ground-truth JSON files.")],
    pred_dir: Annotated[
        Path, typer.Argument(help="Prediction folder (amir-figdata run --out).")
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


def _timing_row(
    bundle_dir: Path, result: FigureDataResult, model: str | None
) -> TimingRow:
    chart = result.chart_data
    running = next((m for m in result.ollama_ps if m.name == model), None)
    return TimingRow(
        bundle=bundle_dir.as_posix(),
        self_ref=chart.figure.self_ref if chart.figure else "",
        mode=result.mode,
        model=model,
        source_kind=chart.source_kind,
        panel_split=result.panel_split,
        panels=len(chart.panels),
        rows=sum(len(p.data) for p in chart.panels),
        seconds=result.seconds,
        calls=len(result.calls),
        prompt_tokens=result.prompt_tokens,
        eval_tokens=result.eval_tokens,
        load_s=round(sum(c.load_s or 0.0 for c in result.calls), 2),
        gpu_bytes=running.size_vram if running else None,
        model_bytes=running.size if running else None,
        issues=len(result.issues),
    )


def _figure_line(row: TimingRow, result: FigureDataResult) -> str:
    calls = " ".join(
        f"[{c.panel or c.prompt}: {c.wall_s:.1f}s p{c.prompt_tokens} e{c.eval_tokens}]"
        for c in result.calls
    )
    gpu = f"{row.gpu_bytes / 1e9:.1f} GB" if row.gpu_bytes else "-"
    return (
        f"{escape(Path(row.bundle).name)} {row.self_ref}: {row.source_kind}, "
        f"{row.panels} panel(s) ({row.panel_split}), {row.rows} rows, "
        f"{row.seconds:.1f}s, {row.calls} call(s), tokens p{row.prompt_tokens}/e{row.eval_tokens}, "
        f"load {row.load_s:.1f}s, GPU {gpu}, {row.issues} issue(s) {escape(calls)}"
    )


def _timing_table(rows: list[TimingRow]) -> Table:
    table = Table(title="figure-data timing")
    for col in (
        "figure",
        "kind",
        "panels",
        "rows",
        "s",
        "calls",
        "prompt tok",
        "eval tok",
        "GPU GB",
    ):
        table.add_column(col)
    for r in rows:
        table.add_row(
            f"{Path(r.bundle).name} {r.self_ref}",
            r.source_kind,
            str(r.panels),
            str(r.rows),
            f"{r.seconds:.1f}",
            str(r.calls),
            str(r.prompt_tokens),
            str(r.eval_tokens),
            f"{r.gpu_bytes / 1e9:.1f}" if r.gpu_bytes else "-",
        )
    return table


def _timing_markdown(rows: list[TimingRow]) -> str:
    lines = [
        "| figure | source | split | panels | rows | s | calls | prompt tok | eval tok | load s | GPU GB |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {Path(r.bundle).name} {r.self_ref} | {r.source_kind} | {r.panel_split} "
            f"| {r.panels} | {r.rows} | {r.seconds:.1f} | {r.calls} | {r.prompt_tokens} "
            f"| {r.eval_tokens} | {r.load_s:.1f} "
            f"| {f'{r.gpu_bytes / 1e9:.1f}' if r.gpu_bytes else '-'} |"
        )
    total = sum(r.seconds for r in rows)
    lines.append(f"\nTotal {total:.1f} s over {len(rows)} figure(s).")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    app()
