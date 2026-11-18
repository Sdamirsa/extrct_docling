# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A chat-completions endpoint for the ``cloud`` method.

Any service that speaks the OpenAI chat-completions format: OpenRouter (the
default base URL), a provider's own endpoint, a gateway, or a local
Ollama's ``/v1``. One ``POST <base url>/chat/completions`` per figure, with
the images as data URLs, the reply asked for as JSON to a schema.

The API key is never passed on a command line or written into a run
record. It is read from the environment variable the options name
(``OPENROUTER_API_KEY`` by default), else from the same name in the
nearest ``.env`` file at or above the working directory. An endpoint on
this machine needs none.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image
from pydantic import BaseModel

from docling.engines.figure_data.readers.vlm import salvage_json

DOTENV_FILENAME = ".env"
_RETRIED = {408, 409, 429, 500, 502, 503, 504, 529}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class EndpointError(RuntimeError):
    """The endpoint is unreachable, refused the request, or returned no JSON."""


class EndpointReply(BaseModel):
    data: dict[str, Any]
    seconds: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    cut: bool = False
    model: str | None = None
    # The endpoint's own usage block, as sent.
    usage: dict[str, Any] = {}
    # The optional request fields the endpoint accepted for this reply.
    asked_with: list[str] = []


def api_key(name: str, start: Path | None = None) -> str | None:
    """The key *name*: from the environment, else from the nearest ``.env``
    at or above *start* (default: the working directory)."""
    value = os.environ.get(name)
    if value:
        return value
    folder = (start or Path.cwd()).resolve()
    for candidate in (folder, *folder.parents):
        path = candidate / DOTENV_FILENAME
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, raw = line.strip().removeprefix("export ").partition("=")
            if sep and key.strip() == name:
                return raw.strip().strip("'\"") or None
        return None
    return None


def required_everywhere(schema: dict[str, Any]) -> dict[str, Any]:
    """*schema* with every property of every object required.

    Providers differ in what an enforced schema does to an optional
    field: Gemini 3.8 Flash through OpenRouter (2026-11) wrote ``err_lo``
    and left ``err_hi`` out of every point, three times of three, and
    wrote both when the schema stood only in the prompt. A nullable
    field that has to be written is written."""
    if isinstance(schema, dict):
        out = {key: required_everywhere(value) for key, value in schema.items()}
        if isinstance(out.get("properties"), dict):
            out["required"] = list(out["properties"])
        return out
    if isinstance(schema, list):
        return [required_everywhere(item) for item in schema]  # type: ignore[return-value]
    return schema


def is_local(base_url: str) -> bool:
    return (urlparse(base_url).hostname or "") in _LOCAL_HOSTS


