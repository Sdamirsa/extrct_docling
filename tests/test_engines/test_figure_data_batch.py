# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The figure-to-data step inside ``amir-batch``, end to end: a real
conversion of a synthetic chart PDF, then the step with each method. No
model runs: the methods talk to stand-ins for the model hosts, a local
HTTP server (an OpenAI-compatible endpoint and Ollama's chat API) and a
``claude`` executable that drives the agent's real tool server."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from typer.testing import CliRunner

from docling.engines.cli import app
from docling.engines.serializers import CHART_DATA_OPEN

from .test_figure_data import _BLUE, RECORDED, _bar_chart_pdf, _points, _session

# The label printed over the tallest bar stands level with the top tick:
# the layout model then boxes the figure with its whole axis (under a
# shorter bar it leaves "1.0" out).
_BATCH_TRUTH = {"A": 0.3, "B": 0.55, "C": 0.95}
_BATCH_PRINTED = {"B": "0.55", "C": "0.95"}
# What the stand-ins for the cloud model and the agent answer: every bar,
# with the label printed over it where there is one.
_BATCH_READING = {
    "description": "Accuracy of three models",
    "has_data": True,
    "panels": [
        {
            "id": "1",
            "title": "Accuracy",
            "kind": "bar",
            "points": [
                {**point, "label": _BATCH_PRINTED.get(point["category"])}
                for point in _points(*_BATCH_TRUTH.items())
            ],
        }
    ],
    "not_read": [],
}
# What the cloud stand-in answers when the method first asks which charts
# the figure holds.
_BATCH_LIST = {
    "description": "Accuracy of three models",
    "has_data": True,
    "charts": [{"id": "1", "kind": "bar", "box": [20, 20, 980, 980]}],
}

# Stands in for `claude -p`: starts the one MCP server the session is given,
# records the chart through its tools, prints a finished session's stream.
_STAND_IN_CLAUDE = """
import json
import subprocess
import sys
from pathlib import Path

script = json.loads(Path(__file__).with_suffix(".json").read_text())
args = sys.argv[1:]
sys.stdin.read()
server = json.loads(args[args.index("--mcp-config") + 1])["mcpServers"]["figure"]
tools = subprocess.Popen(
    [server["command"], *server["args"]],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)
for number, (name, arguments) in enumerate(script["calls"], start=1):
    request = {
        "jsonrpc": "2.0",
        "id": number,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    tools.stdin.write(json.dumps(request) + "\\n")
    tools.stdin.flush()
    assert not json.loads(tools.stdout.readline())["result"]["isError"]
tools.stdin.close()
tools.wait()
print(script["stream"])
"""


class _ModelHosts:
    """Where the stand-ins are and what they were asked."""

    def __init__(self, url: str, path: str, requests: list[tuple[str, dict]]) -> None:
        self.url = url
        self.path = path
        self.requests = requests


@pytest.fixture
def model_hosts(tmp_path: Path) -> Iterator[_ModelHosts]:
    """An OpenAI-compatible chat-completions endpoint and Ollama's chat API
    on one local port, and a ``claude`` executable first on a PATH."""
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))
    requests: list[tuple[str, dict]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return None

        def _reply(self, payload: dict) -> None:
            body = (json.dumps(payload) + "\n").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            self._reply({"models": []})

        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            requests.append((self.path, body))
            if self.path == "/v1/chat/completions":
                schema = body["response_format"]["json_schema"]["schema"]
                listing = "charts" in schema["properties"]
                message = {
                    "content": json.dumps(_BATCH_LIST if listing else _BATCH_READING)
                }
                self._reply(
                    {
                        "model": body["model"],
                        "choices": [{"finish_reason": "stop", "message": message}],
                        "usage": {
                            "prompt_tokens": 6000,
                            "completion_tokens": 900,
                            "cost": 0.03,
                        },
                    }
                )
            else:
                asked = "has_data" in body["format"]["properties"]
                self._reply(recorded["overview" if asked else "grounded"])

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text(f"#!{sys.executable}\n{_STAND_IN_CLAUDE}", encoding="utf-8")
    claude.chmod(0o755)
    tools = [f"mcp__figure__{name}" for name in ("look", "record_chart", "finish")]
    finish = {"description": "bars", "has_data": True, "not_read": []}
    (bin_dir / "claude.json").write_text(
        json.dumps(
            {
                "calls": [
                    ["record_chart", _BATCH_READING["panels"][0]],
                    ["finish", finish],
                ],
                "stream": _session(tools=tools, uses=2),
            }
        ),
        encoding="utf-8",
    )
    try:
        yield _ModelHosts(
            f"http://127.0.0.1:{server.server_port}",
            f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            requests,
        )
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("setup", "method", "model", "source"),
    [
        (
            ["ollama", "--figure-data-ollama-url", "{url}"],
            "ollama",
            "gemma4:26b-a4b-it-qat",
            "vector",
        ),
        (
            ["cloud", "--figure-data-base-url", "{url}/v1"],
            "cloud",
            "anthropic/claude-sonnet-5.5",
            "vlm",
        ),
        (
            [
                "cloud",
                "--figure-data-base-url",
                "{url}/v1",
                "--figure-data-model",
                "google/gemini-3.8-flash",
            ],
            "cloud",
            "google/gemini-3.8-flash",
            "vlm",
        ),
        (["agent"], "agent", "claude-sonnet-5-5", "agent"),
    ],
    ids=["ollama", "cloud", "cloud-other-model", "agent"],
)
def test_amir_batch_converts_a_pdf_and_reads_its_chart_with_each_method(
    tmp_path: Path,
    model_hosts: _ModelHosts,
    setup: list[str],
    method: str,
    model: str,
    source: str,
) -> None:
    """One command, PDF in, bundle out: the conversion, then the step with
    the method asked for, and the reading in every export of the bundle,
    the page viewer and the batch summary included. A second run leaves the
    bundle and its reading alone."""
    inputs = tmp_path / "in"
    inputs.mkdir()
    _bar_chart_pdf(
        inputs / "chart.pdf",
        [(name, [(value, _BLUE)]) for name, value in _BATCH_TRUTH.items()],
        printed=_BATCH_PRINTED,
        # A page with no text outside its figure converts as PARTIAL_SUCCESS.
        sentence="Model C answers every question of the test set correctly.",
    )
    out = tmp_path / "out"
    command = [
        str(inputs),
        "-o",
        str(out),
        "--picture-description",
        "off",
        "--no-granite-vision-tables",
        "--no-figure-types",
        "--figure-data",
        *(part.format(url=model_hosts.url) for part in setup),
    ]
    env = {"COLUMNS": "400", "PATH": model_hosts.path}

    first = CliRunner().invoke(app, command, env=env)

    assert first.exit_code == 0, first.output
    bundle = out / "chart"
    block = json.loads((bundle / "run.json").read_text(encoding="utf-8"))[
        "figure_to_data"
    ]
    assert (block["method"], block["model"]) == (method, model)
    assert (block["figures"], block["embedded"]) == ({"read": 1}, 1)
    (row,) = [
        json.loads(line)
        for line in (bundle / "figures.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    (panel,) = row["chart_data"]["panels"]
    read = {v["category"]: v["value"] for v in panel["data"]}
    assert read == pytest.approx({c: _BATCH_TRUTH[c] for c in read}, abs=0.01)
    assert set(read) == set(_BATCH_TRUTH) and block["values"] == 3
    # Bar A carries no label; B and C are confirmed by the printed ones.
    assert [v["source"] for v in panel["data"]] == [source, "printed", "printed"]
    reading = "figure-to-data/pictures_0/figure-to-data.md"
    assert f"model `{model}`" in (bundle / reading).read_text(encoding="utf-8")
    note = f"read from the image by a vision model (method {method}, model {model}"
    markdown = (bundle / "chart.md").read_text(encoding="utf-8")
    assert CHART_DATA_OPEN in markdown and note in markdown and "0.55" in markdown
    assert note in (bundle / "chart.html").read_text(encoding="utf-8")
    chunks = (bundle / "chunks.jsonl").read_text(encoding="utf-8")
    assert "not the authors' numbers" in chunks
    for viewer in ("preview.html", "preview.embedded.html"):
        page = (bundle / viewer).read_text(encoding="utf-8")
        payload = json.loads(
            re.search(r'data-self-ref="#/pictures/0" data-payload="([^"]*)"', page)
            .group(1)
            .replace("&quot;", '"')
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&#x27;", "'")
            .replace("&amp;", "&")
        )
        shown = payload["figure_data"]
        assert (shown["charts"], shown["values"], shown["reading"]) == (1, 3, reading)
        assert note in shown["note"] and "<td>0.55" in shown["table_html"]
        assert '<span class="bbox-data-badge">data</span>' in page
    check = json.loads((bundle / "check.json").read_text(encoding="utf-8"))
    assert check["figure_data"]["eligible"] == check["figure_data"]["extracted"] == 1
    assert "charts 1/1/1" in first.output
    asked = {path for path, _ in model_hosts.requests}
    assert (
        asked
        == {
            "ollama": {"/api/chat"},
            "cloud": {"/v1/chat/completions"},
            "agent": set(),
        }[method]
    )
    if method == "cloud":
        assert {body["model"] for _, body in model_hosts.requests} == {model}

    runs = sorted((bundle / "figure-to-data" / "runs").glob("*.json"))
    second = CliRunner().invoke(app, command, env=env)

    assert second.exit_code == 0, second.output
    assert "SKIPPED" in second.output
    assert sorted((bundle / "figure-to-data" / "runs").glob("*.json")) == runs
