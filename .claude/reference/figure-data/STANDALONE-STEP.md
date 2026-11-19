<!-- last-reviewed: 2026-11-19 -->
# The figure-to-data step: design, as built

Status: **built** on 2026-11-18 (step version 3), run through `amir-batch`
end to end with all four setups on 2026-11-19. This file is the shape of
the step and the reasons for it. Measured results are in
`docs/mini-bench/chart-to-data/round-3/` (15 prepared figures) and
`round-4/` (one whole paper through the pipeline); the measured engine
behind the local method is in `DESIGN.md`. It replaces the design note of 2026-11-17
("design, not built"); what changed against that note is in section 8.

## 1. What was asked for

The maintainer, 2026-11-18:

- one folder per paper that holds each figure and its text, prepared for a
  reader;
- three ways to read a figure: an open model through Ollama, a cloud
  model, or an agentic read (built with Sonnet, able to run on Ollama);
- the step runs after the main conversion, and on its own on an output
  folder;
- every method writes a `figure-to-data.md` per figure, and the reading can
  be embedded at the figure, after the description the conversion's model
  wrote, with a note that a model read it;
- the config of every run stays in the folder;
- the agent works on one figure at a time, is guided, gets what it needs
  and no more, and can be rerun by someone else;
- all three methods stay: the open models do not reach an acceptable level
  yet, so users choose by what they may send out, what they may spend and
  how good the numbers must be.

## 2. Shape: three phases on a finished bundle

| Phase | Code | Model | What it does |
|---|---|---|---|
| prepare | `figure_data/prepare.py` | none | captures each chart candidate from the PDF at high resolution, collects its printed text (PDF text layer merged with OCR), finds its charts, writes one folder per figure |
| read | `figure_data/methods/` | one of three | turns each prepared folder into a reading |
| embed | `figure_data/publish.py` | none | writes the readings into the paper's exports at the figure |

`figure_data/step.py` runs them (`prepare_step`, `read_step`, `embed_step`,
`run_step`). The step never runs inside a conversion: it reads a finished
bundle and its PDF. That gives one code path for the three ways it is
started (after each PDF, at the end of a batch, later on any output
folder), and a failure in it cannot take a conversion with it.

## 3. The folder

```
<bundle>/figure-to-data/
├── README.md                 what this folder is (for a person or an agent who opens it)
├── prepare.json              every picture of the paper: prepared, or why not
├── runs/<run id>.json        one per run: method, model, options, prompts, outcome per figure
└── pictures_3/               one folder per figure = one unit of work
    ├── figure.png            the figure at high resolution (PDF render at 220 dpi, or the
    │                         embedded bitmap when that is sharper, on white where its
    │                         soft mask makes it transparent; at most 3,200 px)
    ├── figure.txt            what a reader is told beside the image
    ├── evidence.json         the same evidence for code: words with boxes, charts found,
    │                         the PDF's drawing paths
    ├── panel-1.png ...       one crop per chart, when the figure holds several
    ├── figure-to-data.md     the reading, for people and agents
    ├── figure-to-data.json   the same reading, extrct.figure-data/1
    ├── result.json           how it was obtained: calls, seconds, tokens, cost, checks
    ├── overlay.png           ollama: where the engine placed its marks
    ├── trace.json            cloud: the model's reply; agent: the session's event stream
    │                         without image data
    └── agent-reading.json    agent: what it recorded through its tools
```

Why it is laid out this way:

- **A folder per figure.** A reader, above all an agent, is pointed at one
  folder and needs nothing outside it. "One figure at a time" then is a
  property of the layout, not a rule a prompt has to enforce.
- **Image and text as separate files.** A model needs the image as an
  image. The text comes twice because its two readers differ: `figure.txt`
  is short and written for a model (caption, charts found with their tick
  labels, printed text with rough positions); `evidence.json` is complete
  and written for code (every word box, every drawing path).
- **Inputs kept.** What a model was given can be looked at afterwards, and
  a method can be rerun or swapped without the PDF.
- **The conversion's own figure description is left out of `figure.txt`.**
  It states numbers the figure does not show (seen on the first figure
  looked at: an interval plot described with invented centre values), and
  a reader that is told a number tends to repeat it.
