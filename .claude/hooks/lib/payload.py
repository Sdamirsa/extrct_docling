"""Parse hook stdin payloads + emit structured hook responses.

Hook contract (per Anthropic docs):
  - stdin: JSON with hook_event_name, tool_name/tool_input/tool_output, session_id, cwd, ...
  - exit 0: success; JSON stdout (if any) parsed for hook-specific decisions
  - exit 2: blocking error; stderr fed to Claude as feedback
"""

from __future__ import annotations

import json
import sys
from typing import Any


def read_payload() -> dict[str, Any]:
    """Read and JSON-parse stdin. Returns {} on empty/invalid input."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def emit_session_start_context(text: str) -> None:
    """Print SessionStart `additionalContext` JSON to stdout."""
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }))


def deny(reason: str) -> None:
    """Block the tool call: write reason to stderr and exit 2."""
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def allow() -> None:
    """Default; explicit no-op to make hook intent readable."""
    sys.exit(0)
