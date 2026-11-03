#!/usr/bin/env bash
# check_sensitive.sh [BASE_REF] [EXTRA_FILE ...]
#
# Scans what a push would publish: the commits in BASE_REF..HEAD (default:
# the upstream of the current branch) plus any EXTRA_FILE (e.g. the tag
# notes). Prints FAIL lines for things that must not be pushed and REVIEW
# lines for things a person should look at. Exit 1 if anything FAILs.
set -uo pipefail

default_base='@{upstream}'
base="${1:-$default_base}"
shift || true
extra_files=("$@")
self_dir=".claude/skills/release-tag"
fails=0

fail() { echo "FAIL   $*"; fails=$((fails + 1)); }
review() { echo "REVIEW $*"; }

if ! git rev-parse --verify --quiet "$base" >/dev/null; then
  echo "unknown base ref: $base" >&2
  exit 2
fi
range="$base..HEAD"
echo "Scanning $range ($(git rev-list --count "$range") commits)${extra_files[*]:+ + ${extra_files[*]}}"

# 1. Files that must never be published.
never='(^|/)\.env($|\.)|(^|/)\.mcp\.json$|settings\.local\.json$|^\.claude/private-hand-off/|^\.claude/worktrees/|^samples/(?!README\.md$)|\.log$|\.(pem|key|p12|pfx)$|(^|/)id_(rsa|ed25519)|credentials'
while IFS= read -r path; do
  [ -z "$path" ] && continue
  [[ "$path" == ".env.example" || "$path" == */.env.example ]] && continue
  fail "file must not be pushed: $path"
done < <(git diff --name-only --diff-filter=AM "$range" | grep -P "$never" || true)

# 2. Added lines (outside this skill, whose docs name the patterns).
added="$(git diff "$range" -- . ":(exclude)$self_dir" | grep -E '^\+[^+]' || true)"
for f in "${extra_files[@]}"; do
  added+=$'\n'"$(sed 's/^/+/' "$f")"
done

secret_patterns=(
  'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}'
  'hf_[A-Za-z0-9]{30,}'
  'sk-(ant-)?[A-Za-z0-9_-]{20,}'
  'AKIA[0-9A-Z]{16}'
  'xox[abprs]-[A-Za-z0-9-]{10,}'
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  '(api|secret|access|auth)[_-]?(key|token)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"']{12,}'
)
for pat in "${secret_patterns[@]}"; do
  hits="$(grep -oE -- "$pat" <<<"$added" | sort -u | head -3)"
  [ -n "$hits" ] && fail "secret-like string: $(echo "$hits" | cut -c1-12 | tr '\n' ' ')..."
done

user="$(whoami)"
host="$(hostname -s 2>/dev/null || hostname)"
machine_patterns=(
  "/home/[A-Za-z0-9._-]+"
  "/Users/[A-Za-z0-9._-]+"
  'C:\\\\Users\\\\'
  "/tmp/claude"
  "\\b${user}\\b"
  "\\b${host}\\b"
  '\b(10\.[0-9]{1,3}|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}\b'
)
for pat in "${machine_patterns[@]}"; do
  hits="$(grep -oE -- "$pat" <<<"$added" | sort -u | head -3)"
  [ -n "$hits" ] && fail "machine-specific detail ($pat): $(echo "$hits" | tr '\n' ' ')"
done

# 3. For a person to judge.
emails="$(grep -oE '\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}' <<<"$added" | sort -u | head -10)"
[ -n "$emails" ] && review "email addresses in added lines: $(echo "$emails" | tr '\n' ' ')"
while read -r size path; do
  review "large file (${size} bytes): $path"
done < <(git diff --name-only --diff-filter=AM "$range" | while IFS= read -r p; do
  [ -f "$p" ] && s=$(stat -c %s "$p" 2>/dev/null || stat -f %z "$p") && [ "$s" -gt 5000000 ] && echo "$s $p"
done)
review "commit authors: $(git log --format='%an <%ae>' "$range" | sort -u | tr '\n' ' ')"

if [ "$fails" -gt 0 ]; then
  echo "$fails problem(s): fix them (or drop the files from the commits) before pushing."
  exit 1
fi
echo "OK: nothing that must not be pushed."