- **`runs/` keeps every run**; a figure folder holds the latest reading.
  Its markdown names the run that wrote it.

## 4. The three methods

One interface, `FigureReader.read(prepared, figure_dir) -> FigureDataResult`
(`methods/__init__.py`); each method reads the same folder and returns the
same record.

| | `ollama` | `cloud` | `agent` |
|---|---|---|---|
| What reads | a local open-weight model inside the measured engine | one call to a cloud model's API endpoint | one agent session |
| Default model | `gemma4:26b-a4b-it-qat` | `anthropic/claude-sonnet-5.5` on OpenRouter | `claude-sonnet-5-5` |
| The figure goes to | nowhere | the endpoint (OpenRouter and the model host it picks) | the model's provider (nowhere with `--figure-data-backend ollama`) |
| Calls per figure | one overview call, then one per chart | one | one session, several tool calls |
| Needs | Ollama and a GPU | an API key in the environment or `.env` | Claude Code CLI, logged in |
| Code | `methods/ollama.py`, `pipeline.py` | `methods/cloud.py`, `methods/endpoint.py` | `methods/agent.py`, `methods/toolbox.py`, `methods/claude_cli.py` |

Backends (`--figure-data-backend`):

- `ollama`: the local method, and the agent on a local model.
- `openai-compatible` (cloud): `POST <base url>/chat/completions`
  in the OpenAI format, which OpenRouter, most providers and a local
  Ollama's `/v1` speak. Base URL `cloud_base_url` (OpenRouter), key from
  the variable `cloud_api_key_env` (`OPENROUTER_API_KEY`) in the
  environment or the nearest `.env`. The key is never an option, never
  logged, never in a run record. No sampling parameter is sent (current
  models refuse a non-default temperature). The reply schema is sent as
  `response_format` and also stands in the system message. Every field of
  that schema is required, the nullable ones too: with optional fields,
  Gemini 3.8 Flash under an enforced schema wrote `err_lo` and left
  `err_hi` out of every point (three tries of three), and wrote both when
  the schema stood only in the prompt. `reasoning_effort` is sent
  (`cloud_reasoning_effort`, default `high`, as the agent's sessions run);
  the reply and the model's thinking share `cloud_max_output_tokens`
  (64,000: on the densest bench figure Sonnet 5.5 used 24,000, Gemini 3.8
  Flash thought for 26,000 and was cut at a first limit of 32,000; a model
  that allows fewer output tokens needs a lower value, which is an option
  of the Python API only). An endpoint that rejects `response_format` or
  `reasoning_effort` is asked again without the field and not sent it
  again. The local `trace.json` keeps the reply, the endpoint's usage
  block and which of the two fields the endpoint accepted.
- `claude-cli` (agent, the default): the Claude Code CLI without a
  terminal, on its own login.

The cloud method is an API call by decision of the maintainer
(2026-11-18): a first version sent the single call through the Claude
Code login, which is not how a cloud API is used, and its bench result
was withdrawn. The Claude Code CLI is the agent's runtime only.

### What each method carries over from rounds 1 and 2

| What the bench showed | `ollama` | `cloud` | `agent` |
|---|---|---|---|
| Text printed in the figure must reach the reader | word list with positions in every prompt | `figure.txt` | `figure.txt`; `look` returns the text of the region it shows |
| A model given several charts in one image merges them | charts are cut apart by their tick labels; one call per chart | the figure plus one crop per chart in the same call | `look` on one chart at a time; the charts found are listed |
| A model sees an image at a fixed level of detail | each chart crop gets the whole budget | each chart crop is its own image | `look` on a region enlarges it up to four times |
| It must be able to say "not a chart" | overview call first | `has_data` in the reply | step 1 of the policy; `finish` with `has_data` false |
| A model leaves out what it may | naming fields required in the reply schema | the same | the same; a reply without them is still accepted and the check says what is missing |
| A long reply must not be lost | streamed, cut at a deadline, complete points kept | one reply to a schema | one chart per tool call; what is recorded is on disk at once |
| A local model points worse than it reads | pointed and read value are cross-checked | no positions asked for at all | no positions asked for |
| Printed numbers beat measured ones | printed labels replace measured values | `label`; confirmed against the printed text | the same |
| Nothing invented, and say what was left out | `uncertain` | `not_read` | `not_read`; `finish` asks about charts not recorded |

The conventions that turn a mark into a point are one text
(`reading.CONVENTIONS`) shared by `cloud` and `agent`, and the same rules
the local engine's prompt states.

## 5. The agent

- **One session per figure.** The runner starts a fresh session for every
  figure folder. Nothing read in one figure is in the context of the next.
- **Runtime.** A Claude Code session without a terminal (`claude -p`),
  stripped down: `--tools ""` (no built-in tool at all), `--restricted`
  and `--disable-slash-commands` (no settings, memory files, skills or
  commands of the user or the project), `--strict-mcp-config` (no MCP
  server but ours), `--system-prompt` (our policy instead of Claude Code's
  prompt), an empty working directory, `--effort` fixed in the options.
  Measured: the model receives our prompt, the three tool definitions and
  the one message, and nothing else.
- **Context.** System prompt: `agent.POLICY` (the order of work, then the
  conventions). One user message: the figure image and `figure.txt`.
- **Tools** (`methods/toolbox.py`, served over MCP by
  `python -m docling.engines.figure_data.methods.toolbox <figure folder>`):
  `look` (an enlarged view of the figure, a chart or a region, with the
  text printed there), `record_chart` (one chart; the reply is what the
  checks found), `finish` (what the figure is, what was left unread).
- **Confinement by construction.** The server holds one figure folder and
  offers nothing else. The session has no file, shell or web tool, so it
  cannot read another figure, the paper, or a reference answer. Each
  session's event stream lists the tools it was offered; the bench checks
  that list (`collect_round3.py --audit`).
- **Checks are fed back, with the fix.** A naming problem (a pie slice
  under `series`, two bars under one category) is reported together with
  how to name the points; a value check (outside the axis, an interval
  that misses its centre, a stack that does not add up) says where to
  look again. The first bench run reported both kinds only as "what is
  wrong" and told the agent to keep a reading it believed in; it kept
  right numbers under wrong names.
- **Repeatable.** The policy and the options are written into every run
  record. What is not pinned is the model behind the model name and the
  Claude Code version (`2.1.326` when built).
- **On Ollama.** `--figure-data-backend ollama` points the same session at
  Ollama's Anthropic-compatible endpoint. A reading by a local model
  starts at the local confidence (0.5), not the cloud one.

## 6. The embed

For every figure with a reading, at the figure, after the description the
conversion's model wrote:

- the note "Figure data, read from the image by a vision model (method,
  model, date). These are not the authors' numbers: check them against
  the figure. Full reading: figure-to-data/<figure>/figure-to-data.md."
