# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Run one Claude Code session without a terminal (``claude -p``) and read
its event stream. This is the agent method's runtime; the cloud method
calls a model's API (:mod:`.endpoint`).

The session gets nothing of the machine it runs on: no built-in tools
(``--tools ""``), none of the user's or the project's settings, skills,
commands or memory files (``--restricted``, ``--disable-slash-commands``),
no MCP server but the one the caller passes (``--strict-mcp-config``), our
system prompt in place of Claude Code's, and an empty working directory.
What it can do is exactly what the caller passes: the content of one user
message (text and images) and, for an agent, the tools of one MCP server.
That is what makes a run repeatable on another machine, and what keeps a
reader from seeing anything but its figure. (``--safe-mode`` would do the
same for a single call but also switches off the MCP server an agent
needs; measured on Claude Code 2.1.326, the two put the same number of
tokens in front of the model.)

The CLI authenticates as it is set up: its own login, or
``ANTHROPIC_API_KEY``. Pointed at Ollama's Anthropic-compatible endpoint
(``ollama_url``), the same session runs on a local model.
"""

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field

_TEXT_KEPT = 2000


class ClaudeCliError(RuntimeError):
    """The CLI is missing, failed, or returned no usable result."""


class ToolCall(BaseModel):
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class CliRun(BaseModel):
    """One finished (or stopped) session."""

    structured: dict[str, Any] | None = None
    text: str = ""
    seconds: float = 0.0
    turns: int = 0
    cost_usd: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tools_offered: list[str] = Field(default_factory=list)
    model: str | None = None
    error: str | None = None
    # The stream with image data taken out: what was said and done, in order.
    events: list[dict[str, Any]] = Field(default_factory=list)


Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def image_block(image: Image.Image, max_side: int) -> dict[str, Any]:
    """*image* as a content block, scaled down to *max_side* when larger."""
    if max(image.size) > max_side:
        ratio = max_side / max(image.size)
        image = image.resize(
            (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
        },
    }


def text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def run_claude(
    *,
    command: str,
    model: str,
    system_prompt: str,
    content: list[dict[str, Any]],
    timeout_s: float,
    json_schema: dict[str, Any] | None = None,
    mcp_servers: dict[str, Any] | None = None,
    allowed_tools: Sequence[str] = (),
    effort: str | None = None,
    max_cost_usd: float | None = None,
    ollama_url: str | None = None,
    runner: Runner = subprocess.run,
) -> CliRun:
    """One session: *content* as the only user message, *system_prompt* as
    the whole system prompt. A session that runs past *timeout_s* is
    stopped and returned with what its stream held until then."""
    args = [
        command,
        "-p",
        "--model",
        model,
        "--tools",
        "",
        "--system-prompt",
        system_prompt,
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--strict-mcp-config",
        "--restricted",
        "--disable-slash-commands",
        "--permission-prompts",
        "none",
    ]
    if json_schema is not None:
        args += ["--json-schema", json.dumps(json_schema)]
    if mcp_servers:
        args += ["--mcp-config", json.dumps({"mcpServers": mcp_servers})]
    if allowed_tools:
        args += ["--allowedTools", ",".join(allowed_tools)]
    if effort is not None:
        args += ["--effort", effort]
    if max_cost_usd is not None:
        args += ["--max-budget-usd", f"{max_cost_usd:g}"]
    env = dict(os.environ)
    if ollama_url is not None:
        env.update(
            ANTHROPIC_BASE_URL=ollama_url,
            ANTHROPIC_AUTH_TOKEN="ollama",
            ANTHROPIC_API_KEY="",
        )
    message = {"type": "user", "message": {"role": "user", "content": content}}
    started = time.perf_counter()
    error: str | None = None
    with tempfile.TemporaryDirectory(prefix="figure_reader_") as cwd:
        try:
            done = runner(
                args,
                input=json.dumps(message) + "\n",
                capture_output=True,
                text=True,
                cwd=cwd,
                env=env,
                timeout=timeout_s,
                check=False,
            )
            stdout, stderr, code = done.stdout or "", done.stderr or "", done.returncode
        except FileNotFoundError as exc:
            raise ClaudeCliError(
                f"{command!r} is not installed or not on PATH: the agent "
                "method runs through the Claude Code CLI"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code = _text(exc.stdout), _text(exc.stderr), 0
            error = f"stopped after {timeout_s:g} s"
    run = parse_stream(stdout)
    run.seconds = round(time.perf_counter() - started, 2)
    if error is not None:
        run.error = error
    elif code != 0 and run.error is None:
        run.error = f"claude exited with {code}: {(stderr or stdout).strip()[-400:]}"
    return run


def parse_stream(stdout: str) -> CliRun:
    """The session a ``--output-format stream-json`` stream describes."""
    run = CliRun()
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            run.tools_offered = list(event.get("tools") or [])
            run.model = event.get("model")
            run.events.append(
                {
                    "type": "init",
                    "model": run.model,
                    "tools": run.tools_offered,
                    "mcp_servers": event.get("mcp_servers"),
                }
            )
        elif kind in ("assistant", "user"):
            blocks = event.get("message", {}).get("content")
            if isinstance(blocks, str):
                blocks = [{"type": "text", "text": blocks}]
            kept = [_kept(block) for block in blocks or []]
            run.events.append({"type": kind, "content": kept})
            for block in blocks or []:
                if kind == "assistant" and block.get("type") == "tool_use":
                    run.tool_calls.append(
                        ToolCall(
                            name=block.get("name", ""), input=block.get("input") or {}
                        )
                    )
        elif kind == "result":
            usage = event.get("usage") or {}
            run.structured = event.get("structured_output")
            run.text = str(event.get("result") or "")
            run.turns = int(event.get("num_turns") or 0)
            run.cost_usd = event.get("total_cost_usd")
            run.input_tokens = sum(
                int(usage.get(key) or 0)
                for key in (
                    "input_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                )
            )
            run.output_tokens = int(usage.get("output_tokens") or 0)
            if event.get("is_error"):
                run.error = (
                    f"{event.get('subtype') or 'error'}: "
                    f"{str(event.get('result') or event.get('api_error_status'))[:400]}"
                )
            run.events.append(
                {
                    "type": "result",
                    "subtype": event.get("subtype"),
                    "stop_reason": event.get("stop_reason"),
                    "turns": run.turns,
                    "cost_usd": run.cost_usd,
                    "usage": usage,
                    "permission_denials": event.get("permission_denials"),
                }
            )
    return run


def _kept(block: dict[str, Any]) -> dict[str, Any]:
    """A content block for the trace: image data replaced by its size, long
    text cut."""
    kind = block.get("type")
    if kind == "image":
        data = (block.get("source") or {}).get("data") or block.get("data") or ""
        return {"type": "image", "base64_chars": len(data)}
    if kind == "text":
        return {"type": "text", "text": str(block.get("text", ""))[:_TEXT_KEPT]}
    if kind == "thinking":
        return {"type": "thinking", "chars": len(str(block.get("thinking", "")))}
    if kind == "tool_use":
        return {
            "type": "tool_use",
            "name": block.get("name"),
            "input": block.get("input"),
        }
    if kind == "tool_result":
        inner = block.get("content")
        if isinstance(inner, list):
            inner = [_kept(item) for item in inner if isinstance(item, dict)]
        elif isinstance(inner, str):
            inner = inner[:_TEXT_KEPT]
        return {
            "type": "tool_result",
            "is_error": bool(block.get("is_error")),
            "content": inner,
        }
    return {"type": str(kind)}


def _text(raw: object) -> str:
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw if isinstance(raw, str) else ""
