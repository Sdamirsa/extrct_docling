"""Parse Bash command strings robustly for hook deny rules.

Closes regex bypasses called out in the security critique:
  - quote elision (`cat .e''nv` → `cat .env`)
  - env-var indirection (`F=.env; cat $F`)
  - short/long flag aliases (`-f` vs `--force`)
  - command chaining (`;`, `&&`, `||`, `|`, `$()`)
  - find -exec / find -delete masquerading as a non-`rm` destructive op
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


# Treat these as separators when splitting a compound command into clauses.
COMPOUND_SEPS = re.compile(r"(?:;|\|\||&&|\||\$\(|`|>\(|<\()")


@dataclass(frozen=True)
class Clause:
    raw: str
    argv: tuple[str, ...]
    leading_assigns: tuple[str, ...]  # FOO=bar pieces before the actual command


def split_compound(cmd: str) -> list[str]:
    """Split a compound shell command into individual clauses.

    Conservative: any of `;`, `&&`, `||`, `|`, `$()`, `` ` ` `` start a new clause.
    """
    parts = COMPOUND_SEPS.split(cmd)
    return [p.strip() for p in parts if p.strip()]


def parse_clause(cmd: str) -> Clause:
    """Parse a single clause into argv. Tolerates malformed input."""
    raw = cmd.strip()
    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError:
        # Unbalanced quotes — fall back to whitespace split.
        tokens = raw.split()

    assigns: list[str] = []
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        assigns.append(tokens.pop(0))

    return Clause(raw=raw, argv=tuple(tokens), leading_assigns=tuple(assigns))


def all_clauses(cmd: str) -> list[Clause]:
    return [parse_clause(c) for c in split_compound(cmd)]


def has_flag(argv: tuple[str, ...], *flags: str) -> bool:
    """True if any flag form is present.

    Examples: has_flag(argv, "-f", "--force") matches `-f`, `--force`, `-fR`, `-rf`, etc.
    Short single-char flags (e.g. `-f`) are also matched when bundled with other shorts.
    """
    short_singles = [f.lstrip("-") for f in flags if re.fullmatch(r"-[A-Za-z]", f)]
    long_flags = [f for f in flags if f.startswith("--")]
    short_pairs = [f for f in flags if re.fullmatch(r"-[A-Za-z][A-Za-z]+", f)]

    for tok in argv[1:]:
        if tok in flags:
            return True
        if tok in long_flags:
            return True
        if tok in short_pairs:
            return True
        if tok.startswith("--"):
            # Long flag — check exact equality, then strip-value forms (--force=...)
            head = tok.split("=", 1)[0]
            if head in long_flags:
                return True
            continue
        if tok.startswith("-") and len(tok) > 1 and not tok.startswith("--"):
            # Possibly a bundle of short flags like `-rf`.
            chars = set(tok[1:])
            if any(c in chars for c in short_singles):
                return True
    return False


def expanded_argv(clause: Clause) -> tuple[str, ...]:
    """Substitute leading `FOO=bar` assignments into `$FOO` references.

    Cheap heuristic: handles `F=.env; cat $F` after split_compound joins.
    Only substitutes the assignments visible in *this* clause's leading_assigns
    plus those that appeared in earlier clauses of the same compound command —
    but split_compound has already separated them, so we only see the current
    clause's assigns here.
    """
    if not clause.leading_assigns:
        return clause.argv

    env: dict[str, str] = {}
    for a in clause.leading_assigns:
        k, _, v = a.partition("=")
        env[k] = v

    out: list[str] = []
    for tok in clause.argv:
        new = tok
        for k, v in env.items():
            new = new.replace(f"${k}", v).replace(f"${{{k}}}", v)
        out.append(new)
    return tuple(out)


def collect_argv_with_inherited_env(cmd: str) -> list[tuple[Clause, tuple[str, ...]]]:
    """Walk all clauses; for each, return (clause, argv-with-assignments-expanded).

    Carries assignments forward across clauses in a compound command (FOO=bar; cat $FOO).
    """
    env: dict[str, str] = {}
    out: list[tuple[Clause, tuple[str, ...]]] = []
    for clause in all_clauses(cmd):
        for a in clause.leading_assigns:
            k, _, v = a.partition("=")
            env[k] = v
        argv: list[str] = []
        for tok in clause.argv:
            new = tok
            for k, v in env.items():
                new = new.replace(f"${k}", v).replace(f"${{{k}}}", v)
            argv.append(new)
        out.append((clause, tuple(argv)))
    return out
