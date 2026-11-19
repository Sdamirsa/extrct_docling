# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for figure-to-data (:mod:`docling.engines.figure_data`). No model
runs: the Ollama client replays recorded responses through an httpx mock
transport. The step inside ``amir-batch``, end to end, is in
``test_figure_data_batch.py``."""

from __future__ import annotations

import ctypes
import json
import subprocess
from pathlib import Path

import httpx
import numpy as np
import pytest
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)
from docling_core.types.doc.document import RefItem
from rich.console import Console

from docling.engines import check_bundle, export_markdown, write_document_html
from docling.engines.cli import _FigureStep
from docling.engines.figure_data.evidence import (
    AxisMap,
    FigureRow,
    PanelAxes,
    build_job,
    find_axes,
    fit_axis,
    load_bundle,
    merge_words,
    parse_number,
)
from docling.engines.figure_data.methods.agent import POLICY, AgentReader
from docling.engines.figure_data.methods.claude_cli import parse_stream
from docling.engines.figure_data.methods.cloud import CloudReader
from docling.engines.figure_data.methods.endpoint import (
    DOTENV_FILENAME,
    EndpointClient,
    EndpointError,
    api_key,
    text_part,
)
from docling.engines.figure_data.methods.toolbox import FigureToolbox, handle
from docling.engines.figure_data.panels import split_panels
from docling.engines.figure_data.pipeline import read_figure
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.publish import embed_results, get_chart_data
from docling.engines.figure_data.readers.raster import refine_edge
from docling.engines.figure_data.readers.vector import read_vector_panel
from docling.engines.figure_data.readers.vlm import OllamaClient, salvage_json
from docling.engines.figure_data.reading import (
    FigureReading,
    ReadPanel,
    ReadPoint,
    chart_from_reading,
)
from docling.engines.figure_data.schema import (
    SCHEMA_ID,
    Axes,
    Axis,
    ChartData,
    Figure,
    FigureDataOptions,
    FigureDataResult,
    Panel,
    Value,
    Word,
    chart_data_json_schema,
)
from docling.engines.figure_data.scoring import score_figure
from docling.engines.figure_data.step import (
    needs_step,
    prepare_step,
    read_step,
    run_step,
)
from docling.engines.figure_data.verify import (
    apply_printed,
    check_labels,
    pair_printed_labels,
    verify_panel,
)
from docling.engines.serializers import ANNOTATION_CLOSE, CHART_DATA_OPEN

RECORDED = Path("tests/data/figure_data/ollama_recorded.json")
_PAGE = 300.0
_BLUE = (31, 119, 180)
_ORANGE = (255, 127, 14)


# --- a synthetic chart, drawn with pypdfium2 ----------------------------------


def _text(pdf, page, text: str, x: float, y: float, size: float = 8.0) -> None:
    import pypdfium2.raw as pdfium_c

    obj = pdfium_c.FPDFPageObj_NewTextObj(pdf.raw, b"Helvetica", ctypes.c_float(size))
    buffer = (text + "\0").encode("utf-16-le")
    pdfium_c.FPDFText_SetText(
        obj, ctypes.cast(ctypes.c_char_p(buffer), ctypes.POINTER(ctypes.c_ushort))
    )
    pdfium_c.FPDFPageObj_Transform(obj, 1, 0, 0, 1, x, y)
    pdfium_c.FPDFPage_InsertObject(page.raw, obj)


def _rect(
    page, x: float, y: float, w: float, h: float, rgb: tuple[int, int, int]
) -> None:
    import pypdfium2.raw as pdfium_c

    obj = pdfium_c.FPDFPageObj_CreateNewRect(x, y, w, h)
    pdfium_c.FPDFPageObj_SetFillColor(obj, *rgb, 255)
    pdfium_c.FPDFPath_SetDrawMode(obj, pdfium_c.FPDF_FILLMODE_WINDING, False)
    pdfium_c.FPDFPage_InsertObject(page.raw, obj)


def _bar_chart_pdf(
    target: Path,
    stacks: list[tuple[str, list[tuple[float, tuple[int, int, int]]]]],
    *,
    printed: dict[str, str] | None = None,
    sentence: str | None = None,
) -> Path:
    """A 300 pt page: y axis 0..1 from y=60 to y=260 (labels 0, 0.5, 1.0),
    one bar (or stack of segments) per category, 30 pt wide every 50 pt;
    *sentence* is printed under the chart."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(_PAGE, _PAGE)
    for value, label in ((0.0, "0"), (0.5, "0.5"), (1.0, "1.0")):
        width = 0.556 * 8 * (len(label) - (0.5 if "." in label else 0))
        _text(pdf, page, label, 52 - width, 60 + 200 * value - 2.8)
    for i, (category, segments) in enumerate(stacks):
        bottom = 60.0
        for value, colour in segments:
            _rect(page, 80 + 50 * i, bottom, 30, 200 * value, colour)
            bottom += 200 * value
        _text(pdf, page, category, 92 + 50 * i, 45)
        if printed and category in printed:
            _text(pdf, page, printed[category], 85 + 50 * i, bottom + 4)
    if sentence is not None:
        _text(pdf, page, sentence, 40, 18)
    page.gen_content()
    pdf.save(target)
    pdf.close()
    return target


