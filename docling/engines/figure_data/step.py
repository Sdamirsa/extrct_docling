# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The figure-to-data step: prepare, read, embed.

It runs on a finished bundle, never inside a conversion, so the same code
serves the three ways it is started: after each PDF of a batch, once at the
end of a batch, or later on any output folder (``amir-figdata step``).

1. **prepare** (:mod:`.prepare`, no model): the figure at high resolution,
   its context, its evidence, in ``figure-to-data/<pictures_N>/``.
2. **read** (:mod:`.methods`): one of ``ollama``, ``cloud``, ``agent`` turns
   each prepared figure into ``figure-to-data.md`` and ``.json`` beside its
   inputs. What was run, with which options and prompts, and what came of
   each figure is kept as ``figure-to-data/runs/<run id>.json``.
3. **embed** (:mod:`.publish`): the reading goes into the paper's exports at
   the figure, marked as read by a model.

A figure that fails, or a model that is unreachable, is recorded and does
not stop the others; nothing here changes the status of the conversion.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from docling.engines.figure_data.evidence import BundleSource, load_bundle
from docling.engines.figure_data.methods import FigureReader, build_reader
from docling.engines.figure_data.prepare import (
    STEP_DIRNAME,
    STEP_VERSION,
    PreparedFigure,
    PrepareManifest,
    load_manifest,
    prepare_bundle,
)
from docling.engines.figure_data.publish import RUN_BLOCK_KEY, embed_results
from docling.engines.figure_data.report import (
    READING_JSON,
    READING_MD,
    embed_note,
    figure_markdown,
)
from docling.engines.figure_data.schema import (
    ChartData,
    FigureDataOptions,
    FigureDataResult,
)

_log = logging.getLogger(__name__)

RUNS_DIRNAME = "runs"
RESULT_FILENAME = "result.json"
README_FILENAME = "README.md"
RUN_SCHEMA = "extrct.figure-to-data-run/1"
_UNSAFE = re.compile(r"[^\w.-]+")

Status = Literal["read", "no_data", "not_read", "failed"]

README = f"""# figure-to-data

The numbers behind this paper's chart figures, read from the figure images
by a model. Nothing in this folder comes from the paper's text or tables,
and none of it was checked by a person.

- `prepare.json`: every picture of the paper: prepared for reading, or why not.
- `<pictures_N>/figure.png`: the figure, captured from the PDF at high resolution.
- `<pictures_N>/figure.txt`: what the reader was told beside the image.
- `<pictures_N>/evidence.json`: the same evidence for programs.
- `<pictures_N>/{READING_MD}`: the reading, for people and agents.
- `<pictures_N>/{READING_JSON}`: the same reading, `extrct.figure-data/1`.
- `<pictures_N>/{RESULT_FILENAME}`: how that reading was obtained (calls, time, checks).
- `{RUNS_DIRNAME}/<run id>.json`: each run of the step: method, model,
  options, prompts, and what came of every figure.

A figure folder holds the reading of the latest run. Written by
`amir-figdata` (extrct_docling), step version {STEP_VERSION}.
"""


class FigureOutcome(BaseModel):
    """What one run made of one figure."""

    folder: str
    self_ref: str
    status: Status
    reason: str | None = None
    charts: int = 0
    values: int = 0
    seconds: float = 0.0
    calls: int = 0
    tool_calls: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    notes: list[str] = Field(default_factory=list)


class StepRun(BaseModel):
    """``figure-to-data/runs/<run id>.json``."""

    model_config = ConfigDict(validate_by_name=True, serialize_by_alias=True)

    schema_id: str = Field(default=RUN_SCHEMA, alias="schema")
    run_id: str
    step_version: str = STEP_VERSION
    bundle: str
    method: str
    backend: str
    model: str
    started: str
    seconds: float = 0.0
    options: dict[str, Any] = Field(default_factory=dict)
    reader: dict[str, Any] = Field(default_factory=dict)
    figures: list[FigureOutcome] = Field(default_factory=list)
    embedded: int | None = None

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for outcome in self.figures:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
        return counts

    def block(self) -> dict[str, Any]:
        """The ``figure_to_data`` block of the bundle's ``run.json``."""
        costs = [f.cost_usd for f in self.figures if f.cost_usd is not None]
        return {
            "step_version": self.step_version,
            "run_id": self.run_id,
            "method": self.method,
            "backend": self.backend,
            "model": self.model,
            "ran_at": self.started,
            "seconds": self.seconds,
            "figures": self.counts(),
            "values": sum(f.values for f in self.figures),
            "cost_usd": round(sum(costs), 4) if costs else None,
            "embedded": self.embedded,
            "record": f"{STEP_DIRNAME}/{RUNS_DIRNAME}/{self.run_id}.json",
        }


