#!/usr/bin/env bash
# Round 3: the three methods of the figure-to-data step on the same prepared
# figures.
#
#   WORK=<folder outside the repository> \
#     docs/mini-bench/chart-to-data/scripts/run_round3.sh [ollama cloud agent]
#
# From the repository root. $WORK/prepared is made once (no model); each
# method reads its own copy, $WORK/<method>, so that all three start from
# the same images and context. EXTRA holds further `amir-figdata read`
# options for a variant, LABEL the name of its copy (default: the method).
# The truth and the judges' files are unreadable while the readers run; the
# cloud and agent sessions have no file tool in any case.
set -u
BENCH=docs/mini-bench/chart-to-data
WORK=${WORK:?set WORK to a folder outside the repository}
METHODS=${*:-ollama cloud agent}

if [ ! -d "$WORK/prepared" ]; then
  CUDA_VISIBLE_DEVICES='' uv run --no-sync amir-figdata prepare \
    --testset "$BENCH/testset.json" --out "$WORK/prepared" || exit 1
fi

LOCKED="$BENCH/truth $BENCH/judge $BENCH/round-2/judge $BENCH/round-2/sonnet $BENCH/round-3/judge"
restore() { for d in $LOCKED; do [ -d "$d" ] && chmod 775 "$d"; done; }
trap restore EXIT
for d in $LOCKED; do [ -d "$d" ] && chmod 000 "$d"; done

for method in $METHODS; do
  label=${LABEL:-$method}
  [ -d "$WORK/$label" ] || cp -r "$WORK/prepared" "$WORK/$label"
  (
    # shellcheck disable=SC2086
    uv run --no-sync amir-figdata read "$WORK/$label" --method "$method" \
      ${EXTRA:-} > "$WORK/$label.log" 2>&1
    echo "$label finished, exit code $?"
  ) &
done
wait
