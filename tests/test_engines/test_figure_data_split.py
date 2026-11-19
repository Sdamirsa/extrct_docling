# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The chart list: a vision model says which charts a figure holds, and the
rule splitter draws their edges (``panels.cut_from_list``), in the local
engine and in the cloud method."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import numpy as np
import pytest

from docling.engines.figure_data.methods.cloud import CloudReader
from docling.engines.figure_data.panels import cut_from_list, split_panels
from docling.engines.figure_data.pipeline import read_figure
from docling.engines.figure_data.prepare import PreparedFigure
from docling.engines.figure_data.schema import FigureDataOptions, Word

from .test_figure_data import (
    _THREE_BARS,
    _completion,
    _endpoint,
    _frame,
    _job,
    _points,
    _prepared,
    _recorded_client,
    _ticks,
)


def test_a_models_chart_list_decides_the_count_and_the_rules_draw_the_edges() -> None:
    """The figure above, with the charts a vision model lists. Its boxes
    are rough (they clip every tick label): when the rules find as many
    charts their cut stands, and when they do not, the figure is cut
    between the listed boxes along the free bands and each cell trimmed to
    its ink, which takes the labels back in."""
    image = np.full((200, 648, 3), 255, dtype=np.uint8)
    scale = [(30, "1.0"), (60, "0.8"), (90, "0.6"), (120, "0.4"), (150, "0.2")]
    words: list[Word] = []
    for index, left in enumerate((0, 212, 424)):
        words += _ticks(image, left + 28, scale[:2] if index == 2 else scale)
        _frame(image, left + 32, 20, left + 217, 170)
    rules = split_panels(image, words)
    assert len(rules.panels) == 2

    listed = [
        ("a", (30.0, 25.0, 218.0, 165.0)),
        ("b", (236.0, 25.0, 430.0, 165.0)),
        ("c", (450.0, 25.0, 640.0, 165.0)),
    ]
    three = cut_from_list(image, words, listed, rules=rules)

    assert (three.method, three.rule_charts, three.listed_charts) == ("listed", 2, 3)
    assert [p.id for p in three.panels] == ["a", "b", "c"]
    assert [p.bbox[0] for p in three.panels] == pytest.approx([10, 222, 434], abs=3)
    assert [p.bbox[2] for p in three.panels] == pytest.approx([217, 429, 641], abs=3)
    assert three.notes == [
        "the rule splitter finds 2 chart(s), the model lists 3: cut between "
        "the listed charts"
    ]

    agreed = cut_from_list(
        image, words, [listed[0], ("b", (236.0, 25.0, 640.0, 165.0))]
    )
    assert agreed.method == "axes" and agreed.panels == rules.panels
    assert (agreed.rule_charts, agreed.listed_charts) == (2, 2)

    whole = cut_from_list(image, words, [("1", (30.0, 10.0, 600.0, 190.0))])
    assert (whole.method, whole.panels[0].bbox) == ("listed", (0.0, 0.0, 648.0, 200.0))

    nested = [listed[0], listed[1], ("c", (250.0, 40.0, 400.0, 150.0))]
    kept = cut_from_list(image, words, nested)
    assert kept.method == "listed-boxes"
    assert [p.bbox for p in kept.panels] == [box for _, box in nested]


def test_the_charts_the_model_lists_are_each_read_from_a_crop_of_their_own(
    tmp_path: Path,
) -> None:
    """The model lists two charts side by side where the layout analysis
    finds one: its count stands, the figure is cut between the two, and
    each is read on its own. With ``panel_split="rules"`` the layout
    analysis decides alone."""
    job = _job(tmp_path, _THREE_BARS)
    job.source_kind = "raster"
    job.marks = []
    requests: list[dict] = []
    client = _recorded_client("grounded", requests, overview="overview_two_charts")

    result = read_figure(job, FigureDataOptions(mode="measured", model="m"), client)

    assert result.panel_split == "listed" and len(requests) == 3
    assert [p.id for p in result.chart_data.panels] == ["a", "b"]
    assert (
        "the rule splitter finds 1 chart(s), the model lists 2: cut between "
        "the listed charts"
    ) in result.issues

    requests.clear()
    alone = FigureDataOptions(mode="measured", model="m", panel_split="rules")
    kept = read_figure(job, alone, client)
    assert len(kept.chart_data.panels) == 1 and len(requests) == 2