def run_id_for(options: FigureDataOptions) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{stamp}_{options.method}_{_UNSAFE.sub('-', options.model)}"


def prepare_step(
    bundle_dir: Path,
    pdf_path: Path | None,
    options: FigureDataOptions,
    *,
    step_dir: Path | None = None,
    refs: list[str] | None = None,
    force: bool = False,
) -> PrepareManifest:
    """Phase 1. What an earlier call prepared with the same settings is
    kept (the readings with it) unless *force*."""
    target = step_dir or bundle_dir / STEP_DIRNAME
    existing = load_manifest(target)
    if existing is not None and not force and _still_valid(existing, options, refs):
        return existing
    bundle: BundleSource = load_bundle(bundle_dir, pdf_path)
    manifest = prepare_bundle(bundle, options, step_dir=target, refs=refs)
    (target / README_FILENAME).write_text(README, encoding="utf-8")
    return manifest


def read_step(
    step_dir: Path,
    options: FigureDataOptions,
    *,
    reader: FigureReader | None = None,
    only: list[str] | None = None,
    on_result: Callable[[FigureOutcome, FigureDataResult], None] | None = None,
) -> tuple[StepRun, list[FigureDataResult]]:
    """Phase 2: read every prepared figure under *step_dir* (or the
    folders *only*) with ``options.method``; each figure's files are written
    as soon as it is read, the run record at the end."""
    manifest = load_manifest(step_dir)
    if manifest is None:
        raise FileNotFoundError(f"{step_dir} is not prepared (no prepare.json)")
    own_reader = reader is None
    active = reader if reader is not None else build_reader(options)
    run = StepRun(
        run_id=run_id_for(options),
        bundle=manifest.bundle,
        method=options.method,
        backend=options.backend,
        model=options.model,
        started=time.strftime("%Y-%m-%dT%H:%M:%S"),
        options=options.model_dump(mode="json"),
        reader=active.describe(),
    )
    started = time.perf_counter()
    results: list[FigureDataResult] = []
    try:
        for row in manifest.prepared:
            if row.folder is None or (only is not None and row.folder not in only):
                continue
            figure_dir = step_dir / row.folder
            prepared = PreparedFigure.load(figure_dir)
            result = _read_one(active, prepared, figure_dir, options)
            outcome = _outcome(row.folder, result)
            write_reading(
                figure_dir,
                result,
                prepared,
                run_id=run.run_id,
                min_confidence=options.min_confidence_for_markdown,
            )
            run.figures.append(outcome)
            results.append(result)
            _write_run(step_dir, run, started)
            if on_result is not None:
                on_result(outcome, result)
    finally:
        if own_reader:
            active.close()
    _write_run(step_dir, run, started)
    return run, results


