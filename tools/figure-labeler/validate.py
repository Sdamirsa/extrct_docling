"""Validate figure labels against ``extrct.figure-data/1`` and print a summary.

Usage::

    uv run --no-sync python tools/figure-labeler/validate.py <pack_or_labels_dir_or_json>...
    uv run --no-sync python tools/figure-labeler/validate.py --write-schema schema.json

A pack folder (one with ``manifest.js``) is read from its ``labels/`` folder and
compared with the manifest, so unlabelled figures are listed too. Exit status
is 1 when any file is invalid.

The pydantic models below mirror the schema section of
``.claude/reference/figure-data/DESIGN.md`` and are stricter than the engine's
``docling.engines.figure_data.schema.ChartData`` (every key present, enums and
bounds enforced, no unknown fields), so ground truth is complete. When the
engine is importable, each valid label is also loaded as ``ChartData`` to prove
the scorer can read it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

SCHEMA_ID = "extrct.figure-data/1"

PanelKind = Literal[
    "bar",
    "stacked_bar",
    "grouped_bar",
    "line",
    "scatter",
    "box",
    "forest",
    "kaplan_meier",
    "pie",
    "heatmap",
    "other",
]
Source = Literal["printed", "vector", "raster", "vlm", "human", "agent"]
Box = tuple[float, float, float, float]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FigureRef(_Strict):
    bundle: str = Field(min_length=1)
    self_ref: str = Field(pattern=r"^#/pictures/\d+$")
    image_path: str | None
    page: int | None = Field(ge=1)
    bbox: Box | None = Field(
        description="Picture box on the page in PDF points [l, t, r, b] from the "
        "top-left of the page (Docling's frame, as in the engine schema)."
    )


class Axis(_Strict):
    name: str | None
    unit: str | None
    scale: Literal["linear", "log", "categorical"] | None
    range: tuple[float, float] | None
    ticks: list[float | str] | None


class Axes(_Strict):
    x: Axis | None
    y: Axis | None


class Series(_Strict):
    name: str = Field(min_length=1)
    color: str | None


class Value(_Strict):
    category: str | None
    x: float | str | None
    series: str | None
    value: float | None = Field(
        description="Plotted quantity in axis units; null when unreadable."
    )
    err_lo: float | None = Field(
        description="Absolute lower error position, not a delta."
    )
    err_hi: float | None = Field(
        description="Absolute upper error position, not a delta."
    )
    label_printed: str | None
    source: Source
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _err_order(self) -> Value:
        if (
            self.err_lo is not None
            and self.err_hi is not None
            and self.err_lo > self.err_hi
        ):
            raise ValueError(f"err_lo {self.err_lo} > err_hi {self.err_hi}")
        return self


class Panel(_Strict):
    id: str = Field(min_length=1)
    bbox_px: Box = Field(description="[x0, y0, x1, y1] in pixels of the bundle crop.")
    title: str | None
    kind: PanelKind
    orientation: Literal["vertical", "horizontal"] | None
    axes: Axes | None
    series: list[Series]
    data: list[Value]
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _checks(self) -> Panel:
        x0, y0, x1, y1 = self.bbox_px
        if x0 >= x1 or y0 >= y1:
            raise ValueError(
                f"bbox_px must be [x0, y0, x1, y1] with x0<x1, y0<y1: {self.bbox_px}"
            )
        names = [s.name for s in self.series]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate series names in panel {self.id}: {names}")
        return self


class Labeler(_Strict):
    kind: Literal["human", "agent", "engine"]
    name: str | None
    date: str | None = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_minutes: float | None = Field(ge=0)


class FigureData(_Strict):
    schema_id: Literal["extrct.figure-data/1"] = Field(alias="schema")
    figure: FigureRef
    source_kind: Literal["vector", "raster", "mixed", "unknown"]
    panels: list[Panel]
    labeler: Labeler
    uncertain: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_panel_ids(self) -> FigureData:
        ids = [p.id for p in self.panels]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate panel ids: {ids}")
        return self


def json_schema() -> dict:
    schema = FigureData.model_json_schema(by_alias=True)
    schema["$id"] = SCHEMA_ID
    schema["title"] = "extrct figure data v1 (labels and predictions)"
    return schema


def label_filename(bundle: str, self_ref: str) -> str:
    """``HeartAgent`` + ``#/pictures/1`` -> ``HeartAgent__pictures1.json``."""
    return f"{bundle}__pictures{self_ref.rsplit('/', 1)[-1]}.json"