- the table of the charts whose median confidence reaches
  `min_confidence_for_markdown` (0.7). Charts under it are named as left
  out; when no chart reaches it the note stands alone as a pointer. A
  shaky number in a table reads like data, a pointer does not.

| File | What changes |
|---|---|
| `document.json` | picture `meta.amir__chart_data` (the record), `meta.tabular_chart` (table and note) |
| `figures.jsonl` | `chart_data`; a figure that was looked at and holds no data has a record without panels whose `uncertain` says why |
| `<name>.md`, `<name>.embedded.md` | note and table inside `<!--<annotation kind="chart_data">-->` |
| `chunks.jsonl` | rebuilt, so the tables are retrievable |
| `<name>.html` | note and table in the model-generated metadata box; manifest entry |
| `preview.html`, `preview.embedded.html` | rebuilt from the bundle's files (`visualizer.rebuild_html_preview`): a `data` tag on the figure's box, in its side panel the note, the table and a link to the full reading; a chip in the header counts the figures with data |
| `run.json` | a `figure_to_data` block: run id, method, model, counts. Absent = the step never ran |
| `check.json` | `figure_data`: eligible, extracted, no_data, verified, low_confidence |

The page viewer was left as the conversion wrote it until round 4
(2026-11-19): a person who opens a bundle opens the viewer first, and saw
nothing of the step there.