def write_reading(
    figure_dir: Path,
    result: FigureDataResult,
    prepared: PreparedFigure,
    *,
    run_id: str,
    min_confidence: float,
) -> None:
    """``figure-to-data.json``, ``figure-to-data.md`` and ``result.json`` of
    one figure."""
    (figure_dir / READING_JSON).write_text(
        json.dumps(result.chart_data.dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (figure_dir / READING_MD).write_text(
        figure_markdown(result, prepared, run_id=run_id, min_confidence=min_confidence),
        encoding="utf-8",
    )
    (figure_dir / RESULT_FILENAME).write_text(
        result.model_dump_json(indent=1, exclude={"chart_data", "overlay"}) + "\n",
        encoding="utf-8",
    )


def embed_step(
    bundle_dir: Path,
    options: FigureDataOptions,
    *,
    step_dir: Path | None = None,
    pdf_path: Path | None = None,
) -> int:
    """Phase 3: put the readings under *step_dir* into the bundle's exports.
    Works from the files alone, so it can be repeated at any time."""
    target = step_dir or bundle_dir / STEP_DIRNAME
    manifest = load_manifest(target)
    if manifest is None:
        raise FileNotFoundError(f"{target} is not prepared (no prepare.json)")
    results: list[FigureDataResult] = []
    for row in manifest.prepared:
        loaded = load_reading(target / row.folder) if row.folder else None
        if loaded is not None:
            results.append(loaded)
    run = latest_run(target)
    block = run.block() if run is not None else {"step_version": STEP_VERSION}
    embedded = embed_results(
        bundle_dir,
        [(result, embed_note(result)) for result in results],
        min_confidence=options.min_confidence_for_markdown,
        run_block={**block, "embedded": len(results)},
        pdf_path=pdf_path,
    )
    if run is not None:
        run.embedded = embedded
        (target / RUNS_DIRNAME / f"{run.run_id}.json").write_text(
            run.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    return embedded


def run_step(
    bundle_dir: Path,
    pdf_path: Path | None,
    options: FigureDataOptions,
    *,
    reader: FigureReader | None = None,
    embed: bool = True,
    on_result: Callable[[FigureOutcome, FigureDataResult], None] | None = None,
) -> StepRun:
    """The whole step on one bundle: prepare what is not prepared, read it
    with ``options.method``, embed the readings."""
    step_dir = bundle_dir / STEP_DIRNAME
    prepare_step(bundle_dir, pdf_path, options)
    run, _ = read_step(step_dir, options, reader=reader, on_result=on_result)
    if embed:
        run.embedded = embed_step(bundle_dir, options, pdf_path=pdf_path)
    return run


def load_reading(figure_dir: Path) -> FigureDataResult | None:
    """A figure's reading as the last run left it, or None before any run."""
    record, how = figure_dir / READING_JSON, figure_dir / RESULT_FILENAME
    if not record.is_file() or not how.is_file():
        return None
    chart = ChartData.model_validate_json(record.read_text(encoding="utf-8"))
    fields = json.loads(how.read_text(encoding="utf-8"))
    return FigureDataResult(chart_data=chart, **fields)


def latest_run(step_dir: Path) -> StepRun | None:
    runs = sorted((step_dir / RUNS_DIRNAME).glob("*.json"))
    if not runs:
        return None
    return StepRun.model_validate_json(runs[-1].read_text(encoding="utf-8"))


def needs_step(bundle_dir: Path, options: FigureDataOptions) -> bool:
    """Whether the bundle has not had this step with this method and model
    (its ``run.json`` says which run was embedded last)."""
    path = bundle_dir / "run.json"
    if not path.is_file():
        return True
    try:
        block = json.loads(path.read_text(encoding="utf-8")).get(RUN_BLOCK_KEY)
    except ValueError:
        return True
    if not isinstance(block, dict):
        return True
    return (
        block.get("step_version"),
        block.get("method"),
        block.get("backend"),
        block.get("model"),
    ) != (STEP_VERSION, options.method, options.backend, options.model)


def _read_one(
    reader: FigureReader,
    prepared: PreparedFigure,
    figure_dir: Path,
    options: FigureDataOptions,
) -> FigureDataResult:
    started = time.perf_counter()
    try:
        return reader.read(prepared, figure_dir)
    except Exception as exc:
        # One figure a reader chokes on (a reply no code expected, a broken
        # image) must not take the other figures of the batch with it.
        _log.exception("figure-to-data: %s failed", figure_dir)
        return FigureDataResult(
            chart_data=ChartData(
                figure=prepared.figure,
                source_kind=prepared.source_kind,
                uncertain=[f"not read: the reader failed ({type(exc).__name__})"],
            ),
            method=options.method,
            backend=options.backend,
            model=options.model,
            seconds=round(time.perf_counter() - started, 2),
            issues=[f"reader failed: {type(exc).__name__}: {str(exc)[:300]}"],
        )


def _outcome(folder: str, result: FigureDataResult) -> FigureOutcome:
    chart = result.chart_data
    values = sum(len(panel.data) for panel in chart.panels)
    first = chart.uncertain[0] if chart.uncertain else None
    failed = [
        issue for issue in result.issues if "failed" in issue or "session:" in issue
    ]
    status: Status
    if values:
        status, reason = "read", None
    elif first is not None and first.startswith("not a data chart"):
        status, reason = "no_data", first
    elif failed:
        status, reason = "failed", failed[0]
    else:
        status, reason = "not_read", first or "no values returned"
    costs = [c.cost_usd for c in result.calls if c.cost_usd is not None]
    tools = [c.tool_calls for c in result.calls if c.tool_calls is not None]
    return FigureOutcome(
        folder=folder,
        self_ref=chart.figure.self_ref if chart.figure is not None else "",
        status=status,
        reason=reason[:400] if reason else None,
        charts=len(chart.panels),
        values=values,
        seconds=result.seconds,
        calls=len(result.calls),
        tool_calls=sum(tools) if tools else None,
        input_tokens=result.prompt_tokens,
        output_tokens=result.eval_tokens,
        cost_usd=round(sum(costs), 4) if costs else None,
        notes=[issue[:400] for issue in result.issues] + chart.uncertain,
    )


def _write_run(step_dir: Path, run: StepRun, started: float) -> None:
    run.seconds = round(time.perf_counter() - started, 2)
    runs = step_dir / RUNS_DIRNAME
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{run.run_id}.json").write_text(
        run.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


def _still_valid(
    manifest: PrepareManifest, options: FigureDataOptions, refs: list[str] | None
) -> bool:
    if (
        manifest.step_version != STEP_VERSION
        or manifest.crop_dpi != options.crop_dpi
        or manifest.panel_split != options.panel_split
    ):
        return False
    return manifest.selection == (sorted(refs) if refs is not None else None)
