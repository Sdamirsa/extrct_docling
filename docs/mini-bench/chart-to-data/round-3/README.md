# Chart-to-data mini bench, round 3

Rounds 1 and 2 ([`../README.md`](../README.md), [`../round-2/README.md`](../round-2/README.md))
asked which local model reads charts and how much of its failure was our
engine. Round 3 follows a decision of the maintainer: figure-to-data
becomes a step of its own after the conversion, with three ways to read a
figure, and all three are kept so that users can choose.

Run on 2026-11-18: the same 15 figures, truth, scorer and judge prompt.
One prepare pass, then the methods on the same prepared folders. How the
round got here, with what went wrong in our own code on the way, is in
[`LOG.md`](LOG.md); the design of the step and its reasons in
`.claude/reference/figure-data/STANDALONE-STEP.md`.

**All three methods have a result here.** The cloud method, one call per
figure to a model's API endpoint, ran with two models through OpenRouter:
Claude Sonnet 5.5, its default, and Gemini 3.8 Flash, the Google model the
maintainer asked for.

## Answer

When the figure may leave the machine, both ways of sending it to Claude
Sonnet 5.5 return usable data for all ten data charts and nothing that
would mislead. One API call per figure returned every one of the 560
values for 0.70 USD; the agent returned 470 for 1.12 USD. Gemini 3.8 Flash
in the same call: nine of ten charts usable, 464 values, four and a half
times the time and the same cost. The local model is where round 2 left
it: six of ten charts usable, two that would mislead.

| Method | usable data charts (of 10) | figures that would mislead | no-data figures left alone (of 5) | values returned (of 560) | within 5 %, names ignored | time, 15 figures | cost, 15 figures | the figure goes to |
|---|---|---|---|---|---|---|---|---|
| `ollama`: Gemma 4 26B-A4B (4-bit QAT) in the measured engine | 6 | 2 | 5 | 270 | 188 | 344 s | local GPU, 16 GB | nowhere |
| `cloud`: Claude Sonnet 5.5, one API call per figure | **10** | 0 | 5 | **560** | **552** | 257 s | 0.70 USD | OpenRouter and the host it picks |
| `cloud`: Gemini 3.8 Flash, one API call per figure | 9 | 0 | 5 | 464 | 437 | 1,181 s | 0.73 USD | OpenRouter and the host it picks |
| `agent`: Claude Sonnet 5.5, one session per figure | **10** | 0 | 5 | 470 | 458 | 382 s | 1.12 USD | Anthropic |
| *round 2: the same local model, the engine before the step* | 6 | 2 | 5 | 270 | 188 | 343 s | local GPU | nowhere |
| *round 2: Sonnet, bare images, all 15 in one session* | 9 | 0 | 5 | 290 | 284 | 134 s | not recorded | Anthropic |

