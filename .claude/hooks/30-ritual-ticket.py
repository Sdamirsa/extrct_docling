#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""UserPromptSubmit / UserPromptExpansion hook: mint the /project-memory ritual ticket.

The ritual is the user's to open. When the user's OWN prompt starts with
``/project-memory`` (or Claude Code expands that command), this writes
``.claude/.cache/ritual-ticket.json`` = {skill, ts, session_id, event}. The
ritual's CHECK (``.claude/skills/project-memory/check.py``) refuses to run
without a fresh ticket and ``check.py --complete`` consumes it, so a ritual an
agent opens on its own fails loudly. A prompt that merely mentions the command
mid-sentence, or a turn Claude Code starts by itself, writes nothing.

A tripwire, not cryptography: it does not make forging impossible.

Never blocks or alters the prompt: every path exits 0 and prints nothing
(stdout on these events is injected into the context). If it breaks, no
ticket is written and CHECK refuses the ritual: fail closed there, not here.

Adapted from dot-claude-iff's ``ritual-ticket.sh``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from payload import read_payload  # noqa: E402

SKILLS = ("project-memory",)
EVENTS = {"userpromptsubmit": "UserPromptSubmit", "userpromptexpansion": "UserPromptExpansion"}
# The command first (after leading whitespace), then the end or whitespace and an argument.
PROMPT_RE = re.compile(r"\A\s*/(project-memory)(?=\s|\Z)")
# What the user typed: `user_input` in current releases, `prompt` in older ones.
# Never `expanded_prompt`: that is the command's template, not the user's words.
PROMPT_KEYS = ("user_input", "prompt", "userInput", "user_prompt", "userPrompt")
COMMAND_KEYS = ("command_name", "commandName", "command", "slash_command", "slashCommand",
                "skill_name", "skillName", "skill")
NESTED_KEYS = ("expansion", "command", "slash_command", "skill")


def _command_skill(value: object) -> str | None:
    """'project-memory' or '/project-memory args' -> the skill; anything else -> None."""
    if not isinstance(value, str):
        return None
    words = value.strip().split()
    name = words[0].removeprefix("/") if words else ""
    return name if name in SKILLS else None


def skill_of(payload: dict) -> tuple[str | None, str | None]:
    """(skill, event) for a payload that opens the ritual, else (None, event)."""
    raw_event = payload.get("hook_event_name") or payload.get("hookEventName") or ""
    event = EVENTS.get(str(raw_event).strip().lower())
    if raw_event and event is None:
        return None, None  # wired to another event by mistake: never mint there
    origin = payload.get("user_input_type", payload.get("userInputType"))
    if origin is not None and str(origin).strip().lower() != "user":
        return None, event  # a turn Claude Code started on its own
    for key in PROMPT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and (match := PROMPT_RE.match(value)):
            return match.group(1), event
    if event == "UserPromptSubmit":
        return None, event  # a submitted prompt is judged by its text alone
    sources = [payload] + [payload[k] for k in NESTED_KEYS if isinstance(payload.get(k), dict)]
    for source in sources:
        for key in COMMAND_KEYS:
            if skill := _command_skill(source.get(key)):
                return skill, event
    return None, event


def main() -> None:
    payload = read_payload()
    skill, event = skill_of(payload)
    if not skill:
        return
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    target = project / ".claude" / ".cache" / "ritual-ticket.json"
    session = payload.get("session_id")
    ticket = {
        "skill": skill,
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": str(session) if session else None,
        "event": event or "unknown",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(ticket), encoding="utf-8")
    tmp.replace(target)  # atomic: CHECK never reads a half-written ticket


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never block the user's prompt
        pass
    sys.exit(0)