def test_cloud_method_cuts_the_figure_by_the_charts_the_model_lists(
    tmp_path: Path,
) -> None:
    """The model lists two charts where the rules find one: the prepared
    figure is cut again and the read gets a crop per chart. A list that
    cannot be read leaves the rules' cut, and ``panel_split="rules"`` asks
    for none."""
    figure_dir, prepared = _prepared(tmp_path)
    assert len(prepared.panels) == 1
    listing = {
        "description": "Two bar charts side by side.",
        "has_data": True,
        "charts": [
            {"id": "a", "kind": "bar", "box": [0, 0, 500, 1000]},
            {"id": "b", "kind": "bar", "box": [500, 0, 1000, 1000]},
        ],
    }
    reading = {"description": "bars", "has_data": False, "panels": [], "not_read": []}
    lists = [json.dumps(listing)]
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        asked = _asks_for_the_chart_list(requests[-1])
        return _completion(lists[0] if asked else json.dumps(reading))

    reader = CloudReader(FigureDataOptions(method="cloud"), endpoint=_endpoint(handler))

    result = reader.read(prepared, figure_dir)

    cut = PreparedFigure.load(figure_dir)
    assert (cut.split_method, cut.rule_charts, cut.listed_charts) == ("listed", 1, 2)
    assert [p.id for p in cut.panels] == ["a", "b"]
    crops = sorted(p.name for p in figure_dir.glob("panel-*.png"))
    assert crops == ["panel-a.png", "panel-b.png"]
    _, read = requests
    parts = read["messages"][1]["content"]
    assert [part["type"] for part in parts] == ["image_url", "text"] * 3
    assert (
        "Charts as a model listed them, cut by layout analysis: 2" in parts[-1]["text"]
    )
    assert result.panel_split == "listed"
    assert "the rule splitter finds 1 chart(s), the model lists 2" in result.issues[0]

    # The folder is reused by later runs, and each starts from the rules'
    # cut: a reply that is no list leaves that cut, on disk too.
    def on_disk() -> PreparedFigure:
        return PreparedFigure.load(figure_dir)

    requests.clear()
    lists[0] = "{}"
    kept = reader.read(on_disk(), figure_dir)
    assert len(requests) == 2 and kept.panel_split == prepared.split_method
    assert kept.issues[0] == (
        "the reply is not a chart list (3 errors): the rule splitter's cut is kept"
    )
    assert [call.prompt for call in kept.calls] == ["cloud list", "cloud read"]
    assert (on_disk().listed_by, on_disk().panels) == (None, prepared.panels)
    assert list(figure_dir.glob("panel-*.png")) == []
    sent = requests[1]["messages"][1]["content"]
    assert [part["type"] for part in sent] == ["image_url", "text"]

    lists[0] = json.dumps(listing)
    reader.read(on_disk(), figure_dir)
    assert on_disk().listed_by is not None
    requests.clear()
    alone = FigureDataOptions(method="cloud", panel_split="rules")
    ruled = CloudReader(alone, endpoint=_endpoint(handler)).read(on_disk(), figure_dir)
    assert len(requests) == 1 and not _asks_for_the_chart_list(requests[0])
    assert ruled.panel_split == prepared.split_method and on_disk().listed_by is None


def test_a_chart_list_that_cannot_be_cut_by_leaves_the_figure_readable(
    tmp_path: Path,
) -> None:
    """Lists a model can return: a chart without width, a chart inside
    another, the same chart a hundred times, and a list followed by a read
    that fails. The figure folder stays whole and every call is counted."""
    figure_dir, _ = _prepared(tmp_path)
    reading = {"description": "bars", "has_data": False, "panels": [], "not_read": []}
    replies = {"list": "", "read": json.dumps(reading)}

    def handler(request: httpx.Request) -> httpx.Response:
        asked = _asks_for_the_chart_list(json.loads(request.content))
        return _completion(replies["list" if asked else "read"], cost=0.01)

    def read(*boxes: tuple[int, int, int, int]):
        charts = [
            {"id": str(index + 1), "kind": "bar", "box": list(box)}
            for index, box in enumerate(boxes)
        ]
        replies["list"] = json.dumps(
            {"description": "bars", "has_data": True, "charts": charts}
        )
        reader = CloudReader(
            FigureDataOptions(method="cloud"), endpoint=_endpoint(handler)
        )
        result = reader.read(PreparedFigure.load(figure_dir), figure_dir)
        return result, PreparedFigure.load(figure_dir)

    result, cut = read((0, 0, 1000, 1000), (500, 0, 500, 1000))
    assert (cut.split_method, cut.listed_charts, len(cut.panels)) == ("listed", 2, 1)
    assert "lists 2 (1 without a usable box): read whole" in result.issues[0]

    result, cut = read((0, 0, 1000, 1000), (300, 300, 700, 700))
    assert cut.split_method == "listed-boxes"
    assert len(list(figure_dir.glob("panel-*.png"))) == 2

    result, cut = read(*[(0, 0, 1000, 1000)] * 100)
    assert (len(cut.panels), cut.listed_charts) == (1, 100)
    assert list(figure_dir.glob("panel-*.png")) == []
    assert any("too many, not taken" in issue for issue in result.issues)
    assert result.cost_usd == pytest.approx(0.02)

    replies["read"] = "{}"
    result, cut = read((0, 0, 500, 1000), (500, 0, 1000, 1000))
    assert any(issue.startswith("cloud read failed") for issue in result.issues)
    trace = json.loads((figure_dir / "trace.json").read_text(encoding="utf-8"))
    assert trace["reply"] == {} and trace["reply_text"] is None
    assert len(trace["chart_list"]["reply"]["charts"]) == 2
    assert len(cut.panels) == 2 and result.cost_usd == pytest.approx(0.02)


