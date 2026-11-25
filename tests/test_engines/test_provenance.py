# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for a bundle's provenance page and methods paragraph
(:mod:`docling.engines.provenance`)."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.engines import PdfEngine
from docling.engines.export_check import (
    BundleCheck,
    ChunkCheck,
    ExportFidelity,
    GuardCheck,
    HtmlCoverage,
    LigatureSplits,
    PageRecall,
    StructureCheck,
    TableCheck,
)
from docling.engines.provenance import (
    METHODS_FILENAME,
    PROVENANCE_FILENAME,
    PROVENANCE_SCRIPT_ID,
    build_provenance,
    write_provenance,
)
from docling.engines.run_snapshot import build_run_snapshot
from docling.engines.structure import QualityReport
from docling.utils.text_layer import TextLayerSummary

_STARTED = dt.datetime(2026, 11, 25, 9, 35, tzinfo=dt.timezone.utc)
_FIGURE_DATA = {
    "step_version": "3",
    "method": "cloud",
    "model": "anthropic/claude-sonnet-5.5",
    "figures": {"read": 1, "no_data": 0, "not_read": 0},
    "values": 24,
    "seconds": 12.5,
}


def _run() -> dict[str, Any]:
    """A run.json as the engine writes it with TableFormer, no figure
    descriptions and no figure typing, for a PDF with glyph-order pages."""
    engine = PdfEngine(
        picture_description=None, granite_vision_tables=False, figure_types=False
    )
    options = PdfPipelineOptions(do_picture_classification=True, images_scale=1.5)
    quality = QualityReport(
        pages=12,
        label_counts={"text": 40, "section_header": 6, "table": 2, "picture": 3},
        body_text_items=40,
        section_headers=6,
        text_layer=TextLayerSummary(glyph_order_pages=[2, 3, 4]),
    )
    run = build_run_snapshot(
        source="paper.pdf",
        source_kind="local_path",
        file_name="paper.pdf",
        file_size=1000,
        binary_hash="ab" * 32,
        status="ConversionStatus.SUCCESS",
        complete=True,
        started_at=_STARTED,
        finished_at=_STARTED + dt.timedelta(seconds=42),
        engine_config=engine.engine_config(make_html_preview=True),
        pipeline_options=options.model_dump(mode="json", serialize_as_any=True),
        page_count=12,
        pictures_extracted=3,
        tables_extracted=2,
        errors=[],
        structure_version="1",
        quality=quality.model_dump(mode="json"),
    )
    run["figure_to_data"] = _FIGURE_DATA
    return run


def _check() -> dict[str, Any]:
    return BundleCheck(
        bundle="paper",
        html_coverage=HtmlCoverage(items=51, tagged_once=51),
        page_recall=PageRecall(
            pdf_words=5000,
            document_recall=0.991,
            pages_checked=12,
            min_page=8,
            min_page_recall=0.92,
            issues=["p8: recall 0.92, 50 of 653 words missing (e.g. x)"],
        ),
        export_fidelity=ExportFidelity(html=1.0, md=1.0, chunks=0.999),
        ligature_splits=LigatureSplits(per_export={"md": 0, "html": 0}),
        tables=TableCheck(count=2, by_structure_model={"tableformer": 2}),
        chunks=ChunkCheck(count=20, max_tokens=512),
        structure=StructureCheck(),
        guards=GuardCheck(),
    ).model_dump(mode="json")


