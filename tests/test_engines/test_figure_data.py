# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for figure-to-data (:mod:`docling.engines.figure_data`). No model
runs: the Ollama client replays recorded responses through an httpx mock
transport."""

from __future__ import annotations

import ctypes
import json
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

from docling.engines import check_bundle, export_markdown, write_document_html
from docling.engines.figure_data.evidence import (
    AxisMap,
    FigureRow,
    PanelAxes,
    build_job,
    find_axes,
    fit_axis,
    load_bundle,
    parse_number,
)
from docling.engines.figure_data.panels import split_panels
from docling.engines.figure_data.pipeline import read_document, read_figure
from docling.engines.figure_data.publish import (
    get_chart_data,
    publish_to_bundle,
)
from docling.engines.figure_data.readers.vector import read_vector_panel
from docling.engines.figure_data.readers.vlm import OllamaClient
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
from docling.engines.figure_data.verify import (
    apply_printed,
    check_labels,
    pair_printed_labels,
    verify_panel,
)
from docling.engines.picture_filter import PictureNoiseFlag
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
) -> Path:
    """A 300 pt page: y axis 0..1 from y=60 to y=260 (labels 0, 0.5, 1.0),
    one bar (or stack of segments) per category, 30 pt wide every 50 pt."""
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


def _recorded_client(kind: str, requests: list[dict]) -> OllamaClient:
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))[kind]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=recorded)

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


def test_measured_mode_reads_a_vector_chart_without_asking_the_model(
    tmp_path: Path,
) -> None:
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
    assert requests == [] and result.calls == [] and result.issues == []


def test_conversion_stage_reads_eligible_charts_and_attaches_them(
    tmp_path: Path,
) -> None:
    """The PdfEngine stage on a vector chart: no model needed (Ollama is
    unreachable), the record and overlay land in ``figure_data/``, the work
    image does not, and the picture gets its table."""
    pdf = _bar_chart_pdf(tmp_path / "chart.pdf", _THREE_BARS)
    bundle = _chart_bundle(tmp_path, pdf)
    doc = DoclingDocument.load_from_json(bundle / "document.json")
    flags = [PictureNoiseFlag("#/pictures/0", False, None, "bar_chart")]
    options = FigureDataOptions(mode="measured", ollama_url="http://127.0.0.1:9")

    results = read_document(
        doc,
        bundle,
        picture_images=[bundle / "images" / "picture_001.png"],
        noise_flags=flags,
        pdf_path=pdf,
        options=options,
    )

    (result,) = results
    assert result.chart_data.source_kind == "vector" and result.calls == []
    assert sorted(p.name for p in (bundle / "figure_data").iterdir()) == [
        "overlay_pictures_0.png",
        "pictures_0.json",
    ]
    picture = doc.pictures[0]
    assert get_chart_data(picture) == result.chart_data.dump()
    assert picture.meta is not None and picture.meta.tabular_chart is not None


# --- VLM readers with recorded responses ------------------------------------------


def test_grounded_read_measures_pointed_bar_ends_and_prefers_printed_labels(
    tmp_path: Path,
) -> None:
    """The recorded read points 2-4 % off the bar tops and misreads A and C:
    the values come from the snapped bar edges through the calibrated axis,
    B from its printed label."""
    job = _job(tmp_path, _THREE_BARS, printed={"B": "0.55"})
    job.source_kind = "raster"
    job.marks = []
    requests: list[dict] = []
    options = FigureDataOptions(mode="measured", panel_split="off", model="m")

    result = read_figure(job, options, _recorded_client("grounded", requests))

    (request,) = requests
    assert request["model"] == "m" and request["options"]["temperature"] == 0
    assert "points" in request["format"]["properties"]
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
    (call,) = result.calls
    assert (call.prompt_tokens, call.eval_tokens, call.total_s) == (612, 455, 9.5)


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
    assert publish_to_bundle(bundle, [result], min_confidence=0.7) == 1
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


def test_low_confidence_chart_data_stays_out_of_the_markdown(tmp_path: Path) -> None:
    bundle = _published_bundle(tmp_path, confidence=0.5)

    assert CHART_DATA_OPEN not in (bundle / "chart.md").read_text(encoding="utf-8")
    check = check_bundle(bundle)
    assert (check.figure_data.extracted, check.figure_data.low_confidence) == (1, 1)
    row = FigureRow.model_validate_json(
        (bundle / "figures.jsonl").read_text(encoding="utf-8")
    )
    assert row.chart_data is not None