def read_manifest(pack_dir: Path) -> dict:
    text = (pack_dir / "manifest.js").read_text(encoding="utf-8")
    return json.loads(text.split("=", 1)[1].strip().rstrip(";"))


@dataclass
class Summary:
    valid: list[Path] = field(default_factory=list)
    invalid: dict[Path, list[str]] = field(default_factory=dict)
    panels: int = 0
    rows: int = 0
    null_values: int = 0
    printed: int = 0
    minutes: float = 0.0
    kinds: Counter[str] = field(default_factory=Counter)
    missing: Counter[str] = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)
    labelled: set[str] = field(default_factory=set)
    engine_checked: bool = False


def _missing_fields(fd: FigureData) -> list[str]:
    out: list[str] = []
    if not fd.labeler.name:
        out.append("labeler.name")
    if fd.labeler.time_minutes is None:
        out.append("labeler.time_minutes")
    if fd.source_kind == "unknown":
        out.append("source_kind")
    if not fd.panels:
        out.append("panels (none)")
    for p in fd.panels:
        if not p.title:
            out.append("panel.title")
        if not p.series and p.kind not in {"pie", "heatmap"}:
            out.append("panel.series (none)")
        if not p.data:
            out.append("panel.data (none)")
        if (
            p.kind in {"bar", "stacked_bar", "grouped_bar", "box", "forest"}
            and p.orientation is None
        ):
            out.append("panel.orientation")
        if p.kind not in {"pie"}:
            for key in ("x", "y"):
                axis = getattr(p.axes, key) if p.axes else None
                if axis is None:
                    out.append(f"axes.{key}")
                elif not axis.name:
                    out.append(f"axes.{key}.name")
        out.extend("series.color" for s in p.series if not s.color)
    return out


def _warnings(fd: FigureData, path: Path) -> list[str]:
    out: list[str] = []
    expected = label_filename(fd.figure.bundle, fd.figure.self_ref)
    if path.name != expected:
        out.append(f"{path.name}: file name should be {expected}")
    for p in fd.panels:
        names = {s.name for s in p.series}
        seen: Counter[tuple[str, str]] = Counter()
        for i, v in enumerate(p.data):
            where = f"{path.name} panel {p.id} row {i + 1}"
            if v.series is not None and names and v.series not in names:
                out.append(
                    f"{where}: series {v.series!r} not in panel series {sorted(names)}"
                )
            if v.category is None and v.x is None and p.kind != "pie":
                out.append(f"{where}: neither category nor x")
            if v.value is not None:
                lo, hi = v.err_lo, v.err_hi
                if (lo is not None and v.value < lo) or (
                    hi is not None and v.value > hi
                ):
                    out.append(f"{where}: value {v.value} outside [{lo}, {hi}]")
            seen[
                (str(v.category if v.category is not None else v.x), str(v.series))
            ] += 1
        out.extend(
            f"{path.name} panel {p.id}: {n} rows for (category/x, series) = {key}"
            for key, n in seen.items()
            if n > 1
        )
    return out


def _flatten_errors(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}"
        for err in exc.errors()
    ]


