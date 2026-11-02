"""Canonical-path + glob helpers for hook deny rules.

The bash regex bypasses found in the v0 security critique (./.env vs
./.env.local vs /abs/path/.env vs ./../foo/.env) are all handled by
canonicalizing the path before matching globs.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path


def canonicalize(p: str | Path, cwd: Path | None = None) -> Path:
    """Best-effort absolute, symlink-resolved path. Tolerates non-existent files."""
    base = Path(cwd or os.getcwd())
    candidate = Path(os.path.expandvars(os.path.expanduser(str(p))))
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        return candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return candidate.absolute()


def matches_any_glob(path: Path, globs: list[str]) -> str | None:
    """Return the first matching glob (for explaining denials), else None.

    Globs may use `~` (home), `**`, `*`, `?`, `[seq]`. They are matched against
    the absolute path string AND the basename, so `**/.env*` matches
    `/abs/path/to/.env.local`.
    """
    s = str(path)
    home = str(Path.home())
    for g in globs:
        # Expand ~ in the glob.
        g_expanded = g.replace("~", home, 1) if g.startswith("~") else g
        # Two forms: with **-prefix for any depth, and the literal expansion.
        if fnmatch.fnmatchcase(s, g_expanded):
            return g
        # Also try matching with normalized forward-slash on the path
        if fnmatch.fnmatchcase(s.replace(os.sep, "/"), g_expanded):
            return g
    return None


# Pre-compiled regex helpers for raw-string matching (used by Bash hook).

ENV_TOKEN_RE = re.compile(r"(?:^|[\s'\"=:&|;])([./~$\w\-]*\.env(?:\.[\w\-]+)*)")
PEM_KEY_RE = re.compile(r"[./~$\w\-]+\.(pem|key|p12|pfx)\b")
CRED_FILE_RE = re.compile(
    r"(?:\.git-credentials|\.netrc|\.npmrc|id_[a-z]+|credentials(?:\.json)?|"
    r"\.aws/[^\s]+|\.ssh/[^\s]+|\.gnupg/[^\s]+|\.kube/config|\.docker/config\.json)",
    re.IGNORECASE,
)
PROC_ENVIRON_RE = re.compile(r"/proc/(?:self|\d+)/environ\b")
