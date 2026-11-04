"""CHECK phase of /project-memory: one PASS / WARN / FAIL line per step.

    uv run --no-sync python .claude/skills/project-memory/check.py [--gates]
    uv run --no-sync python .claude/skills/project-memory/check.py --complete
    uv run --no-sync python .claude/skills/project-memory/check.py --grant   (USER only)

Read-only, except ``--gates`` (the engine tests and ``make validate``, whose
pre-commit hooks may rewrite files) and ``--complete`` (consumes the ritual
ticket at the end of the ritual). ``--grant`` is the user's fallback when the
prompt hook didn't fire (hooks not yet accepted): it writes a ticket marked
``human-terminal``. settings.json denies it to Claude's Bash tool; agents never
run it. Exit 1 if any step FAILs.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLAUDE_DIR = ROOT / ".claude"
TICKET = CLAUDE_DIR / ".cache" / "ritual-ticket.json"
TICKET_HOOK = "30-ritual-ticket.py"
TICKET_TTL_S = 6 * 3600
LOG_TYPES = {
    "decision",
    "deliverable",
    "milestone",
    "analysis",
    "note",
    "mistake",
    "tooling",
}
TAG_RE = re.compile(r"^extrct_docling-v(\d+)\.(\d+)\.(\d+)-r(\d+)$")
failed = False


def report(level: str, step: str, message: str) -> None:
    global failed
    failed |= level == "FAIL"
    print(f"{level:<5} {step:<16} {message}")


def run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)


def git(*args: str) -> str:
    return run("git", *args).stdout.strip()


def check_ticket() -> None:
    """The ritual is the user's: with the ticket hook installed, CHECK needs the
    ticket it mints when the user's own prompt starts with /project-memory."""
    hook = CLAUDE_DIR / "hooks" / TICKET_HOOK
    settings = (CLAUDE_DIR / "settings.json").read_text(encoding="utf-8")
    if not hook.exists() or TICKET_HOOK not in settings:
        report(
            "WARN",
            "ticket",
            "ticket hook not installed: only disable-model-invocation keeps the ritual user-only",
        )
        return
    if not TICKET.exists():
        report(
            "FAIL",
            "ticket",
            "no ritual ticket: the USER must type /project-memory (never mint one yourself)",
        )
        return
    ticket = json.loads(TICKET.read_text(encoding="utf-8"))
    age_min = (time.time() - float(ticket.get("ts", 0))) / 60
    if age_min * 60 > TICKET_TTL_S:
        report(
            "FAIL",
            "ticket",
            f"ticket is {age_min:.0f} min old (> {TICKET_TTL_S // 60}): the user types /project-memory again",
        )
    else:
        report(
            "PASS",
            "ticket",
            f"minted {age_min:.0f} min ago by {ticket.get('event')} (session {ticket.get('session_id')})",
        )


def grant() -> None:
    """The user's own fallback ticket, typed in their terminal."""
    TICKET.parent.mkdir(parents=True, exist_ok=True)
    ticket = {
        "skill": "project-memory",
        "ts": time.time(),
        "session_id": None,
        "event": "human-terminal",
    }
    TICKET.write_text(json.dumps(ticket), encoding="utf-8")
    print("ticket granted from the terminal: type /project-memory")


def complete() -> None:
    """Close the ritual: consume the ticket so it can't open another run."""
    if TICKET.exists():
        TICKET.unlink()
        print("ritual complete: ticket consumed")
    else:
        print(
            "ritual complete (no ticket to consume: hook not installed or already consumed)"
        )


