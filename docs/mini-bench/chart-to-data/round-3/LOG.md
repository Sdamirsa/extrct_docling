# Round 3 log: steps and findings, in order

2026-11-18. How round 3 was reached: what was asked, what was built, what
went wrong in our own code on the way, what was run. The results are in
[README.md](README.md); the design and its reasons in
`.claude/reference/figure-data/STANDALONE-STEP.md`.

Read section 9 first: sections 2 to 7 were written while the single
Sonnet call per figure ran through the Claude Code login and was called
"the cloud method". It is not a call to a cloud API, was taken out of the
results, and the cloud method was rebuilt as an API endpoint call, which
then ran on the bench with two models (section 10).

## 1. What was asked

After round 2 the maintainer decided the shape of the step:

- a folder per paper with each chart figure and its text, prepared;
- three ways to read a figure: an open model through Ollama, a cloud
  model, an agentic read (built with Sonnet, able to run on Ollama);
- after the main conversion, and on its own on an output folder;
- a `figure-to-data.md` per figure, and a section at the figure in the
  paper's exports, after the description the conversion's model wrote,
  saying that a model read it;
- the config of every run kept in the folder;
- an agent that takes one figure at a time, is guided, gets a condensed
  context and can be rerun;
- all three methods kept, because the open models are not good enough yet
  and users differ in what they may send out and spend.

The bench was to run the round-2 winner among the open models, Sonnet, and
the Sonnet agent.

## 2. What the Sonnet methods can run on

The build machine has no Anthropic API key and no `anthropic` package; it
has the Claude Code CLI, logged in. Probed before anything was designed:

| Probe | Result |
|---|---|
| `claude -p` started from a script, model `claude-sonnet-5-5`, no tools, our system prompt | works; the model receives 599 tokens for a one-line prompt, so nothing of Claude Code's own prompt, settings or memory reaches it |
| the same with an image in the message and `--json-schema` | works: a three-point interval plot read to a schema in 2.3 s, 0.008 USD |
| Ollama 0.32.14, `POST /v1/messages` (Anthropic-compatible) | answers |

So the cloud method is one headless CLI session without tools, and the
agent is a headless session whose only tools are ours. The API-key path
for the cloud method was written against the SDK's documented call and
has not been exercised (section 7).

## 3. What was built

`docling/engines/figure_data/`: `prepare.py` (phase 1), `methods/`
(`ollama.py` around the unchanged round-2 engine, `cloud.py`, `agent.py`,
`toolbox.py`, `claude_cli.py`), `reading.py` (the reply a cloud model or an
agent gives, the shared conventions, the checks), `report.py`
(`figure-to-data.md`), `step.py` (the three phases, the run record),
`publish.py` (the embed). `amir-figdata prepare | read | embed | step`,
`amir-batch --figure-data ollama|cloud|agent [--figure-data-when end|each]`.
The conversion engine no longer has a figure-data stage.

The local method is the round-2 engine with nothing changed in how it
calls the model. Its bench numbers reproduce round 2 exactly (270 values
returned, 85 within 5 % with names matched, 188 with names ignored), which
is the check that the restructuring left it alone.

## 4. What was wrong in our own code this time

Found on the first figures each new method read, or in the first bench
run. Each is the same kind of fault round 2 was about: ours, not the
model's.

