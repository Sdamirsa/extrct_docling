#!/bin/bash
# Run the fork's figure-to-data engine (measured mode) on the bench's 15
# figures with each Ollama vision model, one model at a time. Reads the
# bundles under samples/aca-papers_out, writes only under runs/.
# Run from the repo root:  bash docs/mini-bench/chart-to-data/scripts/run_ollama_models.sh
set -u
BENCH=docs/mini-bench/chart-to-data
MODELS=${MODELS:-"gemma4:12b-it-q8_0 gemma4:26b-a4b-it-qat gemma4:26b-a4b-it-q8_0 gemma4:31b-it-qat gemma4:31b-it-q8_0 qwen3.8:27b-mtp-q8_0 qwen3.8:27b-q8_0"}
for model in $MODELS; do
  name=$(echo "$model" | tr ':/' '__')
  out=$BENCH/runs/$name/all
  [ -f "$out/timing.json" ] && { echo "skip $model (done)"; continue; }
  echo "START $model $(date +%H:%M:%S)"
  uv run --no-sync amir-figdata run --testset $BENCH/testset.json --mode measured \
      --model "$model" --out "$out" --unload-after > "$BENCH/runs/$name.log" 2>&1
  echo "DONE $model rc=$?"
done