def _chart_bundle(tmp_path: Path, pdf_path: Path) -> Path:
    """A bundle whose only picture is the whole synthetic page."""
    import pypdfium2 as pdfium

    doc = DoclingDocument(name="chart")
    doc.add_page(page_no=1, size=Size(width=_PAGE, height=_PAGE))
    prov = ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(
            l=0, t=_PAGE, r=_PAGE, b=0, coord_origin=CoordOrigin.BOTTOMLEFT
        ),
        charspan=(0, 0),
    )
    doc.add_text(label=DocItemLabel.TEXT, text="Accuracy of three models.", prov=prov)
    doc.add_picture(prov=prov)
    bundle = tmp_path / "chart"
    (bundle / "images").mkdir(parents=True)
    pdf = pdfium.PdfDocument(pdf_path)
    pdf[0].render(scale=1.5).to_pil().save(bundle / "images" / "picture_001.png")
    pdf.close()
    doc.save_as_json(bundle / "document.json")
    row = {
        "index": 0,
        "self_ref": "#/pictures/0",
        "image_path": "images/picture_001.png",
        "figure_type": "bar_chart",
        "is_noise": False,
        "caption_text": "",
    }
    (bundle / "figures.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    return bundle


def _job(tmp_path: Path, stacks, *, printed=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    pdf = _bar_chart_pdf(tmp_path / "chart.pdf", stacks, printed=printed)
    bundle = load_bundle(_chart_bundle(tmp_path, pdf), pdf)
    return build_job(bundle, "#/pictures/0", work_dir=tmp_path / "work")


_THREE_BARS = [("A", [(0.3, _BLUE)]), ("B", [(0.55, _BLUE)]), ("C", [(0.8, _BLUE)])]


def _recorded_client(
    kind: str, requests: list[dict], overview: str = "overview"
) -> OllamaClient:
    """Replays the recorded reply *kind*; the overview call that precedes a
    measured read gets the recorded reply *overview*."""
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        body = json.loads(request.content)
        requests.append(body)
        asked = "has_data" in body["format"]["properties"]
        return httpx.Response(200, json=recorded[overview if asked else kind])

    return OllamaClient("http://ollama.test", transport=httpx.MockTransport(handler))


# --- schema --------------------------------------------------------------------


def test_chart_data_round_trips_and_exports_a_reference_free_json_schema() -> None:
    chart = ChartData(
        figure=Figure(
            bundle="AMIE-Mx", self_ref="#/pictures/5", page=6, bbox=[1, 2, 3, 4]
        ),
        source_kind="vector",
        panels=[
            Panel(
                id="a",
                bbox_px=[0, 0, 10, 10],
                kind="forest",
                orientation="horizontal",
                axes=Axes(x=Axis(name="OR", scale="log", range=[0.1, 10])),
                data=[
                    Value(
                        category="Age",
                        value=1.4,
                        err_lo=1.1,
                        err_hi=1.9,
                        source="printed",
                    )
                ],
            )
        ],
    )
    dumped = chart.dump()
    assert dumped["schema"] == SCHEMA_ID
    assert ChartData.model_validate(json.loads(json.dumps(dumped))) == chart

    schema = chart_data_json_schema()
    assert "$ref" not in json.dumps(schema) and "$defs" not in schema
    assert "schema" in schema["properties"]

    dumped_options = FigureDataOptions(mode="measured").model_dump(mode="json")
    assert dumped_options["eligible_types"] == sorted(dumped_options["eligible_types"])


# --- axis calibration ------------------------------------------------------------


def test_axis_fit_is_linear_log_or_categorical_and_rejects_non_monotone_ticks() -> None:
    linear = fit_axis([(812, "0.2"), (600, "0.4"), (388, "0.6"), (176, "0.8")], "y")
    assert linear is not None and linear.scale == "linear"
    assert linear.value_at(494) == pytest.approx(0.5)
    assert linear.pos_of(0.4) == pytest.approx(600)

    log = fit_axis([(100, "1"), (200, "10"), (300, "100"), (400, "1,000")], "x")
    assert log is not None and log.scale == "log"
    assert log.value_at(250) == pytest.approx(31.62, rel=1e-3)

    categorical = fit_axis([(50, "CoT"), (150, "SC-CoT"), (250, "HeartAgent")], "x")
    assert categorical is not None and categorical.scale == "categorical"
    assert categorical.category_at(160) == "SC-CoT"
    assert categorical.category_at(400) is None

    assert fit_axis([(100, "0.2"), (200, "0.6"), (300, "0.4")], "y") is None
    assert [
        parse_number(t) for t in ("\u22120.5", "65.2%", "64k", "1M", "2,5", "ns")
    ] == [
        -0.5,
        65.2,
        64000,
        1e6,
        2.5,
        None,
    ]


# --- panels ----------------------------------------------------------------------


def _frame(image: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    image[y0:y1, x0 : x0 + 2] = 0
    image[y1 - 2 : y1, x0:x1] = 0
    image[y0 + 40 : y1 - 2, x0 + 20 : x0 + 40] = (200, 60, 60)


def test_panel_split_names_a_lettered_grid_and_keeps_a_single_chart_whole() -> None:
    image = np.full((400, 400, 3), 255, dtype=np.uint8)
    corners = {"a": (20, 20), "b": (220, 20), "c": (20, 220), "d": (220, 220)}
    words = []
    for letter, (x, y) in corners.items():
        _frame(image, x + 15, y + 10, x + 170, y + 165)
        image[y : y + 8, x : x + 6] = 0
        words.append(Word(text=letter, bbox=(x, y, x + 6, y + 8), source="ocr"))

    result = split_panels(image, words)

    assert [p.id for p in result.panels] == ["a", "b", "c", "d"]
    assert result.method == "gutters"
    for panel, (x, y) in zip(result.panels, corners.values()):
        assert panel.bbox[0] == pytest.approx(x, abs=2)
        assert panel.bbox[1] == pytest.approx(y, abs=2)
        assert panel.bbox[2] < x + 180 and panel.bbox[3] < y + 180

    single = np.full((300, 400, 3), 255, dtype=np.uint8)
    _frame(single, 30, 20, 370, 280)
    alone = split_panels(single, [])
    assert [p.id for p in alone.panels] == ["1"]
    assert alone.panels[0].bbox == pytest.approx((30, 20, 370, 280), abs=1)


def _ticks(image: np.ndarray, x: int, labels: list[tuple[int, str]]) -> list[Word]:
    """Tick labels right-aligned at *x* (ink drawn where each label stands)."""
    words = []
    for y, text in labels:
        left = x - 6 * len(text)
        image[y - 4 : y + 4, left:x] = 0
        words.append(Word(text=text, bbox=(left, y - 5, x, y + 5), source="ocr"))
    return words


def test_charts_packed_without_a_gutter_are_split_by_their_tick_labels() -> None:
    """Three charts 5 px apart (no gutter of 1 % of the width): each has a
    run of tick labels, and the cut goes through the free band between a
    plot and the next chart's labels. One label misread by OCR ("80" for
    "0.8") does not cost the chart its axis; two tick labels alone count
    only when a model also sees that many charts."""
    image = np.full((200, 648, 3), 255, dtype=np.uint8)
    scale = [(30, "1.0"), (60, "0.8"), (90, "0.6"), (120, "0.4"), (150, "0.2")]
    words: list[Word] = []
    for index, left in enumerate((0, 212, 424)):
        labels = [(y, "80" if (index, t) == (1, "0.8") else t) for y, t in scale]
        words += _ticks(image, left + 28, labels[:2] if index == 2 else labels)
        _frame(image, left + 32, 20, left + 217, 170)

    assert split_panels(image, words, mode="gutters").method == "single"

    two = split_panels(image, words)
    assert two.method == "axes" and len(two.panels) == 2
    assert two.panels[0].bbox == pytest.approx((10, 20, 217, 170), abs=3)

    for word in words:
        word.text = word.text.replace("80", "0.8")
    three = split_panels(image, words, expect=3)
    assert [p.bbox[0] for p in three.panels] == pytest.approx([10, 222, 434], abs=3)
    assert [p.bbox[2] for p in three.panels] == pytest.approx([217, 429, 641], abs=3)
    assert len(split_panels(image, words, expect=5).panels) == 2


# --- vector reader ---------------------------------------------------------------


def test_vector_reader_measures_bars_and_stacks_from_pdf_paths(tmp_path: Path) -> None:
    job = _job(tmp_path, _THREE_BARS)
    assert job.source_kind == "vector"
    assert {w.text for w in job.words} >= {"0", "0.5", "1.0", "A", "B", "C"}
    full = (0.0, 0.0, *map(float, _image_size(job.image_path)))

    bars = read_vector_panel(job.marks, job.words, full, find_axes(job.words, full))

    assert bars is not None and bars.kind == "bar" and bars.orientation == "vertical"
    assert [(v.value.category, v.value.value) for v in bars.values] == [
        ("A", pytest.approx(0.3, abs=0.005)),
        ("B", pytest.approx(0.55, abs=0.005)),
        ("C", pytest.approx(0.8, abs=0.005)),
    ]

    stacked_job = _job(
        tmp_path / "stacked",
        [("A", [(0.2, _BLUE), (0.5, _ORANGE)]), ("B", [(0.6, _BLUE), (0.3, _ORANGE)])],
    )
    stacked = read_vector_panel(
        stacked_job.marks, stacked_job.words, full, find_axes(stacked_job.words, full)
    )
    assert stacked is not None and stacked.kind == "stacked_bar"
    assert sorted(
        (v.value.category, v.value.series, round(v.value.value or 0, 2))
        for v in stacked.values
    ) == [
        ("A", "#1f77b4", 0.2),
        ("A", "#ff7f0e", 0.5),
        ("B", "#1f77b4", 0.6),
        ("B", "#ff7f0e", 0.3),
    ]


def _image_size(path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as image:
        return image.size


def test_measured_mode_reads_a_vector_chart_from_its_paths(
    tmp_path: Path,
) -> None:
    """The model is asked once what the figure is and how many charts it
    holds; the values come from the PDF paths."""
    job = _job(tmp_path, _THREE_BARS, printed={"B": "0.55"})
    requests: list[dict] = []

    result = read_figure(
        job, FigureDataOptions(mode="measured"), _recorded_client("grounded", requests)
    )

    (panel,) = result.chart_data.panels
    assert panel.kind == "bar"
    assert [(v.category, v.source, v.confidence) for v in panel.data] == [
        ("A", "vector", 0.9),
        ("B", "printed", 0.95),
        ("C", "vector", 0.9),
    ]
    assert panel.data[1].value == 0.55
    (asked,) = requests
    assert "has_data" in asked["format"]["properties"]
    assert [c.prompt for c in result.calls] == ["overview"] and result.issues == []


def test_step_prepares_reads_and_embeds_a_finished_bundle(tmp_path: Path) -> None:
    """The whole step on a vector chart, with Ollama unreachable: the values
    come from the PDF paths. The figure folder holds what the reader was
    given and what it read, the run is recorded with its options, and the
    paper's markdown and run.json say that a model read the table."""
    pdf = _bar_chart_pdf(tmp_path / "chart.pdf", _THREE_BARS)
    bundle = _chart_bundle(tmp_path, pdf)
    doc = DoclingDocument.load_from_json(bundle / "document.json")
    (bundle / "chart.md").write_text(export_markdown(doc), encoding="utf-8")
    (bundle / "run.json").write_text("{}", encoding="utf-8")
    options = FigureDataOptions(method="ollama", ollama_url="http://127.0.0.1:9")

    run = run_step(bundle, pdf, options)

    step = bundle / "figure-to-data"
    assert sorted(p.name for p in (step / "pictures_0").iterdir()) == [
        "evidence.json",
        "figure-to-data.json",
        "figure-to-data.md",
        "figure.png",
        "figure.txt",
        "overlay.png",
        "result.json",
    ]
    assert _image_size(step / "pictures_0" / "figure.png")[0] > 450
    (outcome,) = run.figures
    assert (outcome.status, outcome.values) == ("read", 3)
    (record,) = (step / "runs").glob("*.json")
    assert json.loads(record.read_text())["options"]["method"] == "ollama"
    reading = (step / "pictures_0" / "figure-to-data.md").read_text(encoding="utf-8")
    assert "Machine-read from the figure" in reading
    assert "| B |  | #1f77b4 | 0.5503 |  |  |  | vector | 0.9 |" in reading

    doc = DoclingDocument.load_from_json(bundle / "document.json")
    assert get_chart_data(doc.pictures[0])["panels"][0]["kind"] == "bar"
    markdown = (bundle / "chart.md").read_text(encoding="utf-8")
    note = markdown.split(CHART_DATA_OPEN, 1)[1].split(ANNOTATION_CLOSE, 1)[0]
    assert "read from the image by a vision model (method ollama" in note
    assert "figure-to-data/pictures_0/figure-to-data.md" in note
    block = json.loads((bundle / "run.json").read_text())["figure_to_data"]
    assert (block["method"], block["figures"]) == ("ollama", {"read": 1})
    assert not needs_step(bundle, options)
    assert needs_step(bundle, FigureDataOptions(method="cloud"))


def test_ocr_lines_fill_in_where_the_text_layer_is_silent() -> None:
    """A bitmap chart with a watermark over it: the text layer holds the
    watermark only, OCR the tick labels. Both reach the reader; an OCR line
    over text-layer words is the same text twice and is dropped."""
    layer = [
        Word(text="PREPRINT", bbox=(100, 100, 180, 112), source="pdf"),
        Word(text="NOT", bbox=(190, 100, 215, 112), source="pdf"),
    ]
    read = [
        Word(text="PREPRINT NOT", bbox=(98, 98, 217, 114), source="ocr"),
        Word(text="0.5", bbox=(10, 40, 30, 50), source="ocr"),
        Word(text="1.0", bbox=(10, 10, 30, 20), source="ocr"),
    ]
    assert [w.text for w in merge_words(layer, read)] == [
        "PREPRINT",
        "NOT",
        "0.5",
        "1.0",
    ]


# --- VLM readers with recorded responses ------------------------------------------


def test_grounded_read_measures_pointed_bar_ends_and_prefers_printed_labels(
    tmp_path: Path,
) -> None:
    """The recorded read points 2-4 % off the bar tops of B and C, deep into
    bar A, and misreads A and C: the values come from the bar ends through
    the calibrated axis, B from its printed label."""
    job = _job(tmp_path, _THREE_BARS, printed={"B": "0.55"})
    job.source_kind = "raster"
    job.marks = []
    requests: list[dict] = []
    options = FigureDataOptions(mode="measured", panel_split="off", model="m")

    result = read_figure(job, options, _recorded_client("grounded", requests))

    asked, request = requests
    assert "has_data" in asked["format"]["properties"]
    assert request["model"] == "m" and request["options"]["temperature"] == 0
    assert "points" in request["format"]["properties"]
    assert set(request["format"]["properties"]["points"]["items"]["required"]) == {
        "category",
        "x",
        "series",
        "px",
        "py",
        "value",
    }
    assert len(request["messages"][0]["images"]) == 1
    assert "0.5 @" in request["messages"][0]["content"]
    (panel,) = result.chart_data.panels
    values = {v.category: v for v in panel.data}
    assert values["A"].source == "raster" and values["A"].confidence == 0.8
    assert values["A"].value == pytest.approx(0.3, abs=0.01)
    assert values["C"].value == pytest.approx(0.8, abs=0.01)
    assert (values["B"].value, values["B"].source) == (0.55, "printed")
    assert panel.axes is not None and panel.axes.y is not None
    assert panel.axes.y.range == [0.0, 1.0] and panel.axes.y.name == "Accuracy"
    overview, call = result.calls
    assert (overview.prompt, call.prompt, call.cut) == ("overview", "grounded", False)
    assert (call.prompt_tokens, call.eval_tokens, call.total_s) == (612, 180, 9.5)


def test_a_figure_without_data_is_not_read(tmp_path: Path) -> None:
    job = _job(tmp_path, _THREE_BARS)
    job.source_kind = "raster"
    job.marks = []
    requests: list[dict] = []
    client = _recorded_client("grounded", requests, overview="overview_diagram")

    result = read_figure(job, FigureDataOptions(mode="measured", model="m"), client)

    assert result.chart_data.panels == [] and len(requests) == 1
    assert result.chart_data.uncertain == [
        "not a data chart: A workflow diagram of a two-stage pipeline."
    ]


def test_several_charts_that_cannot_be_separated_are_not_read(tmp_path: Path) -> None:
    """The model sees two charts, the layout analysis one: reading both
    from one image is what merges panels, so the figure is left with a note."""
    job = _job(tmp_path, _THREE_BARS)
    job.source_kind = "raster"
    job.marks = []
    requests: list[dict] = []
    client = _recorded_client("grounded", requests, overview="overview_two_charts")

    result = read_figure(job, FigureDataOptions(mode="measured", model="m"), client)

    assert result.chart_data.panels == [] and len(requests) == 1
    (note,) = result.chart_data.uncertain
    assert note.startswith("not read: the model sees 2 charts")


def test_a_reply_cut_mid_list_keeps_its_complete_points() -> None:
    cut = (
        '{"title": null, "kind": "line", "points": [{"x": "1", "px": 10, "py": 20, '
        '"value": 0.5}, {"x": "2", "px": 30, "py": 40, "value": 0.6}, {"x": "3", "px'
    )
    kept = salvage_json(cut)
    assert kept is not None and [p["x"] for p in kept["points"]] == ["1", "2"]
    assert salvage_json("no json here") is None


def test_a_point_inside_a_bar_is_followed_to_the_bar_end() -> None:
    image = np.full((200, 100, 3), 255, dtype=np.uint8)
    image[60:180, 40:60] = (40, 90, 200)
    white = np.array([255, 255, 255])

    inside = refine_edge(
        image, 50, 150, "vertical", window=8, inward=1, background=white
    )
    assert inside == pytest.approx(59.5)
    assert refine_edge(image, 50, 150, "vertical", window=8, inward=1) is None
    near = refine_edge(image, 50, 56, "vertical", window=8, inward=1, background=white)
    assert near == pytest.approx(59.5)


def test_simple_read_turns_the_recorded_table_into_panels(tmp_path: Path) -> None:
    job = _job(tmp_path, _THREE_BARS, printed={"B": "0.55"})
    requests: list[dict] = []

    result = read_figure(
        job, FigureDataOptions(mode="simple"), _recorded_client("simple", requests)
    )

    assert "rows" in json.dumps(requests[0]["format"])
    (panel,) = result.chart_data.panels
    width, height = _image_size(job.crop_path)
    assert panel.bbox_px == pytest.approx([0, 0, width, height], abs=1)
    assert [(v.category, v.value, v.source) for v in panel.data] == [
        ("A", 0.3, "vlm"),
        ("B", 0.55, "printed"),
        ("C", 0.8, "vlm"),
    ]


# --- verifier and scorer ---------------------------------------------------------------


def _panel(kind: str, rows: list[Value], **extra) -> Panel:
    return Panel(id="a", bbox_px=[0, 0, 100, 100], kind=kind, data=rows, **extra)


def test_verifier_checks_stacks_intervals_ranges_survival_and_printed_labels() -> None:
    stacked = _panel(
        "stacked_bar",
        [
            Value(category="CoT", series="0", value=25, confidence=0.7),
            Value(category="CoT", series="1", value=35, confidence=0.7),
            Value(category="CoT", series="2", value=30, confidence=0.7),
        ],
        axes=Axes(y=Axis(range=[0, 100])),
    )
    assert any("do not sum to 100" in i for i in verify_panel(stacked))

    forest = _panel(
        "forest",
        [Value(category="Age", value=2.5, err_lo=1.1, err_hi=1.9, confidence=0.9)],
        axes=Axes(x=Axis(range=[0, 3])),
    )
    assert any("misses" in i for i in verify_panel(forest))
    assert forest.data[0].confidence == 0.65

    bars = _panel(
        "bar",
        [
            Value(category="A", value=1.4, confidence=0.7),
            Value(
                category="B",
                value=0.42,
                label_printed="0.61",
                source="raster",
                confidence=0.7,
            ),
        ],
        axes=Axes(y=Axis(range=[0, 1])),
    )
    assert any("outside the axis range" in i for i in verify_panel(bars))
    printed = apply_printed(bars, [Word(text="0.61", bbox=(0, 0, 1, 1), source="pdf")])
    assert printed and "printed 0.61 vs measured 0.42" in printed[0]
    assert (bars.data[1].value, bars.data[1].source, bars.data[1].confidence) == (
        0.61,
        "printed",
        0.7,
    )

    km = _panel(
        "kaplan_meier",
        [
            Value(x=float(t), series="arm", value=v, confidence=0.7)
            for t, v in ((0, 1.0), (6, 0.8), (12, 0.85))
        ],
    )
    assert any("survival rises" in i for i in verify_panel(km))

    junk = _panel(
        "line",
        [
            Value(category=c, value=0.5, source="raster", confidence=0.7)
            for c in (":[],", "x1", "CoT")
        ],
    )
    issues = check_labels(junk, [Word(text="CoT", bbox=(0, 0, 1, 1), source="ocr")])
    assert issues and "2 of 3 categories" in issues[0]
    assert [v.confidence for v in junk.data] == [0.45, 0.45, 0.7]


def test_printed_labels_are_paired_with_categories_by_position() -> None:
    """The model gave the second bar the first bar's label; the number on
    each category's row wins, and near-identical names stay apart."""
    rows = ["GPT4 Web - no image", "GPT4 API - no image"]
    axes = PanelAxes(
        y=AxisMap(
            axis="y", scale="categorical", ticks=[(100.0, rows[0]), (200.0, rows[1])]
        )
    )
    words = [
        Word(text="65.2%", bbox=(300, 95, 330, 105), source="ocr"),
        Word(text="68.8%", bbox=(310, 195, 340, 205), source="ocr"),
        Word(text="100", bbox=(500, 400, 520, 410), source="ocr"),
    ]
    panel = _panel(
        "bar",
        [
            Value(
                category=rows[0],
                series="Correct",
                value=0.0,
                label_printed="65.2%",
                source="raster",
                confidence=0.7,
            ),
            Value(
                category=rows[1],
                series="Correct",
                value=0.0,
                label_printed="65.2%",
                source="raster",
                confidence=0.7,
            ),
        ],
        orientation="horizontal",
    )

    assert pair_printed_labels(panel, words, axes) == 2
    apply_printed(panel, words)
    assert [(v.value, v.source) for v in panel.data] == [
        (65.2, "printed"),
        (68.8, "printed"),
    ]


def test_scorer_matches_panels_and_values_and_measures_axis_normalised_error() -> None:
    def chart(panels: list[Panel]) -> ChartData:
        return ChartData(
            figure=Figure(bundle="b", self_ref="#/pictures/1"), panels=panels
        )

    truth = chart(
        [
            Panel(
                id="a",
                bbox_px=[0, 0, 100, 100],
                kind="bar",
                axes=Axes(y=Axis(range=[0, 1])),
                series=[],
                data=[
                    Value(category="CoT", series="Llama", value=0.42),
                    Value(category="SC-CoT", series="Llama", value=0.46),
                    Value(
                        category="HeartAgent",
                        series="Llama",
                        value=0.60,
                        label_printed="0.60",
                    ),
                ],
            ),
            Panel(
                id="b",
                bbox_px=[110, 0, 200, 100],
                kind="pie",
                data=[Value(category="Yes", value=40.2)],
            ),
        ]
    )
    pred = chart(
        [
            Panel(
                id="1",
                bbox_px=[2, 1, 98, 99],
                kind="bar",
                data=[
                    Value(category="cot", series="llama", value=0.43, source="raster"),
                    Value(
                        category="SC CoT", series="Llama", value=0.50, source="raster"
                    ),
                    Value(
                        category="HeartAgnt",
                        series="Llama",
                        value=0.60,
                        source="printed",
                    ),
                    Value(category="Extra", series="Llama", value=0.1, source="vlm"),
                ],
            )
        ]
    )

    score = score_figure(truth, pred)

    assert (score.panels_matched, score.panel_recall, score.panel_precision) == (
        1,
        0.5,
        1.0,
    )
    assert score.kind_matches == 1
    assert (score.matched_values, score.missing_values, score.extra_values) == (3, 1, 1)
    assert (score.hits_02, score.hits_05) == (2, 3)
    assert score.mean_norm_error == pytest.approx((0.01 + 0.04 + 0.0) / 3, abs=1e-4)
    assert score.printed_mape == 0.0
    assert set(score.by_source) == {"raster", "printed"}


# --- publishing -------------------------------------------------------------------


def _published_bundle(tmp_path: Path, confidence: float) -> Path:
    pdf = _bar_chart_pdf(tmp_path / "chart.pdf", _THREE_BARS)
    bundle = _chart_bundle(tmp_path, pdf)
    doc = DoclingDocument.load_from_json(bundle / "document.json")
    markdown = export_markdown(doc).replace(
        "<!-- image -->", "![](images/picture_001.png)"
    )
    (bundle / "chart.md").write_text(markdown, encoding="utf-8")
    write_document_html(doc, bundle, figures_jsonl=bundle / "figures.jsonl")
    (bundle / "check.json").write_text("{}", encoding="utf-8")
    chart = ChartData(
        figure=Figure(
            bundle="chart", self_ref="#/pictures/0", image_path="images/picture_001.png"
        ),
        source_kind="vector",
        panels=[
            Panel(
                id="1",
                bbox_px=[0, 0, 450, 450],
                kind="bar",
                data=[
                    Value(
                        category=c,
                        series="Accuracy",
                        value=v,
                        source="vector",
                        confidence=confidence,
                    )
                    for c, v in (("A", 0.3), ("B", 0.55), ("C", 0.8))
                ],
            )
        ],
    )
    result = FigureDataResult(chart_data=chart, mode="measured", model="m")
    written = embed_results(
        bundle,
        [(result, "Read by a model.")],
        min_confidence=0.7,
        run_block={"method": "ollama"},
    )
    assert written == 1
    return bundle


def test_publish_puts_chart_data_in_every_export_of_the_bundle(tmp_path: Path) -> None:
    bundle = _published_bundle(tmp_path, confidence=0.9)

    row = json.loads((bundle / "figures.jsonl").read_text(encoding="utf-8"))
    assert row["chart_data"]["schema"] == SCHEMA_ID
    doc = DoclingDocument.load_from_json(bundle / "document.json")
    picture = RefItem(cref="#/pictures/0").resolve(doc)
    assert get_chart_data(picture) == row["chart_data"]
    assert picture.meta.tabular_chart is not None

    markdown = (bundle / "chart.md").read_text(encoding="utf-8")
    assert "![](images/picture_001.png)" in markdown
    table = markdown.split(CHART_DATA_OPEN, 1)[1].split(ANNOTATION_CLOSE, 1)[0]
    assert table.strip().startswith("Read by a model.")
    cells = [
        [c.strip() for c in line.strip("|").split("|")]
        for line in table.split("\n")
        if line.startswith("|")
    ]
    assert cells[0] == ["category", "Accuracy"] and ["B", "0.55"] in cells

    html = (bundle / "chart.html").read_text(encoding="utf-8")
    assert '"chart_data": {"schema": "extrct.figure-data/1"' in html
    assert "amir__chart_data" not in html.split("</script>", 1)[1]

    check = check_bundle(bundle)
    assert (check.figure_data.extracted, check.figure_data.verified) == (1, 1)
    assert check.export_fidelity.md == 1.0
    assert (
        json.loads((bundle / "check.json").read_text())["figure_data"]["extracted"] == 1
    )


def test_low_confidence_values_stay_out_of_the_markdown_and_leave_a_pointer(
    tmp_path: Path,
) -> None:
    bundle = _published_bundle(tmp_path, confidence=0.5)

    markdown = (bundle / "chart.md").read_text(encoding="utf-8")
    held_back = markdown.split(CHART_DATA_OPEN, 1)[1].split(ANNOTATION_CLOSE, 1)[0]
    assert "Read by a model." in held_back and "not shown here" in held_back
    assert "|" not in held_back
    check = check_bundle(bundle)
    assert (check.figure_data.extracted, check.figure_data.low_confidence) == (1, 1)
    row = FigureRow.model_validate_json(
        (bundle / "figures.jsonl").read_text(encoding="utf-8")
    )
    assert row.chart_data is not None


# --- the step's readers -------------------------------------------------------------


def _prepared(tmp_path: Path, *, printed=None) -> tuple[Path, PreparedFigure]:
    pdf = _bar_chart_pdf(tmp_path / "chart.pdf", _THREE_BARS, printed=printed)
    bundle = _chart_bundle(tmp_path, pdf)
    prepare_step(bundle, pdf, FigureDataOptions())
    figure_dir = bundle / "figure-to-data" / "pictures_0"
    return figure_dir, PreparedFigure.load(figure_dir)


def _points(*rows: tuple[str, float | None]) -> list[dict]:
    return [{"category": c, "x": None, "series": None, "value": v} for c, v in rows]


def test_prepared_context_names_caption_charts_and_printed_text(
    tmp_path: Path,
) -> None:
    figure_dir, prepared = _prepared(tmp_path, printed={"B": "0.55"})

    context = (figure_dir / "figure.txt").read_text(encoding="utf-8")
    assert "Caption in the paper:" in context
    assert "y ticks 0 | 0.5 | 1 (linear)" in context
    assert "0.55 @" in context and "A @" in context
    assert prepared.capture == "pdf-render" and prepared.source_kind == "vector"
    assert [p.image for p in prepared.panels] == [None]


def test_a_word_the_pdf_holds_half_of_does_not_cost_the_figure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A text layer with a lone surrogate (three figures of the sample
    papers have one) used to fail when the evidence was written, and the
    figure was skipped."""
    from docling.engines.figure_data import prepare

    real = prepare.build_job

    def with_broken_word(*args, **kwargs):
        job = real(*args, **kwargs)
        job.words.append(Word(text="n\udc9d=12", bbox=(1, 1, 9, 9), source="pdf"))
        return job

    monkeypatch.setattr(prepare, "build_job", with_broken_word)

    figure_dir, prepared = _prepared(tmp_path)

    assert prepared.words[-1].text == "n?=12"
    assert "n?=12 @" in (figure_dir / "figure.txt").read_text(encoding="utf-8")


def test_a_reading_takes_the_prepared_chart_and_goes_through_the_checks(
    tmp_path: Path,
) -> None:
    """One chart read by a cloud model: it gets the box and the axis of the
    chart the layout analysis found, a printed label the figure confirms
    becomes the value, and a value off the axis loses confidence."""
    _, prepared = _prepared(tmp_path, printed={"B": "0.55"})
    reading = FigureReading(
        description="Accuracy of three models",
        has_data=True,
        panels=[
            ReadPanel(
                id="a",
                title="Accuracy",
                kind="bar",
                points=[
                    ReadPoint(category="A", x=None, series=None, value=0.3),
                    ReadPoint(
                        category="B", x=None, series=None, value=0.5, label="0.55"
                    ),
                    ReadPoint(category="C", x=None, series=None, value=1.8),
                ],
                notes="read by eye",
            )
        ],
        not_read="the grid lines",
    )

    chart, issues = chart_from_reading(
        reading, prepared, reader="cloud", labeler="test", frontier=True
    )

    (panel,) = chart.panels
    assert panel.bbox_px == prepared.to_crop(prepared.panels[0].bbox)
    assert panel.axes.y.range == [0.0, 1.0] and panel.notes == ["read by eye"]
    rows = {v.category: (v.value, v.source, v.confidence) for v in panel.data}
    assert rows["A"] == (0.3, "vlm", 0.8)
    assert rows["B"] == (0.55, "printed", 0.95)
    assert rows["C"] == (1.8, "vlm", 0.55)
    assert any("outside the axis range" in issue for issue in issues)
    assert chart.uncertain == ["the grid lines"]
    assert chart.description == "Accuracy of three models"

    diagram = FigureReading(description="a workflow diagram", has_data=False)
    declined, _ = chart_from_reading(
        diagram, prepared, reader="agent", labeler="test", frontier=True
    )
    assert declined.panels == []
    assert declined.uncertain == ["not a data chart: a workflow diagram"]


def test_agent_tools_show_a_region_check_a_chart_and_close_the_reading(
    tmp_path: Path,
) -> None:
    figure_dir, prepared = _prepared(tmp_path)
    toolbox = FigureToolbox(figure_dir)
    chart_id = prepared.panels[0].id

    view = toolbox.call("look", {"chart": chart_id, "box": [0, 0, 500, 1000]})
    assert view.image_png is not None and "0.5 @" in view.text
    assert toolbox.call("look", {"chart": "z"}).is_error

    incomplete = toolbox.call("record_chart", {"id": chart_id, "kind": "bar"})
    assert incomplete.is_error and "points" in incomplete.text
    unnamed = toolbox.call(
        "record_chart",
        {"id": chart_id, "kind": "bar", "points": [{"value": 0.3}, {"value": 0.5}]},
    )
    assert not unnamed.is_error and "Naming problems" in unnamed.text
    assert "the tick label (or the bar, row or curve name)" in unnamed.text
    stacks = [
        {"category": c, "x": None, "series": f"{group} - {level}", "value": v}
        for c in ("A", "B")
        for group in ("drug", "placebo")
        for level, v in (("yes", 60.0), ("no", 40.0))
    ]
    two_bars = toolbox.call(
        "record_chart", {"id": "s", "kind": "stacked_bar", "points": stacks}
    )
    assert 'written "<tick label> - <group>"' in two_bars.text
    assert "do not sum to" not in two_bars.text
    unfinished = toolbox.call(
        "finish", {"description": "bars", "has_data": True, "not_read": []}
    )
    assert "still have the naming problems" in unfinished.text
    recorded = toolbox.call(
        "record_chart",
        {
            "id": chart_id,
            "title": None,
            "kind": "bar",
            "points": _points(("A", 0.3), ("B", 0.55), ("C", 8.0)),
            "notes": "one note, given as text",
        },
    )
    assert not recorded.is_error and "Value checks" in recorded.text
    assert "8 outside the axis range" in recorded.text
    corrected = toolbox.call(
        "record_chart",
        {
            "id": chart_id,
            "title": None,
            "kind": "bar",
            "points": _points(("A", 0.3), ("B", 0.55), ("C", 0.8)),
        },
    )
    assert corrected.text.startswith("Replaced") and "No check failed" in corrected.text

    no_data = {"description": "bars", "has_data": False, "not_read": []}
    assert toolbox.call("finish", no_data).is_error
    toolbox.call("finish", {"description": "bars", "has_data": True, "not_read": []})
    state = FigureToolbox.load_state(figure_dir)
    assert state is not None and state.finished
    assert [p.value for p in state.panels[-1].points] == [0.3, 0.55, 0.8]


def test_the_tool_server_answers_mcp_requests(tmp_path: Path) -> None:
    figure_dir, _ = _prepared(tmp_path)
    toolbox = FigureToolbox(figure_dir)

    listed = handle(toolbox, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    assert [t["name"] for t in listed["result"]["tools"]] == [
        "look",
        "record_chart",
        "finish",
    ]
    looked = handle(
        toolbox,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "look", "arguments": {}},
        },
    )
    assert looked is not None
    assert [c["type"] for c in looked["result"]["content"]] == ["text", "image"]
    started = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    assert handle(toolbox, started) is None
    unknown = handle(toolbox, {"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
    assert unknown is not None and unknown["error"]["code"] == -32601


def _stream(*events: dict) -> str:
    return "\n".join(json.dumps(event) for event in events)


def _session(structured: dict | None = None, *, tools: list[str], uses: int = 0) -> str:
    """The event stream of a finished ``claude -p`` session, as the CLI
    writes it (the fields the reader takes)."""
    return _stream(
        {
            "type": "system",
            "subtype": "init",
            "tools": tools,
            "mcp_servers": [],
            "model": "claude-sonnet-5-5",
        },
        *(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "tool_use", "name": tools[0], "input": {}}]
                },
            }
            for _ in range(uses)
        ),
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": uses + 1,
            "total_cost_usd": 0.04,
            "usage": {
                "input_tokens": 2,
                "cache_creation_input_tokens": 6000,
                "cache_read_input_tokens": 500,
                "output_tokens": 900,
            },
            "structured_output": structured,
            "result": "done",
        },
    )


def _fake_claude(stdout: str, calls: list[dict], act=None):
    def runner(args, **kwargs):
        calls.append({"args": args, **kwargs})
        if act is not None:
            act()
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    return runner


def _endpoint(handler, **kwargs) -> EndpointClient:
    return EndpointClient(
        "https://api.example.test/v1",
        "sk-test",
        transport=httpx.MockTransport(handler),
        sleep=lambda seconds: None,
        **kwargs,
    )


def _completion(content: str, **usage) -> httpx.Response:
    """A chat-completions reply as an OpenAI-compatible endpoint sends it."""
    return httpx.Response(
        200,
        json={
            "model": "anthropic/claude-sonnet-5.5",
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            "usage": usage,
        },
    )


def test_cloud_method_posts_figure_and_context_to_a_chat_completions_endpoint(
    tmp_path: Path,
) -> None:
    figure_dir, prepared = _prepared(tmp_path)
    reading = {
        "description": "Accuracy of three models",
        "has_data": True,
        "panels": [
            {
                "id": prepared.panels[0].id,
                "title": "Accuracy",
                "kind": "bar",
                "points": _points(("A", 0.3), ("B", 0.55), ("C", 0.8)),
            }
        ],
        "not_read": [],
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _completion(
            f"```json\n{json.dumps(reading)}\n```",
            prompt_tokens=6000,
            completion_tokens=900,
            cost=0.03,
        )

    reader = CloudReader(FigureDataOptions(method="cloud"), endpoint=_endpoint(handler))

    result = reader.read(prepared, figure_dir)

    (request,) = requests
    assert str(request.url) == "https://api.example.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer sk-test"
    body = json.loads(request.content)
    assert body["model"] == "anthropic/claude-sonnet-5.5"
    assert "temperature" not in body
    assert body["response_format"]["type"] == "json_schema"
    assert body["reasoning_effort"] == "high"
    # An enforced schema with optional fields lost the upper bound of
    # every interval on one provider: each field has to be written.
    sent = body["response_format"]["json_schema"]["schema"]
    point = sent["properties"]["panels"]["items"]["properties"]["points"]["items"]
    assert {"err_lo", "err_hi", "label"} <= set(point["required"])
    system, user = body["messages"]
    assert system["role"] == "system" and '"has_data"' in system["content"]
    assert [part["type"] for part in user["content"]] == ["image_url", "text"]
    assert user["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert "Caption in the paper:" in user["content"][-1]["text"]
    assert (result.method, result.backend) == ("cloud", "openai-compatible")
    assert (result.cost_usd, result.prompt_tokens, result.eval_tokens) == (
        0.03,
        6000,
        900,
    )
    assert [v.value for v in result.chart_data.panels[0].data] == [0.3, 0.55, 0.8]
    assert {v.confidence for v in result.chart_data.panels[0].data} == {0.8}
    assert "sk-test" not in (figure_dir / "trace.json").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="calls a model's API endpoint"):
        CloudReader(FigureDataOptions(method="cloud", backend="claude-cli"))


def test_the_endpoint_is_asked_again_after_a_busy_reply_and_without_a_field_it_rejects() -> (
    None
):
    replies = [
        httpx.Response(429, headers={"retry-after": "0"}),
        httpx.Response(400, json={"error": {"message": "reasoning is not supported"}}),
        httpx.Response(400, json={"error": {"message": "response_format unsupported"}}),
        _completion('{"ok": true}'),
        _completion('{"ok": true}'),
    ]
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return replies[len(bodies) - 1]

    endpoint = _endpoint(handler)
    question = {
        "model": "m",
        "system": "s",
        "content": [text_part("x")],
        "schema": {"type": "object"},
        "max_tokens": 10,
        "reasoning_effort": "high",
    }

    reply = endpoint.ask(**question)
    endpoint.ask(**question)

    assert reply.data == {"ok": True}
    # busy, reasoning refused, the schema field refused, answered; the
    # next figure is asked without the two refused fields at once.
    assert ["reasoning_effort" in body for body in bodies] == [
        True,
        True,
        False,
        False,
        False,
    ]
    assert ["response_format" in body for body in bodies] == [
        True,
        True,
        True,
        False,
        False,
    ]


def test_an_empty_reply_is_asked_for_once_more() -> None:
    question = {
        "model": "m",
        "system": "s",
        "content": [text_part("x")],
        "schema": {"type": "object"},
        "max_tokens": 10,
    }
    replies = [_completion(""), _completion('{"ok": true}')]
    asked: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return replies[len(asked) - 1]

    assert _endpoint(handler).ask(**question).data == {"ok": True}
    assert len(asked) == 2

    silent = _endpoint(lambda request: _completion(""))
    with pytest.raises(EndpointError, match=r"empty reply twice .*'stop'"):
        silent.ask(**question)


def test_the_api_key_comes_from_the_environment_or_the_nearest_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FIGURE_TEST_KEY", raising=False)
    (tmp_path / DOTENV_FILENAME).write_text(
        "# keys\nOTHER=1\nexport FIGURE_TEST_KEY='from-file'\n", encoding="utf-8"
    )
    nested = tmp_path / "out" / "paper"
    nested.mkdir(parents=True)

    assert api_key("FIGURE_TEST_KEY", nested) == "from-file"
    assert api_key("FIGURE_TEST_MISSING", nested) is None
    monkeypatch.setenv("FIGURE_TEST_KEY", "from-environment")
    assert api_key("FIGURE_TEST_KEY", nested) == "from-environment"


def test_a_figure_the_endpoint_does_not_answer_is_a_failed_figure(
    tmp_path: Path,
) -> None:
    figure_dir, _ = _prepared(tmp_path)

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "No auth credentials"}})

    options = FigureDataOptions(method="cloud")
    run, results = read_step(
        figure_dir.parent,
        options,
        reader=CloudReader(options, endpoint=_endpoint(refuse)),
    )

    (outcome,) = run.figures
    assert outcome.status == "failed"
    assert "refused the API key (401): No auth credentials" in (outcome.reason or "")
    assert results[0].chart_data.panels == []
    assert "No data read" in (figure_dir / "figure-to-data.md").read_text()
    assert run.reader["system_prompt"].startswith("You read the data out of one")
    assert "OPENROUTER_API_KEY" in run.reader["runtime"]
    assert "sk-test" not in run.model_dump_json()


def test_agent_method_gives_one_session_one_figure_and_its_three_tools(
    tmp_path: Path,
) -> None:
    figure_dir, prepared = _prepared(tmp_path)
    tools = [f"mcp__figure__{name}" for name in ("look", "record_chart", "finish")]

    def session() -> None:
        # What the model does through the tool server during the session.
        toolbox = FigureToolbox(figure_dir)
        toolbox.call(
            "record_chart",
            {
                "id": prepared.panels[0].id,
                "title": "Accuracy",
                "kind": "bar",
                "points": _points(("A", 0.3), ("B", 0.55), ("C", 0.8)),
            },
        )
        toolbox.call(
            "finish", {"description": "bars", "has_data": True, "not_read": []}
        )

    calls: list[dict] = []
    reader = AgentReader(
        FigureDataOptions(method="agent"),
        runner=_fake_claude(_session(tools=tools, uses=2), calls, session),
    )

    result = reader.read(prepared, figure_dir)

    args = calls[0]["args"]
    servers = json.loads(args[args.index("--mcp-config") + 1])["mcpServers"]
    assert list(servers) == ["figure"]
    assert servers["figure"]["args"][-1] == str(figure_dir.resolve())
    assert args[args.index("--allowedTools") + 1] == ",".join(tools)
    assert args[args.index("--tools") + 1] == ""
    isolation = {"--restricted", "--strict-mcp-config", "--disable-slash-commands"}
    assert isolation <= set(args)
    assert not Path(calls[0]["cwd"]).is_relative_to(tmp_path)
    content = json.loads(calls[0]["input"])["message"]["content"]
    assert [block["type"] for block in content] == ["image", "text"]
    assert args[args.index("--system-prompt") + 1] == POLICY and "ONE figure" in POLICY
    (panel,) = result.chart_data.panels
    assert [(v.value, v.source, v.confidence) for v in panel.data] == [
        (0.3, "agent", 0.8),
        (0.55, "agent", 0.8),
        (0.8, "agent", 0.8),
    ]
    assert result.calls[0].tool_calls == 2 and result.issues == []

    local = AgentReader(
        FigureDataOptions(method="agent", backend="ollama"),
        runner=_fake_claude(_session(tools=tools), calls, session),
    )
    on_ollama = local.read(prepared, figure_dir)
    last = calls[-1]
    assert last["env"]["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:11434"
    assert last["args"][last["args"].index("--model") + 1].startswith("gemma4")
    assert {v.confidence for v in on_ollama.chart_data.panels[0].data} == {0.5}
    assert on_ollama.cost_usd is None


def test_an_agent_session_that_is_stopped_keeps_what_it_recorded(
    tmp_path: Path,
) -> None:
    figure_dir, prepared = _prepared(tmp_path)

    def stopped(args, **kwargs):
        # The session recorded its chart, then ran into the time limit.
        FigureToolbox(figure_dir).call(
            "record_chart",
            {
                "id": prepared.panels[0].id,
                "kind": "bar",
                "points": _points(("A", 0.3), ("B", 0.55), ("C", 0.8)),
            },
        )
        raise subprocess.TimeoutExpired(args, kwargs["timeout"], output="")

    options = FigureDataOptions(method="agent")
    run, results = read_step(
        figure_dir.parent, options, reader=AgentReader(options, runner=stopped)
    )

    (outcome,) = run.figures
    assert (outcome.status, outcome.values) == ("read", 3)
    assert any("stopped after 600 s" in note for note in outcome.notes)
    assert any("ended before finish" in issue for issue in results[0].issues)
    assert run.reader["system_prompt"] == POLICY
    with pytest.raises(ValueError, match="agent method runs"):
        AgentReader(FigureDataOptions(method="agent", backend="openai-compatible"))


def test_a_cut_stream_keeps_what_the_session_did_until_then() -> None:
    run = parse_stream(
        _stream(
            {"type": "system", "subtype": "init", "tools": ["mcp__figure__look"]},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "mcp__figure__look",
                            "input": {"chart": "1"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": [
                                {"type": "text", "text": "View of chart 1"},
                                {"type": "image", "source": {"data": "A" * 4000}},
                            ],
                        }
                    ]
                },
            },
        )
        + '\n{"type": "assi'
    )

    assert [call.name for call in run.tool_calls] == ["mcp__figure__look"]
    assert run.structured is None and run.turns == 0
    kept = run.events[-1]["content"][0]["content"]
    assert kept == [
        {"type": "text", "text": "View of chart 1"},
        {"type": "image", "base64_chars": 4000},
    ]


def test_a_batch_runs_the_step_once_per_bundle_and_method(tmp_path: Path) -> None:
    """What `amir-batch --figure-data` does after a conversion: a bundle
    that had the step with this method is left alone, so a batch that was
    interrupted continues with the bundles still to read."""
    pdf = _bar_chart_pdf(tmp_path / "chart.pdf", _THREE_BARS)
    bundle = _chart_bundle(tmp_path, pdf)
    (bundle / "run.json").write_text("{}", encoding="utf-8")
    options = FigureDataOptions(method="ollama", ollama_url="http://127.0.0.1:9")
    step = _FigureStep(options, Console(quiet=True))

    step.run(bundle, pdf)
    step.run(bundle, pdf)
    step.run(tmp_path / "not-converted", pdf)
    step.close()

    (run,) = step.runs
    assert run.embedded == 1 and run.counts() == {"read": 1}
