#!/usr/bin/env bash
# Round 4: one paper through the whole pipeline, once per reading method.
#
#   OUT=samples/round-4-showcase \
#     docs/mini-bench/chart-to-data/scripts/run_round4.sh [label ...]
#
# From the repository root. Each label is one `amir-batch` run of the paper
# into $OUT/<label>/: the conversion with the default options, then the
# figure-to-data step with that label's method and model. The runs go one
# after the other (the conversion and the local model share the GPU). Per
# label: $OUT/<label>.log (the terminal output) and $OUT/<label>.time (exit
# code and wall time of the command). The cloud labels need the endpoint's
# key (OPENROUTER_API_KEY in the environment or .env); the agent label the
# Claude Code CLI, logged in; the ollama label a running Ollama with the
# model pulled.
set -u
PDF=${PDF:-showcase/Public-test-manuscript.pdf}
OUT=${OUT:?set OUT to the output root, e.g. samples/round-4-showcase}
LABELS=${*:-cloud-sonnet-5-5 agent-sonnet-5-5 ollama-gemma4-26b-qat cloud-gemini-3-8-flash}

options() {
  case "$1" in
    ollama-gemma4-26b-qat) echo "--figure-data ollama" ;;
    cloud-sonnet-5-5) echo "--figure-data cloud" ;;
    cloud-gemini-3-8-flash) echo "--figure-data cloud --figure-data-model google/gemini-3.8-flash" ;;
    agent-sonnet-5-5) echo "--figure-data agent" ;;
    *) return 1 ;;
  esac
}

mkdir -p "$OUT"
for label in $LABELS; do
  extra=$(options "$label") || { echo "unknown label: $label"; exit 2; }
  started=$(date +%s)
  # shellcheck disable=SC2086
  uv run --no-sync amir-batch "$PDF" -o "$OUT/$label" $extra > "$OUT/$label.log" 2>&1
  code=$?
  echo "$label exit_code=$code seconds=$(($(date +%s) - started))" | tee "$OUT/$label.time"
done