def image_part(image: Image.Image, max_side: int) -> dict[str, Any]:
    """*image* as a message part (a PNG data URL), scaled down to *max_side*."""
    if max(image.size) > max_side:
        ratio = max_side / max(image.size)
        image = image.resize(
            (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{encoded}"},
    }


def text_part(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


class EndpointClient:
    def __init__(
        self,
        base_url: str,
        key: str | None,
        *,
        timeout_s: float = 600,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        self._http = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout_s,
            headers=headers,
            transport=transport,
        )
        self._retries = retries
        self._sleep = sleep
        # Optional request fields this endpoint has refused.
        self._refused: set[str] = set()

    def close(self) -> None:
        self._http.close()

    def ask(
        self,
        *,
        model: str,
        system: str,
        content: list[dict[str, Any]],
        schema: dict[str, Any],
        max_tokens: int,
        reasoning_effort: str | None = None,
    ) -> EndpointReply:
        """One request, answered as a JSON object of *schema*. The schema
        also stands in the system message, for a model or a provider that
        does not enforce ``response_format``. An endpoint that rejects
        ``response_format`` or ``reasoning_effort`` is asked again without
        the field and not sent it again. An empty reply is asked for once
        more. No sampling parameter is sent: current models refuse a
        non-default temperature."""
        schema = required_everywhere(schema)
        optional: dict[str, Any] = {
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "figure_reading", "schema": schema},
            },
            "reasoning_effort": reasoning_effort,
        }
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": f"{system}\n\nReply with one JSON object of this "
                    f"JSON schema and nothing else:\n{json.dumps(schema)}",
                },
                {"role": "user", "content": content},
            ],
            **{
                name: value
                for name, value in optional.items()
                if value is not None and name not in self._refused
            },
        }
        started = time.perf_counter()
        payload, choice, text = self._answer(body, optional)
        if not text.strip():
            # HTTP 200 with nothing in it: seen once in some 55 calls (Gemini
            # 3.8 Flash through OpenRouter, after 130 s).
            payload, choice, text = self._answer(body, optional)
        if not text.strip():
            raise EndpointError(
                "the endpoint returned an empty reply twice (finish_reason "
                f"{choice.get('finish_reason')!r})"
            )
        cut = choice.get("finish_reason") == "length"
        data = _json_object(text, cut)
        usage = payload.get("usage") or {}
        return EndpointReply(
            data=data,
            seconds=round(time.perf_counter() - started, 2),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cost_usd=usage.get("cost"),
            cut=cut,
            model=payload.get("model"),
            usage=usage,
            asked_with=[name for name in optional if name in body],
        )

    def _answer(
        self, body: dict[str, Any], optional: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """The reply to *body*: payload, first choice and its text. An
        optional field the endpoint rejects is taken out of *body* and
        remembered once a request without it is answered."""
        response = self._post(body)
        dropped: list[str] = []
        while response.status_code in (400, 422):
            sent = [name for name in optional if name in body]
            if not sent:
                break
            # The error usually names the field it rejects.
            field = (
                "reasoning_effort"
                if "reasoning_effort" in sent and "reasoning" in response.text
                else sent[0]
            )
            del body[field]
            dropped.append(field)
            response = self._post(body)
        if response.status_code != 200:
            raise EndpointError(_refusal(response))
        self._refused.update(dropped)
        try:
            payload = response.json()
            choice = payload["choices"][0]
            text = _text(choice["message"].get("content"))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise EndpointError(
                f"unexpected reply from the endpoint: {response.text[:200]!r}"
            ) from exc
        return payload, choice, text

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        """The response, after waiting out rate limits and server errors."""
        attempt = 0
        while True:
            try:
                response = self._http.post("chat/completions", json=body)
            except httpx.HTTPError as exc:
                if attempt >= self._retries:
                    raise EndpointError(f"endpoint unreachable: {exc}") from exc
                response = None
            if response is not None and (
                response.status_code not in _RETRIED or attempt >= self._retries
            ):
                return response
            wait = 2.0**attempt
            if response is not None:
                after = response.headers.get("retry-after", "")
                wait = float(after) if after.replace(".", "", 1).isdigit() else wait
            self._sleep(min(wait, 60.0))
            attempt += 1


def _text(content: object) -> str:
    """The reply text; some endpoints return it in parts."""
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        )
    return str(content or "")


def _json_object(text: str, cut: bool) -> dict[str, Any]:
    stripped = _FENCE.sub("", text.strip())
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        # A reply that ran into the token limit: keep its complete items.
        kept = salvage_json(stripped) if cut else None
        if kept is None:
            raise EndpointError(f"no JSON object in the reply: {text[:200]!r}") from exc
        return kept
    if not isinstance(value, dict):
        raise EndpointError(f"the reply is not a JSON object: {text[:200]!r}")
    return value


def _refusal(response: httpx.Response) -> str:
    detail = response.text[:300]
    try:
        error = response.json().get("error")
        if isinstance(error, dict):
            detail = str(error.get("message") or detail)
    except ValueError:
        pass
    if response.status_code in (401, 403):
        return f"the endpoint refused the API key ({response.status_code}): {detail}"
    return f"endpoint {response.status_code}: {detail}"