"Usable" and "would mislead" (severity 3) are the judges' verdicts; the
value counts are the automatic scorer with names ignored, an upper bound.
The cloud calls cost what OpenRouter charged per request. The agent runs
through the Claude Code CLI on its own login; its cost is what the CLI
reports per session, at list prices. Gemini's row is its second run, with
one figure read again after an empty reply (see [The cloud
method](#the-cloud-method)).

**Which method.**

- **Nothing may leave the machine: `ollama`.** Printed numbers, pies and
  simple bar or interval charts are right; box plots, dense lines and
  stacked bars are not. Its low-confidence readings stay out of the
  paper's exports and leave a pointer. Review what it writes.
- **The figures may leave and you have an API key: `cloud` with Sonnet
  5.5.** Every value of the bench, the least time and the least cost of
  the methods that send the figure out. One paper's five chart candidates
  (four are not charts) take 18 s and 0.08 USD on top of a 379 s
  conversion.
- **The figures may leave and you have Claude Code but no API key:
  `agent`.** The same ten charts usable. It left 90 values out and said
  so, and its readings are checked and corrected in the loop. 54 s and
  0.13 USD for the same paper.
- **Gemini 3.8 Flash in the cloud call** is no saving on these figures. It
  thinks for four fifths of its output, so it costs as much as Sonnet and
  takes four and a half times as long, and its reading of the dense
  stacked bars is wrong in 23 of 264 values without saying so.

The open models are not good enough to publish chart numbers unreviewed.
That was round 2's conclusion and it stands.

## What moved Sonnet from 9 of 10 and 290 values to 10 of 10 and 560

Round 2's Sonnet run had the bare images, all fifteen in one session, and
no conventions beyond a paragraph. It was precise and left half the values
out. Both Sonnet methods now read each figure on its own, with

- the paper's caption and the text printed in the figure (PDF text layer
  merged with OCR),
- every chart enlarged: one crop per chart in the call, a tool to look at
  a chart or a part of it for the agent,
- the conventions that turn a mark into a point, spelled out per chart
  kind,
- for the agent, our checks fed back when it records a chart.

The dense stacked bars went from 84 to 264 of 264 values with both. The
three-panel line chart came back whole from the call (180 of 180) and
half from the agent in this run (90; its first run returned all 180).

## The methods, figure by figure

Verdicts of the judges (C correct, p partial, w wrong, tn no data and
nothing returned). A1 to A5 are every chart candidate of one paper.

| | A1 | A2 | A3 | A4 | A5 | B1 | B2 | B3 | B4 | B5 | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ollama` | tn | tn | C | tn | tn | C | p | C | C | p | C | tn | **w** | **p** | C |
| `cloud`, Sonnet 5.5 | tn | tn | C | tn | tn | C | C | C | C | C | C | tn | C | C | C |
| `cloud`, Gemini 3.8 Flash | tn | tn | C | tn | tn | C | p | C | C | p | C | tn | p | C | C |
| `agent` | tn | tn | C | tn | tn | C | p | C | C | p | C | tn | C | C | C |

Bold: would mislead (severity 3).

- **`cloud`, Sonnet 5.5.** Every value within 5 % of the axis, 556 of 560
  within 2 %. The four beyond are box medians the figure does not draw as
  a line of their own (up to 4.8 %). What is wrong is cosmetic: its own
  series names on the line chart that has no legend, axis tick lists from
  the layout analysis that disagree with the rows in three figures, one
  box for both charts of the vector figure.
- **`cloud`, Gemini 3.8 Flash.** Printed numbers 48 of 48, bars and point
  estimates within about 1 % of the axis, nothing invented. Three partial
  readings: the dense stacked bars with one segment boundary 6 to 10
  points off in 12 of 44 bars, while every bar still sums to 100 and
  nothing is declared (the one figure its judge calls not usable); a box
  median taken at the wrong box edge (10 % of the range off); the line
  chart with 84 of 180 values, two of thirty vertices per panel dropped
  and the raw dots left out.
- **`agent`.** No wrong number of consequence: everything it returned is
  within 2.7 % of the axis, the 42 printed values are exact, the 264
  stacked segments are off by 0.15 points on average. Its failure is
  omission, declared: it skipped the 90 raw dots behind the lines (B2) and
  left 4 of 30 box medians empty where the median lies on a box edge (B5).
- **`ollama`.** As in round 2. Never invents data for a non-chart,
  transcribes printed numbers without an error (42 of 42), reads simple
  charts well. Box medians snap to ticks and lose their whiskers, the line
  chart comes back as an unkeyed sequence, and the stacked bars as 58
  numbers of which 45 exceed 100 %.

Per figure: [`judge/summary.md`](judge/summary.md), the judges' files in
[`judge/`](judge), the automatic scores in [`metrics/`](metrics).

## Time and cost

| | 15 figures | the 10 data charts | the 5 without data | one paper's 5 candidates | tool calls |
|---|---|---|---|---|---|
| `ollama` | 344 s | 335 s | 9 s | 16 s | |
| `cloud`, Sonnet 5.5 | 257 s, 0.70 USD | 242 s | 15 s | 18 s, 0.08 USD | |
| `cloud`, Gemini 3.8 Flash | 1,181 s, 0.73 USD | 1,131 s | 51 s | 72 s, 0.05 USD | |
| `agent` | 382 s, 1.12 USD | 335 s | 47 s | 54 s, 0.13 USD | 66 |

The dearest figure is the dense stacked-bar one: 112 s and 0.28 USD for
the Sonnet call, 112 s and 0.35 USD for the agent, 331 s and 0.20 USD for
Gemini. Sonnet's fifteen calls wrote 49,656 output tokens, 6,854 of them
thinking, on two figures only. Gemini's wrote 173,155, of which 138,280
were thinking: at less than half Sonnet's price per token it costs the
same here. Preparing the 15 figures takes 23 s on the CPU, once, for all
methods.

## The step, as it now is

Three phases on a finished paper, started by `amir-batch --figure-data
ollama|cloud|agent` (at the end of a batch, or after each PDF) or by
`amir-figdata step <output folder>` at any later time:

1. **prepare** (no model): one folder per chart candidate with the figure
   at high resolution, the context a reader gets, and the evidence for
   code;
2. **read**: one of the three methods writes `figure-to-data.md` and its
   JSON twin into the figure's folder, and the run's options and prompts
   into `runs/`;
3. **embed**: the reading goes into the paper's markdown, HTML, chunks,
   `figures.jsonl` and `document.json` at the figure, after the
   description the conversion's model wrote, under a sentence that says a
   model read it. Charts under the confidence threshold are left out and
   the figure carries a pointer instead.

What the embedded section looks like: [`examples/embedded-section.md`](examples/embedded-section.md)
(the conversion's description of that figure states a centre of 0.79; the
figure and the reading say 0.67).
A whole reading: [`runs/agent-sonnet-5-5/Cardiologent/figure-to-data/pictures_3/figure-to-data.md`](runs/agent-sonnet-5-5/Cardiologent/figure-to-data/pictures_3/figure-to-data.md);
the dense stacked bars as the Sonnet call read them: [`runs/cloud-sonnet-5-5/AMIE-Mx/figure-to-data/pictures_14/figure-to-data.md`](runs/cloud-sonnet-5-5/AMIE-Mx/figure-to-data/pictures_14/figure-to-data.md).
A run record with its prompts: any `runs/<run>/<paper>/figure-to-data/runs/*.json`.

On one paper, end to end (scratch copy, 5 candidates): the local method
37 s including prepare and embed; the Sonnet cloud call 34 s and 0.08 USD,
also with prepare and embed; the agent 62 s and 0.06 USD on the folders
already prepared. The same paper from scratch with
`amir-batch --figure-data ollama`: 515 s in all, of which the conversion
took 471 s (tests were running on the machine beside it; 379 s when it is
alone) and the reading 23 s.

## The agent

One Claude Code session per figure, without a terminal, with our policy as
its whole system prompt (about 900 words), the figure and `figure.txt` as
its one message, and three tools served for that one figure folder:
`look`, `record_chart`, `finish`. It has no file, shell or web tool.
Every session's event stream lists the tools it had and used:
[`runs/agent-sonnet-5-5/AUDIT.md`](runs/agent-sonnet-5-5/AUDIT.md) (15
sessions, the three tools, nothing else).

The first agent run named values wrongly while reading them right, and
the cause was our tool's feedback (LOG.md, F18). That run is kept in
[`superseded/agent-sonnet-5-5-v1`](superseded/agent-sonnet-5-5-v1): 560
values, 546 within 5 % with names ignored, 150 with names matched; the
rerun 470, 458 and 368.

**On a local model.** The same session runs on Gemma 4 26B-A4B through
Ollama (`--backend ollama`). It was stopped after seven figures and 887 s
([`extra/agent-gemma4-26b-qat`](extra/agent-gemma4-26b-qat)): the interval
plot right in 80 s, the three pies right in 171 s, three diagrams declined
in about 20 s each, a fourth after 280 s and 40 tool calls, and the dense
stacked bars cut off at 300 s with 44 values of one chart. It works, and
it is several times slower than the same model inside the measured
engine. Not one of the methods compared.

## The cloud method

One `POST <base url>/chat/completions` per figure, in the OpenAI
chat-completions format that OpenRouter, most providers and a local
Ollama (`/v1`) speak: the figure, one crop per chart, `figure.txt`, and a
JSON schema for the reply. The default endpoint is OpenRouter and the
default model `anthropic/claude-sonnet-5.5`. The API key is read from
`OPENROUTER_API_KEY`, in the environment or in `.env`; another endpoint
and key variable can be named. The call asks the model to think
(`reasoning_effort` high, as the agent's sessions run) and allows 64,000
output tokens, which the reply and the thinking share. The model gets one
request and no tool. OpenRouter picks the host of a model per request, so
the figure goes to OpenRouter and to whichever host that is.

What the first calls to cloud models showed about the call itself, each
fixed before the run that counts ([`LOG.md`](LOG.md), section 10):

- **Gemini left the upper bound out of every interval** when the reply
  schema was enforced by the endpoint, three tries of three, and wrote it
  when the schema stood only in the prompt. Every field of the schema sent
  is now required.
- **Anthropic refuses the reply schema as an enforced format** (it allows
  16 nullable fields, the reading has 22). The method then asks again with
  the schema in the prompt only, as it was built to; all 15 of Sonnet's
  replies parsed.
- **Gemini's first run was cut on the dense figure.** It thought for
  26,000 tokens of a limit of 32,000 and had written 93 of 264 values.
  The limit is now 64,000 and the run was repeated; the first is kept in
  [`superseded/cloud-gemini-3-8-flash-v1`](superseded/cloud-gemini-3-8-flash-v1)
  (299 values, 939 s, 0.62 USD, not judged).
- **One reply of Gemini's second run was empty** after 130 s (the line
  chart, B2). An empty reply is now asked for once more. B2 was read again
  on its own (84 values, 161 s), and the run's numbers count that reading.

Sonnet's run was made with the limit at 32,000; its largest reply was
24,192 tokens, so it was not repeated. A second backend, on Anthropic's
SDK, was written earlier, never run, and removed: it relied on the
enforced format that Anthropic refuses.

An earlier state of this round reported a "cloud" result that was a
single Sonnet call per figure through the Claude Code login. That is not
a call to a cloud API; the maintainer had it taken out of the results and
its files deleted. Its numbers were close to what the same model now
returned through the endpoint (560 values, 551 within 5 %, 228 s).

## The panel splitter, checked on its own

All methods lean on the layout analysis that finds the charts of a
figure: the local method entirely, the cloud call for its crops, the
agent for its list. A separate check ([`splitter-page/`](splitter-page),
`results.json`):

- On the bench's 33 charts the splitter alone finds 32 (9 of 10 figures
  cut exactly); the round-1 splitter found 20. **Round 2's "33 of 33"
  holds only with the chart count from the model's first call**, which
  the local method has and the prepared folders do not: the vector figure
  C4 is prepared as one chart.
- On 41 chart candidates of 14 other papers, judged once by eye, without
  truth: 11 are not charts; of the 30 data figures 7 are cut cleanly, 4
  have a title or legend in the wrong box, 19 are cut wrongly (charts that
  share tick labels merged, heatmap cell values and colour-bar ticks
  taken for axes, an axis cut from its chart).

The splitter was built on the bench's figures in round 2. That it does
this much worse elsewhere is the clearest sign of how much of this
bench's numbers will not carry over, the local method's above all.

## Limits

- **One endpoint.** The cloud method ran through OpenRouter only. Another
  provider's endpoint may accept or refuse other fields; the method drops
  a field an endpoint rejects, which is tested but was needed for Anthropic
  alone.
- **Gemini's result is a second run with one figure read again.** Both
  were our defects (an output limit, no retry for an empty reply), and
  both runs are kept.
- **Tuned on the test set.** Prompts, conventions and checks were written
  with these 15 figures and their truth in view, in this round as in round
  2. One convention (one category per stacked bar) was worded with the
  figure it decides open. The splitter result above says what that can
  mean outside the bench.
- **One run per method.** The agent returned 180 values for the line chart
  in its first run and 90 in its second; Gemini 90 and then 84.
- **Small set, one judge per run.** Ten data charts; each run judged once,
  by a fresh agent that saw no other run and no earlier round. The judge
  of the local run gave the same counts as round 2's judge for the same
  engine (6 usable, 2 misleading), which speaks for the judging being
  stable.
- **Automatic scores still mislead.** The scorer pairs by name: it counts
  the line chart's 90 right values as zero, because the series are named
  by description.

## Next

1. A round on figures nobody tuned on, including figures one call cannot
   hold: that is where the agent should earn its cost, and here it did
   not.
2. The splitter on the failure types the wider check found.
3. A showcase run of `default-plusFigData` and release r5.
4. The cloud method on another endpoint than OpenRouter.

## Files

| | |
|---|---|
| `config.json` | what was run, with which options |
| `LOG.md` | steps and findings in order |
| `runs/<run>/<paper>/figure-to-data/` | the step's folders as each method left them (readings, results, run records; images, inputs and traces are kept locally) |
| `runs/<run>/timing.json`, `AUDIT.md` | one row per figure; what each agent session could and did call |
| `judge/` | the prompt, one verdict file per run, `summary.md` |
| `metrics/` | automatic scores |
| `superseded/` | the first agent run and the first Gemini run |
| `extra/` | not part of the results: the agent on a local model |
| `examples/` | the section as embedded in a paper's markdown |
| `splitter-page/` | the splitter check: builder and numbers |
| `report-page/` | builder of the round's report page |

To repeat it: `WORK=<folder outside the repository>
scripts/run_round3.sh ollama cloud agent` (`cloud` needs
`OPENROUTER_API_KEY` in `.env`; `LABEL=<name> EXTRA="--model
google/gemini-3.8-flash"` runs it with another model), then
`scripts/collect_round3.py`, then `BENCH_ROUND=round-3` with
`scripts/judge_inputs.py`, `scripts/compare_runs.py`,
`scripts/analyze.py` and `scripts/judge_summary.py`.
