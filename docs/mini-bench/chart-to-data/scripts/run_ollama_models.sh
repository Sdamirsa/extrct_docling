#!/bin/bash
# Run the fork's figure-to-data engine (measured mode) on the bench's 15
# figures with each Ollama vision model, one model at a time. Reads the
# bundles under samples/aca-papers_out, writes only under runs/ (of the
# round folder when BENCH_ROUND is set, e.g. BENCH_ROUND=round-2).
# Run from the repo root:  bash docs/mini-bench/chart-to-data/scripts/run_ollama_models.sh
# Choose models with MODELS="tag tag ...".
#
# Rounds 1 and 2 only. It calls `amir-figdata run`, the command of the engine
# at those rounds' commits. From round 3 the engine is the `ollama` method of
# the figure-to-data step (`amir-figdata prepare` / `read`): to run a local
# model on the bench with the current code, use run_round3.sh with
# EXTRA="--model <tag>" LABEL=<name> and the method `ollama`.
set -u
BENCH=docs/mini-bench/chart-to-data
ROUND=$BENCH${BENCH_ROUND:+/$BENCH_ROUND}
mkdir -p "$ROUND/runs"
MODELS=${MODELS:-"gemma4:12b-it-q8_0 gemma4:26b-a4b-it-qat gemma4:26b-a4b-it-q8_0 gemma4:31b-it-qat gemma4:31b-it-q8_0 qwen3.8:27b-mtp-q8_0 qwen3.8:27b-q8_0"}
for model in $MODELS; do
  name=$(echo "$model" | tr ':/' '__')
  out=$ROUND/runs/$name/all
  [ -f "$out/timing.json" ] && { echo "skip $model (done)"; continue; }
  echo "START $model $(date +%H:%M:%S)"
  uv run --no-sync amir-figdata run --testset $BENCH/testset.json --mode measured \
      --model "$model" --out "$out" --unload-after > "$ROUND/runs/$name.log" 2>&1
  echo "DONE $model rc=$?"
done