| # | Finding | Evidence | Fix |
|---|---|---|---|
| F13 | **`--safe-mode` also switches off the MCP server that carries the agent's tools.** The session started with no tools, and the model wrote tool calls as text. | first agent probe: `tools: []`, a reply that begins `<invoke name="look">` | `--restricted --disable-slash-commands --strict-mcp-config`: the three tools and nothing else. Same token count in front of the model as with `--safe-mode` (599). A `CLAUDE.md` planted in the working folder was obeyed without these flags and ignored with them. |
| F14 | **Our tool rejected a chart because `notes` came as text instead of a list.** | five-panel ROC figure: five `record_chart` calls refused, then five repeated | the reply model accepts a note as text, a legend as objects, a number where text is expected |
| F15 | **The range check penalised numbers printed for a whole curve.** "87.97 outside the axis range [0, 1]" for a printed AUROC; confidence fell to 0.6, under the threshold for the exports. | the same figure, both Sonnet methods: 15 right values that would not have been embedded | a printed statistic of a curve is not checked against the axes |
| F16 | **The label check called wrapped labels "not printed".** A label on two lines is two OCR lines. | stacked bars: "9 of 11 categories are not printed in the figure"; confidence of 76 right values fell to 0.55 | a label counts as printed when the figure prints each of its words |
| F17 | **The description the conversion's model wrote of a figure states wrong numbers.** | interval plot: described with "a central value of 0.79", the figure shows 0.67 | it is not part of what a reader is given (`figure.txt` holds the paper's caption and the printed text) |
| F18 | **The agent's check feedback said what was wrong and not what to do.** "5 points have neither a category nor an x", "Being Polite sums to 200", then "if they were right, leave it". Its numbers were right, so it left them: pie slices under `series`, two bars under one category. | first agent run: 546 of 560 values within 5 % with names ignored, 150 with names matched (the single call, same model and conventions: 551 and 371) | naming problems are reported apart from value checks, each with how to name the points, and `finish` asks once about charts that still have one; the policy says a naming problem is always the agent's to fix |
| F19 | **The CLI prices local tokens at the provider's list price.** | agent on Gemma: "0.18 USD" for a run on the local GPU | no cost is recorded for the Ollama backend |
| F20 | **A local model leaves out fields the tool insisted on.** | agent on Gemma: first `record_chart` refused for `x_axis.name` and `points.0.x` | the schema still marks them required, a reply without them is read, and the check says what is missing |
| F21 | **A reading under the confidence threshold left no trace at the figure.** | local model on the interval plot: right values at confidence 0.5, nothing in the markdown | the figure carries the note as a pointer to its `figure-to-data.md` |
| F22 | **The reading's header said a model read every value**, also those the engine measured on the PDF's drawing. | vector bar chart in the unit test | "Machine-read from the figure", and a legend for the `from` column |
| F23 | **Prepare skipped a figure whose text layer holds half a surrogate pair**: the evidence file could not be written. | found by the splitter check on the other papers: three figures (two of CardAIc-Agents, one of Risk-Score-Interfaces_Supplementary) | the character is replaced before anything is written; both CardAIc figures now prepare |

On F18, what the rerun does and does not show: in the second run the
agent named the pies and the stacked bars as the conventions say at its
first attempt, so the new feedback never had to fire. The policy sentence
is the likelier cause, and one run each cannot rule out chance.

## 5. The conventions, and what they owe to the truth

`reading.CONVENTIONS` is the text both Sonnet methods get. It was written
with the truth's conventions in view (`../truth/README.md`), like the
local engine's prompt in round 2. One rule was added after looking at a
probe on this test set: a stacked bar is one category, and when a tick
label carries two bars each is "<tick label> - <group>" (the truth's
form). The step's stack check needs that form in any case, but the
wording was chosen with this bench's figure open. See Limits in the
README.

## 6. The runs

All from the same prepared folders (`amir-figdata prepare --testset`, 23 s
for the 15 figures, CPU only), one copy per method.

| Run | When | Seconds | Values | Cost | Note |
|---|---|---|---|---|---|
| `ollama-gemma4-26b-qat` | first wave | 344 | 270 | local | truth and judge folders locked |
| single Sonnet call through the Claude Code login | first wave | 228 | 560 | 0.70 USD | locked; first reported as "cloud", withdrawn (section 9), files deleted |
| agent, first run | first wave | 392 | 560 | 1.24 USD | locked; kept in `superseded/agent-sonnet-5-5-v1` |
| `agent-sonnet-5-5` | after F18 | 382 | 470 | 1.12 USD | not locked: a session has no file tool (`AUDIT.md`) |

The agent returned 180 values for the three-panel line chart in its first
run and 90 in its second: the second time it left the raw dots behind the
lines out and said so. The same agent on the same figure does not decide
the same way twice.

Automatic scorer, values within 5 % of the axis, of 560: local 85 named /
188 names ignored; the withdrawn single call 371 / 551; agent 368 / 458
(first run 150 / 546). The cloud method's runs through the endpoint are in
section 10.

## 7. Tried and dropped, or not done

- **`--safe-mode`** for the agent (F13).
- **`anthropic-api` backend.** Written for the cloud method with the
  SDK's `messages.parse`; not run once, for want of a key, and removed
  when the endpoint run showed it could not have worked (F25, section
  10). The cloud method's one backend is the endpoint of section 9.
- **An agent loop of our own**, without the Claude Code CLI. Not built:
  the CLI session confined to one MCP server does what was asked, runs on
  the login the maintainer has, and on Ollama.
- **Changing the local engine.** Left as round 2 froze it. Its prompt does
  not have the stacked-bar rule of section 5.
- **The folder lock for the reruns.** It protects against a reader with
  file tools; none of this round's readers has one.

## 8. The agent on a local model (an extra)

`--backend ollama` points the same session at Ollama's Anthropic-compatible
endpoint. Gemma 4 26B-A4B (4-bit QAT) used the tools. The run was given
300 s per figure and stopped by hand after seven figures and 887 s
(`extra/agent-gemma4-26b-qat`):