Confidence a value starts at: printed and confirmed 0.95, measured on PDF
paths 0.90, printed 0.85, a cloud model's reading 0.80 (289 of 290 such
values were within 5 % of the axis in round 2), measured on pixels 0.70 to
0.80, a local model's reading 0.50. A failed check takes 0.25 off.

## 7. Starting it

```
amir-batch <pdfs> --figure-data ollama|cloud|agent
           [--figure-data-model M] [--figure-data-backend B]
           [--figure-data-base-url U] [--figure-data-key-env V]
           [--figure-data-ollama-url U] [--figure-data-when end|each]

amir-figdata step <output folder or bundles> --method ...
amir-figdata prepare | read | embed ...      # phase by phase
```

- `default-plusFigData` is `amir-batch <pdfs> --figure-data ollama`.
- `--figure-data-when end` (default): the conversion models are released
  first and the reading model loads once. `each`: after each PDF.
- A bundle whose `run.json` already names this step version, method,
  backend and model is left alone, so an interrupted batch continues, and
  another method reads again.
- `--out DIR` on `prepare` keeps the folders outside the bundles (the bench
  uses it; nothing is embedded then).

## 8. What changed against the note of 2026-11-17, and why

| Then | Now | Why |
|---|---|---|
| "Local models only" | three methods; local stays the default | the maintainer's decision: the open models are not good enough yet, and who may send a figure out is the user's call. Every method says where the figure goes. |
| a stage inside the conversion plus `--publish` afterwards | one step on the finished bundle | the two paths had already drifted (chunks). `PdfEngine` no longer takes `figure_data`. |
| records under `figure_data/` | `figure-to-data/` with a folder per figure | inputs, reading and run config in one place; one figure = one unit of work |
| source image optional | always kept | it is what the readers read; 0.2 to 2 MB a figure |
| low-confidence values silently absent from the exports | a pointer at the figure | a reader should know a reading exists and where |
| `chunks.jsonl`, `run.json` not updated | both updated | asked for: "every place that needs it" |

## 9. Failure and time

- A figure a reader fails on is recorded (`failed`, with the reason) and
  the next one is read. A bundle the step fails on leaves the conversion
  as it was.
- Files are written per figure, the run record after every figure.
- `ollama`: a call is cut after 120 s and keeps its complete points; no
  new call starts once a figure took 600 s. `cloud`, `agent`: a session is
  stopped after 600 s or past 2 USD (`max_cost_usd_per_figure`); what an
  agent had recorded is kept.

## 10. Not done

- Seen on one whole paper (round 4, `docs/mini-bench/chart-to-data/round-4/LOG.md`)
  and open: the chart splitter was wrong on six of eleven chart figures
  (one chart in blocks cut in two, grids of bar charts miscounted); a
  reading's chart takes the box of the prepared chart with the same id,
  also after a wrong split; the agent leaves the unlabelled segments of
  some stacked bars out though the conventions ask for every segment;
  the vector reader takes a bar that fills 90 % of its chart's box for a
  frame; the batch process still held 8.7 GiB of GPU memory while the
  step ran.

- The cloud method was run through OpenRouter only (Claude Sonnet 5.5 and
  Gemini 3.8 Flash, round 3), and against a local Ollama endpoint. No
  other provider's endpoint was tried.
- A backend on Anthropic's own SDK (`anthropic-api`, structured output
  through `messages.parse`) was written and removed without ever being
  run: Anthropic refuses the reading's schema as an enforced output format
  ("limit: 16 parameters with unions"; the reading has 22 nullable
  fields), seen through OpenRouter. On the endpoint the method falls back
  to the schema in the prompt, and all 15 bench replies parsed.
- The agent needs the Claude Code CLI; there is no loop of our own for an
  API key without it.
- With `--compare` the step is skipped (two bundles per PDF); run
  `amir-figdata step` on the one that is kept.
- The local engine is the round-2 engine, unchanged: dense stacked bars,
  thin marks and vector series names are as they were.

## 11. Documents that describe it

`README.md` (config table, what you get), `RUN.md`, `DESIGN.md` (engine),
`docs/mini-bench/chart-to-data/round-3/` and `round-4/` (results, log, run
records), the
usage skill under `docling/.agents/skills/docling/`.