def _bundle(tmp_path: Path, run: dict[str, Any], check: dict[str, Any] | None) -> Path:
    pdf_dir = tmp_path / "paper"
    pdf_dir.mkdir()
    (pdf_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    if check is not None:
        (pdf_dir / "check.json").write_text(json.dumps(check), encoding="utf-8")
    return pdf_dir


def _embedded_steps(page: str) -> list[dict[str, Any]]:
    script = re.search(
        rf'<script type="application/json" id="{PROVENANCE_SCRIPT_ID}">(.*?)</script>',
        page,
        re.S,
    )
    assert script is not None
    return json.loads(script.group(1))["steps"]


def test_provenance_follows_what_the_bundle_records(tmp_path: Path) -> None:
    """The steps come out in execution order; steps the options turned off are
    drawn as skipped with the reason; the methods paragraph takes its versions
    and numbers from run.json, and every placeholder of the template is
    filled."""
    run = _run()
    pdf_dir = _bundle(tmp_path, run, _check())
    figures = [
        {"self_ref": "#/pictures/0", "generic_classifier_label": "bar_chart"},
        {"self_ref": "#/pictures/1", "generic_classifier_label": "logo"},
        {
            "self_ref": "#/pictures/2",
            "generic_classifier_label": "logo",
            "is_noise": True,
            "noise_reason": "classifier:logo",
        },
    ]
    (pdf_dir / "figures.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in figures), encoding="utf-8"
    )
    (pdf_dir / "structure.json").write_text(
        json.dumps(
            {
                "structure_version": "1",
                "title_ref": "#/texts/0",
                "outline": [{"ref": f"#/texts/{i}", "level": 1} for i in range(6)],
                "relabels": [{"rule": "rule:caption-pattern"}] * 2,
            }
        ),
        encoding="utf-8",
    )

    written = write_provenance(pdf_dir)

    assert [p.name for p in written] == [PROVENANCE_FILENAME, METHODS_FILENAME]
    page = (pdf_dir / PROVENANCE_FILENAME).read_text(encoding="utf-8")
    steps = {s["key"]: s for s in _embedded_steps(page)}
    assert list(steps) == [
        "parse_pages",
        "text_layer",
        "parser_repair",
        "ocr",
        "layout",
        "layout_cleanup",
        "table_structure",
        "assemble",
        "picture_classifier",
        "picture_description",
        "enrichment",
        "text_repairs",
        "structure",
        "quality",
        "figure_types",
        "noise_filter",
        "exports",
        "self_check",
        "figure_to_data",
    ]
    for key in ("picture_description", "figure_types", "enrichment"):
        assert (steps[key]["state"], steps[key]["reason"]) == ("skipped", "off")
        assert f'st-skipped" id="step-{key}"' in page
    assert steps["parser_repair"]["reason"] == "no page needed it"
    assert steps["text_layer"]["outcome"] == [
        "3 pages decoded from glyph order (p2\N{EN DASH}4)"
    ]
    assert (steps["table_structure"]["model"], steps["table_structure"]["owner"]) == (
        "TableFormer",
        "docling",
    )
    assert steps["noise_filter"]["outcome"] == [
        "1 of 3 pictures marked as noise; classifier:logo 1"
    ]
    assert steps["self_check"]["outcome"][0] == "1 issue: page_recall 1"
    assert steps["figure_to_data"]["phase"] == "figure_data"

    methods = (pdf_dir / METHODS_FILENAME).read_text(encoding="utf-8")
    assert "$" not in methods
    packages = run["environment"]["packages"]
    for expected in (
        f"extrct_docling {run['engine']['version']}",
        f"docling-parse {packages['docling-parse'] or '(version not recorded)'}",
        "On 3 pages, text in fonts without a Unicode map was decoded",
        "Tables were structured with TableFormer (2 tables: TableFormer 2).",
        "Pictures were not described by a vision-language model.",
        "of the 5,000 words of the PDF's text layer",
        "anthropic/claude-sonnet-5.5 (cloud)",
    ):
        assert expected in methods
    for name, version in packages.items():
        if version is not None:
            assert f"- {name} {version}" in methods


def test_a_bundle_of_an_earlier_release_marks_what_it_does_not_record(
    tmp_path: Path,
) -> None:
    """A run.json from before the text-layer check, the parser repair and the
    structure pass, without check.json and figures.jsonl: the steps it has no
    record of say so, the parser repair is left out, and Docling's steps are
    not credited with the fork's later patches."""
    run = _run()
    del run["quality"]["text_layer"], run["structure_version"]
    del run["pipeline_options"]["repair_parser_text"], run["figure_to_data"]
    del run["engine_config"]["figure_types"]
    pdf_dir = _bundle(tmp_path, run, check=None)

    write_provenance(pdf_dir)

    steps = {s.key: s for s in build_provenance(pdf_dir).steps}
    assert "parser_repair" not in steps
    assert "figure_to_data" not in steps
    for key in ("text_layer", "structure", "figure_types", "self_check"):
        assert steps[key].state == "not_recorded", key
    assert steps["self_check"].reason == "no check.json"
    for key in ("ocr", "layout_cleanup", "assemble"):
        assert steps[key].owner == "docling", key
    methods = (pdf_dir / METHODS_FILENAME).read_text(encoding="utf-8")
    assert "$" not in methods
    assert "structure rules" not in methods
    assert "of the PDF's text layer" not in methods


def test_a_converter_supplied_by_the_caller_is_one_unrecorded_docling_step(
    tmp_path: Path,
) -> None:
    """The full-page VLM side of a comparison runs a converter handed to the
    engine: run.json has no pipeline options, so Docling's part is one card
    that says why, followed by the engine's own steps."""
    run = _run()
    run["pipeline_options"], run["models"] = None, {}
    run["engine_config"]["converter_supplied"] = True
    pdf_dir = _bundle(tmp_path, run, _check())

    steps = build_provenance(pdf_dir).steps

    assert steps[0].key == "docling_unrecorded"
    assert steps[0].state == "not_recorded"
    assert "supplied by the caller" in (steps[0].reason or "")
    assert steps[1].key == "text_repairs"