| Figure | Seconds | Tool calls | Result |
|---|---|---|---|
| C5, three pies | 171 | 10 | 15 of 15 printed values |
| C3, dense stacked bars | 300 (stopped) | 4 | 44 values of one chart kept, 44 within 5 % with names ignored |
| C2, a schematic | 280 | 40 | declined, after looking 40 times |
| A1, A2, A4, diagrams | 16, 17, 22 | 1 to 2 | declined |
| A3, interval plot | 80 | 4 | three centres and six bounds right |

It works, what it had recorded survives a stop, and it is several times
slower than the same model inside the measured engine (9 s and 4 s for A3
and C5). Ollama loads the model with a 262,144-token context for it
(17 GB). Not one of the three methods compared, and not judged.

## 8a. The splitter, checked on its own

Asked for by the maintainer during the round; done by a separate agent
(`splitter-page/`, page kept private). Two things it found change what
earlier rounds said:

- Round 2 reported 33 of 33 charts found. That is the engine with the
  chart count from the model's overview call. The splitter alone, which
  is what the prepare phase runs, finds 32: the vector figure C4 stays one
  box. The cloud and agent methods therefore got C4 as one chart, read
  both its charts anyway, and put both under the whole-figure box.
- On 30 data figures of other papers, judged once by eye, 7 are cut
  cleanly and 19 wrongly. The splitter was built on the bench's figures.

## 9. Correction: what "cloud" has to mean

The maintainer, after the first report: a single call through the Claude
Code login is not how a cloud API works; the cloud method has to call a
model's API endpoint with a key, as with an Ollama endpoint or OpenRouter,
and the Sonnet single-call result has to stay out of the report if that
cannot be run. Then: build the endpoint, the key in `.env`, and the
method.

What was done:

- **The cloud method is now an API endpoint call** (`methods/endpoint.py`,
  `methods/cloud.py`): one `POST <base url>/chat/completions` per figure in
  the OpenAI chat-completions format, images as data URLs, the reply as
  JSON to a schema. Default endpoint OpenRouter, default model
  `anthropic/claude-sonnet-5.5` (taken from OpenRouter's public model
  list: image input, `response_format` and structured outputs supported).
  The key is read from `OPENROUTER_API_KEY` in the environment or in the
  nearest `.env`; it is never an option and never written into a run
  record. `--figure-data-base-url` and `--figure-data-key-env` name another
  endpoint. The Claude Code CLI is no longer a backend of this method; it
  is the agent's runtime.
- **Checked without a cloud key.** Unit tests of the request, the reply,
  the retry after a busy reply, the fallback when an endpoint rejects
  `response_format`, and the key lookup. Live against the local Ollama
  endpoint (`--base-url http://127.0.0.1:11434/v1`, Gemma 4 26B-A4B) on six
  prepared figures: the interval plot's three centres right, the 15
  printed AUROC values of the five-panel figure right, four diagrams
  declined; 16 to 118 s a figure. Without a key the default endpoint is
  not called: the figure is recorded as failed, "no API key: set
  OPENROUTER_API_KEY in the environment or in a .env file".
- **No cloud model was called.** No key for OpenRouter, Anthropic or any
  other provider is on the build machine.
- **The single-call run left the results.** For the record: 560 values,
  551 within 5 % with names ignored, 228 s, 0.70 USD at the CLI's list
  prices, ten of ten data charts correct by its judge. It was not a result
  of the cloud method and not in the report. Its files were first kept
  under `extra/` and deleted the same day on the maintainer's word, once
  the method could be run through the endpoint (section 10).
- A `.env.example` could not be added (the project's permission settings
  deny writing files of that name); the variable is documented in `RUN.md`.

## 10. The cloud method on the bench

The maintainer put an OpenRouter key into `.env` and asked for the method
on the bench, and for one Google model, Gemini Flash, beside Sonnet.
`google/gemini-3.8-flash` is the newest Gemini Flash in OpenRouter's model
list with image input and structured output. The files of the withdrawn
single-call run were deleted on the same word.

Two settings were decided before the runs. The call sends
`reasoning_effort` high: the agent's sessions run at effort high, and a
call that reads a dense chart without thinking is not the method at its
best. The output limit, which thinking shares, went from 16,000 to 32,000
tokens.

What the calls showed in our own code:

| | Found | Seen on | Now |
|---|---|---|---|
| F24 | **An enforced schema with optional fields lost the upper bound of every interval.** Gemini wrote `err_lo` and left `err_hi` out of each point, three tries of three; with the schema only in the prompt it wrote both, two of two. | smoke test on the interval plot: centre 0.67, low 0.52, high empty | every field of the schema sent to an endpoint is required, the nullable ones written as null: both bounds, two of two |
| F25 | **Anthropic refuses the reading's schema as an enforced format**: "limit: 16 parameters with unions"; the reading has 22 nullable fields. | Sonnet's first request, HTTP 400 through OpenRouter | the fallback that was built took over (ask again without `response_format`, do not send it again): Sonnet had the schema in the prompt only, and all 15 replies parsed. The `anthropic-api` backend, never run, relied on the enforced format and was removed. |
| F26 | **Thinking can eat the output limit.** Sonnet used 24,192 tokens for the dense stacked bars, 4,013 of them thinking. Gemini thought for 26,356, was cut at 32,000 and had written 93 of 264 values. | Gemini's first run, C3 | limit 64,000. Second run: all 264 values, 52,491 tokens. |
| F27 | **An empty reply was a failed figure.** HTTP 200 with no content after 130 s, once in some 55 calls. | Gemini's second run, the line chart B2 | an empty reply is asked for once more; if it stays empty the error says how the reply ended. B2 was read again on its own: 84 values, 161 s. |

The runs:

| Run | Output limit | Seconds | Values | Within 5 %, named / names ignored | Cost | Output tokens (of them thinking) |
|---|---|---|---|---|---|---|
| `cloud-sonnet-5-5` | 32,000, not reached | 257 | 560 | 372 / 552 | 0.70 USD | 49,656 (6,854) |
| Gemini, first run (`superseded/cloud-gemini-3-8-flash-v1`) | 32,000 | 939 | 299 | 91 / 181 | 0.62 USD | 140,255 (115,010) |
| `cloud-gemini-3-8-flash` | 64,000 | 1,181 | 464 | 332 / 437 | 0.73 USD | 173,155 (138,280) |

- Sonnet's run and Gemini's first ran with the truth and judge folders
  locked. Gemini's second ran without the lock, because the judge of
  Sonnet's run was reading the truth at the time. A cloud call is one HTTP
  request; the model has no file access either way.
- Gemini's 1,181 s and 0.73 USD count the second reading of B2 and not the
  130 s of the empty reply, whose cost was not reported.
- Sonnet's run was made with the limit at 32,000. Its largest reply was
  24,192 tokens, so the limit now in the code would not have changed it,
  and it was not repeated.
- Cost is `usage.cost` as OpenRouter returns it with each reply.
- OpenRouter picks the host of a model per request: the refused Sonnet
  request names Anthropic, Azure and Google as tried. The figure goes to
  OpenRouter and to whichever host it picks.
- Gemini's first run was scored automatically and not judged.

The judges, one per run, fresh, with the round's prompt:

- **Sonnet's call:** correct on all ten data charts, five true negatives,
  nothing above severity 1. All 560 values within 5 % of the axis, 556
  within 2 %; the four beyond are box medians the figure does not draw as
  a line of their own. Cosmetic: its own series names on the line chart
  without a legend, axis tick lists that disagree with the rows in three
  figures, one box for both charts of the vector figure.
- **Gemini's call:** 7 correct, 3 partial (B2, B5, C3), five true
  negatives; 9 of 10 data charts usable. Not usable: C3, where one segment
  boundary is 6 to 10 points off in 12 of 44 bars while every bar still
  sums to 100 and nothing is declared. B5: a box median taken at the other
  box edge (10 % of the range). B2: 84 of 180 values, two of thirty
  vertices per panel dropped, the raw dots left out.

On one paper end to end (scratch copy, `amir-figdata step --method
cloud`): prepare, read and embed in 34 s for 0.08 USD; the interval plot is
embedded at the figure, `check.json` counts 5 eligible, 1 extracted, 4
without data.

## 11. Open after this round

- A round on figures no method was tuned on, before any number here is
  quoted outside the bench.
- Whether the agent earns its extra cost: on these 15 figures one Sonnet
  call per figure returns more for less (560 values for 0.70 USD against
  470 for 1.12 USD). Figures a single call cannot hold (many panels of
  dense marks) are where it should, and there are none here.
- The cloud method through another endpoint than OpenRouter, and a
  setting for the output limit on the command line.
- The axis tick lists a reading carries come from the layout analysis
  and can disagree with the rows (the judge of Sonnet's cloud run:
  "GPT-40", pies given axes). The values are not affected.
- The local engine's open items from round 2 (dense stacked bars, thin
  marks, vector series names) are untouched.
- A showcase run of `default-plusFigData` and release r5.