def check_git() -> None:
    branch = git("branch", "--show-current")
    changed = git("status", "--porcelain")
    counts = run("git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    level = "PASS"
    notes = [f"branch {branch}"]
    if branch in {"main", "master"}:
        level = "WARN"
        notes.append("on a protected branch")
    if changed:
        level = "WARN"
        notes.append(
            f"{len(changed.splitlines())} changed/untracked paths (PUBLISH commits what belongs)"
        )
    if counts.returncode == 0:
        ahead, behind = counts.stdout.split()
        notes.append(f"ahead {ahead} / behind {behind} of upstream")
        if behind != "0":
            level = "WARN"
    else:
        level = "WARN"
        notes.append("no upstream branch")
    report(level, "git", "; ".join(notes))


def check_release() -> None:
    tags = [
        t for t in git("tag", "-l", "extrct_docling-v*").splitlines() if TAG_RE.match(t)
    ]
    match = re.search(
        r'^ENGINE_VERSION = "(.+)"',
        (ROOT / "docling/engines/run_snapshot.py").read_text(),
        re.M,
    )
    if not tags or match is None:
        report("WARN", "release", "no extrct_docling-v* tag or no ENGINE_VERSION")
        return
    latest = max(tags, key=lambda t: tuple(int(x) for x in TAG_RE.match(t).groups()))  # type: ignore[union-attr]
    problems = []
    if latest != f"extrct_docling-v{match.group(1)}":
        problems.append(f"ENGINE_VERSION {match.group(1)} vs latest tag {latest}")
    readme = (ROOT / "README.md").read_text()
    first_row = re.search(r"^\| \[`(extrct_docling-v[^`]+)`\]", readme, re.M)
    if first_row is None or first_row.group(1) != latest:
        problems.append(f"README Releases top row is not {latest}")
    if (
        f"Current release: **`{latest}`**"
        not in (CLAUDE_DIR / "HANDOFF.md").read_text()
    ):
        problems.append(f"HANDOFF current release is not {latest}")
    unreleased = git("log", "--oneline", f"{latest}..HEAD", "--", "docling", "tests")
    if unreleased:
        problems.append(
            f"{len(unreleased.splitlines())} commit(s) changing docling/ or tests/ since {latest} (release-tag when ready)"
        )
    report(
        "WARN" if problems else "PASS",
        "release",
        "; ".join(problems) or f"{latest} matches ENGINE_VERSION, README, HANDOFF",
    )


def check_handoff() -> None:
    handoff = (CLAUDE_DIR / "HANDOFF.md").read_text()
    problems = []
    collected = run(
        "uv",
        "run",
        "--no-sync",
        "pytest",
        "tests/test_engines",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
    )
    total = re.search(r"(\d+) tests? collected", collected.stdout)
    stated = re.findall(r"(\d+) pass, (\d+) skip", handoff)
    if total and stated:
        for passed, skipped in set(stated):
            if int(passed) + int(skipped) != int(total.group(1)):
                problems.append(
                    f"says {passed} pass + {skipped} skip, {total.group(1)} tests are collected"
                )
    modules = sorted(
        p.name
        for p in (ROOT / "docling/engines").glob("*.py")
        if p.name != "__init__.py"
    )
    missing = [m for m in modules if m not in handoff]
    if missing:
        problems.append(f"module tree lacks {', '.join(missing)}")
    report(
        "WARN" if problems else "PASS",
        "handoff",
        "; ".join(problems) or "test counts and module tree current",
    )


def read_jsonl(path: Path, step: str, required: set[str]) -> list[dict] | None:
    if not path.exists():
        report("FAIL", step, f"{path.relative_to(ROOT)} missing")
        return None
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            report("FAIL", step, f"line {n} is not JSON: {exc}")
            return None
        if missing := required - row.keys():
            report("FAIL", step, f"line {n} lacks {sorted(missing)}")
            return None
        rows.append(row)
    return rows


def check_memory_files() -> None:
    log = read_jsonl(
        CLAUDE_DIR / "Project-log.jsonl",
        "project-log",
        {"date", "type", "title", "summary", "source"},
    )
    if log is not None:
        bad = [r["type"] for r in log if r["type"] not in LOG_TYPES]
        last_commit = git("log", "-1", "--format=%cs")
        last_entry = max((r["date"] for r in log), default="")
        if bad:
            report("FAIL", "project-log", f"unknown type(s): {sorted(set(bad))}")
        elif last_entry < last_commit:
            report(
                "WARN",
                "project-log",
                f"{len(log)} entries, last {last_entry or 'none'}; commits up to {last_commit} not logged yet",
            )
        else:
            report("PASS", "project-log", f"{len(log)} entries, last {last_entry}")
    lessons = read_jsonl(
        CLAUDE_DIR / "LESSONS.jsonl",
        "lessons",
        {"id", "what", "root_cause", "prevention", "active"},
    )
    if lessons is not None:
        latest = {r["id"]: r for r in lessons}  # a later row supersedes an earlier id
        active = [i for i, r in latest.items() if r["active"]]
        level = "PASS" if 1 <= len(active) <= 3 or not latest else "WARN"
        report(
            level,
            "lessons",
            f"{len(latest)} lessons, {len(active)} active (keep 1-3): {', '.join(active)}",
        )
    status = CLAUDE_DIR / "STATUS.md"
    if not status.exists():
        report("FAIL", "status", ".claude/STATUS.md missing")
    else:
        text = status.read_text(encoding="utf-8")
        lines = len([line for line in text.splitlines() if line.strip()])
        sections = [
            "Current focus",
            "Active work",
            "Next steps",
            "Blockers",
            "Watch-outs",
        ]
        absent = [s for s in sections if s not in text]
        stub = "first `/project-memory` run" in text
        level = "WARN" if absent or stub or not 12 <= lines <= 40 else "PASS"
        detail = f"; missing sections {absent}" if absent else ""
        detail += "; still the pre-ritual stub" if stub else ""
        report(level, "status", f"{lines} lines{detail}")


def check_auto_memory() -> None:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
    memory = Path.home() / ".claude" / "projects" / slug / "memory"
    index = memory / "MEMORY.md"
    if not index.exists():
        report("WARN", "auto-memory", "no MEMORY.md for this project")
        return
    links = re.findall(r"\]\(([^)]+\.md)\)", index.read_text(encoding="utf-8"))
    missing = [link for link in links if not (memory / link).exists()]
    unindexed = sorted(
        p.name
        for p in memory.glob("*.md")
        if p.name != "MEMORY.md" and p.name not in links
    )
    if missing:
        report("FAIL", "auto-memory", f"MEMORY.md points at missing files: {missing}")
    else:
        extra = f"; not in the index: {unindexed}" if unindexed else ""
        report(
            "WARN" if unindexed else "PASS",
            "auto-memory",
            f"{len(links)} memories indexed{extra}",
        )


def check_torch() -> None:
    out = run(
        "uv",
        "run",
        "--no-sync",
        "python",
        "-c",
        "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())",
    )
    if out.returncode != 0:
        report("WARN", "torch", "could not import torch")
        return
    version, cuda, available = out.stdout.split()
    level = "PASS" if cuda != "None" and available == "True" else "WARN"
    report(
        level,
        "torch",
        f"{version}, CUDA {cuda}, available {available} (a re-sync can swap in a CPU build)",
    )


def check_gates() -> None:
    tests = run(
        "uv",
        "run",
        "--no-sync",
        "pytest",
        "tests/test_engines",
        "-q",
        "-p",
        "no:cacheprovider",
    )
    summary = (tests.stdout.strip().splitlines() or ["no output"])[-1]
    report("PASS" if tests.returncode == 0 else "FAIL", "tests", summary)
    before = git("status", "--porcelain")
    validate = run("make", "validate")
    after = git("status", "--porcelain")
    if validate.returncode != 0:
        failing = [line for line in validate.stdout.splitlines() if "Failed" in line]
        report("FAIL", "make validate", "; ".join(failing) or "non-zero exit")
    elif before != after:
        report(
            "WARN",
            "make validate",
            "hooks modified files: review the diff, rerun until clean",
        )
    else:
        report("PASS", "make validate", "clean")


if __name__ == "__main__":
    if "--complete" in sys.argv[1:]:
        complete()
        sys.exit(0)
    if "--grant" in sys.argv[1:]:
        grant()
        sys.exit(0)
    check_ticket()
    check_git()
    check_release()
    check_handoff()
    check_memory_files()
    check_auto_memory()
    check_torch()
    if "--gates" in sys.argv[1:]:
        check_gates()
    sys.exit(1 if failed else 0)