def collect(paths: list[Path]) -> tuple[list[Path], dict | None]:
    """JSON files to check, plus the manifest when a pack folder was given."""
    files: list[Path] = []
    manifest: dict | None = None
    for path in paths:
        if path.is_dir() and (path / "manifest.js").is_file():
            manifest = read_manifest(path)
            files.extend(sorted((path / "labels").glob("*.json")))
        elif path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            files.append(path)
    return files, manifest


def _engine_model() -> type[BaseModel] | None:
    try:
        from docling.engines.figure_data.schema import ChartData
    except ImportError:  # kit used outside the extrct_docling environment
        return None
    return ChartData


def check(files: list[Path]) -> Summary:
    engine = _engine_model()
    summary = Summary(engine_checked=engine is not None)
    for path in files:
        try:
            fd = FigureData.model_validate_json(path.read_bytes(), strict=True)
            if engine is not None:
                engine.model_validate_json(path.read_bytes())
        except ValidationError as exc:
            summary.invalid[path] = _flatten_errors(exc)
            continue
        summary.valid.append(path)
        summary.labelled.add(label_filename(fd.figure.bundle, fd.figure.self_ref))
        summary.panels += len(fd.panels)
        summary.minutes += fd.labeler.time_minutes or 0.0
        for p in fd.panels:
            summary.kinds[p.kind] += 1
            summary.rows += len(p.data)
            summary.null_values += sum(v.value is None for v in p.data)
            summary.printed += sum(v.label_printed is not None for v in p.data)
        summary.missing.update(_missing_fields(fd))
        summary.warnings.extend(_warnings(fd, path))
    return summary


def report(summary: Summary, manifest: dict | None) -> None:
    for path in summary.valid:
        print(f"OK    {path.name}")
    for path, errors in summary.invalid.items():
        print(f"FAIL  {path.name}")
        for err in errors[:20]:
            print(f"        {err}")
        if len(errors) > 20:
            print(f"        ... {len(errors) - 20} more")
    n = len(summary.valid) + len(summary.invalid)
    print(
        f"\nfiles {n}: valid {len(summary.valid)}, invalid {len(summary.invalid)} | "
        f"panels {summary.panels} | rows {summary.rows} "
        f"(value null {summary.null_values}, printed label {summary.printed}) | "
        f"labelling time {summary.minutes:.1f} min"
    )
    print(
        "checked: kit models (strict)"
        + (
            " + engine ChartData"
            if summary.engine_checked
            else " (engine not importable, ChartData check skipped)"
        )
    )
    if summary.kinds:
        print(
            "panel kinds: "
            + ", ".join(f"{k} {v}" for k, v in summary.kinds.most_common())
        )
    if manifest is not None:
        expected = {f"{f['id']}.json" for f in manifest["figures"]}
        todo = sorted(expected - summary.labelled)
        print(
            f"manifest: {len(expected)} figures, labelled {len(expected & summary.labelled)}, unlabelled {len(todo)}"
        )
        for name in todo:
            print(f"  todo  {name}")
    if summary.missing:
        print(
            "missing / empty (count): "
            + ", ".join(f"{k} {v}" for k, v in summary.missing.most_common())
        )
    if summary.warnings:
        print(f"warnings ({len(summary.warnings)}):")
        for w in summary.warnings[:40]:
            print(f"  - {w}")
        if len(summary.warnings) > 40:
            print(f"  ... {len(summary.warnings) - 40} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "paths", nargs="*", type=Path, help="pack folder, labels folder or JSON files"
    )
    parser.add_argument(
        "--write-schema", type=Path, help="write the JSON Schema and exit"
    )
    args = parser.parse_args(argv)
    if args.write_schema:
        args.write_schema.write_text(
            json.dumps(json_schema(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.write_schema}")
        return 0
    if not args.paths:
        parser.error("give a pack folder, a labels folder or JSON files")
    files, manifest = collect(args.paths)
    if not files and manifest is None:
        print("no label files found", file=sys.stderr)
        return 1
    summary = check(files)
    report(summary, manifest)
    return 1 if summary.invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
