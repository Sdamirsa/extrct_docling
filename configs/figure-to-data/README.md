# Recommended configs of the figure-to-data step

The figure-to-data step runs on converted papers: it reads the numbers
behind every chart and writes them into the bundle (the HTML, the markdown,
the chunks, `document.json`, the viewer). These two files are the step's
recommended settings. The conversion is not in them and keeps its defaults.

| Config | Charts read by | The figures go to | Use it when |
|---|---|---|---|
| [`recommended-cloud.toml`](recommended-cloud.toml) | Claude Sonnet 5.5 through OpenRouter, reasoning effort medium, five bundles at a time | OpenRouter and the model host it picks | the values matter and the figures may leave the machine |
| [`recommended-local.toml`](recommended-local.toml) | Gemma 4 26B in Ollama | nowhere | nothing may leave the machine |

On bundles that are already converted:

```bash
uv run amir-figdata step samples/my-papers_out --config configs/figure-to-data/recommended-cloud.toml
uv run amir-figdata step samples/my-papers_out --config configs/figure-to-data/recommended-local.toml
```

With the conversion, in one command:

```bash
uv run amir-batch samples/my-papers -o samples/my-papers_out \
    --figure-data-config configs/figure-to-data/recommended-cloud.toml
```

The keys are the options of `amir-figdata step` (`method`, `model`,
`backend`, `base_url`, `api_key_env`, `ollama_url`, `effort`, `workers`); a
key that is not one of them is an error. Options given on the command line
win over the file, so `--effort high` reads the dense charts at high effort
with the cloud config. A bundle that already holds a reading by the same
method and model is left alone, so a run that stopped can be started again
without paying twice; one whose last reading had failed figures (an
endpoint that refused, out of credit) is read again; `--force` reads every
bundle again.

The cloud config names the environment variable that holds the API key
(`api_key_env`). The key is read from the environment or the repository's
`.env` and is never written into a bundle. Put your own variable's name
there.

What the choices rest on: `docs/mini-bench/chart-to-data/` (rounds 1 to 5)
and `.claude/reference/figure-data/STANDALONE-STEP.md`. The showcase paper
read with both configs: [`showcase/figure-to-data/`](../../showcase/figure-to-data/).