def test_several_charts_that_cannot_be_separated_are_not_read(tmp_path: Path) -> None:
    """The model lists two charts, one inside the other, and the layout
    analysis finds one: no straight cut separates them, and reading both
    from one image is what merges panels, so the figure is left with a note."""
    job = _job(tmp_path, _THREE_BARS)
    job.source_kind = "raster"
    job.marks = []
    requests: list[dict] = []
    client = _recorded_client("grounded", requests, overview="overview_nested_charts")

    result = read_figure(job, FigureDataOptions(mode="measured", model="m"), client)

    assert result.chart_data.panels == [] and len(requests) == 1
    (note,) = result.chart_data.uncertain
    assert note.startswith("not read: the model sees 2 charts")


def _asks_for_the_chart_list(body: dict) -> bool:
    schema = body["response_format"]["json_schema"]["schema"]
    return "charts" in schema["properties"]


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
    listing = {
        "description": "Accuracy of three models",
        "has_data": True,
        "charts": [{"id": "1", "kind": "bar", "box": [20, 20, 980, 980]}],
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if _asks_for_the_chart_list(json.loads(request.content)):
            return _completion(
                json.dumps(listing), prompt_tokens=2000, completion_tokens=60, cost=0.01
            )
        return _completion(
            f"```json\n{json.dumps(reading)}\n```",
            prompt_tokens=6000,
            completion_tokens=900,
            cost=0.03,
        )

    reader = CloudReader(FigureDataOptions(method="cloud"), endpoint=_endpoint(handler))

    result = reader.read(prepared, figure_dir)

    # The model is first asked which charts the figure holds, with little
    # thinking; the rules found the one chart it lists, so their cut stands.
    asked, request = requests
    first = json.loads(asked.content)
    assert first["reasoning_effort"] == "low"
    assert "list its charts" in first["messages"][1]["content"][-1]["text"]
    listed = PreparedFigure.load(figure_dir)
    assert (listed.listed_by, listed.rule_charts, listed.listed_charts) == (
        "anthropic/claude-sonnet-5.5",
        1,
        1,
    )
    assert listed.panels == prepared.panels
    assert [call.prompt for call in result.calls] == ["cloud list", "cloud read"]
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
        pytest.approx(0.04),
        8000,
        960,
    )
    assert [v.value for v in result.chart_data.panels[0].data] == [0.3, 0.55, 0.8]
    assert {v.confidence for v in result.chart_data.panels[0].data} == {0.8}
    trace = (figure_dir / "trace.json").read_text(encoding="utf-8")
    assert "sk-test" not in trace
    assert json.loads(trace)["chart_list"]["reply"] == listing
    with pytest.raises(ValueError, match="calls a model's API endpoint"):
        CloudReader(FigureDataOptions(method="cloud", backend="claude-cli"))


def test_a_reply_that_wraps_its_json_is_read_and_one_without_json_is_counted(
    tmp_path: Path,
) -> None:
    """Seen once the read got a crop per chart: a sentence before a fenced
    JSON object, and tool calls the model does not have. The object is
    found inside the reply; a reply that holds none fails the figure, with
    its cost counted and its text kept."""
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
    junk = (
        '<invoke name="bash">\n<parameter name="cmd">echo skip</parameter>\n</invoke>'
    )
    replies = [
        f"I transcribed the bars; they are approximate.\n\n```json\n{json.dumps(reading)}\n```",
        f"{junk}\n\n{json.dumps(reading)}\n\n{junk}",
        f"Only the bars are tabulated.\n\n{junk}",
    ]
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _completion(
            replies[0], prompt_tokens=100, completion_tokens=10, cost=0.05
        )

    options = FigureDataOptions(method="cloud", panel_split="rules")
    reader = CloudReader(options, endpoint=_endpoint(handler))

    for _ in range(2):
        result = reader.read(prepared, figure_dir)
        assert [v.value for v in result.chart_data.panels[0].data] == [0.3, 0.55, 0.8]
        replies.pop(0)
    assert "You have no tools" in requests[0]["messages"][0]["content"]

    failed = reader.read(prepared, figure_dir)
    assert failed.chart_data.panels == [] and failed.cost_usd == 0.05
    assert failed.issues[0].startswith("cloud read failed: no JSON object in the reply")
    trace = json.loads((figure_dir / "trace.json").read_text(encoding="utf-8"))
    assert trace["reply"] is None and trace["reply_text"] == replies[0]
