# Round 2 log: steps and findings, in order

2026-11-17. The record of how round 2 was reached: what was looked at,
what was found, what was changed, and what was tried and dropped. The
results are in [README.md](README.md).

The question that opened it: in round 1 every model failed the same ways.
How much of that is the model, and how much is the way our engine calls
it?

## 1. Reading the round-1 runs for causes

`runs/<model>/**/timing.json` already held, per figure, the split method,
the number of calls and the tokens. Laid side by side for all seven Ollama
models, three things stood out before any new experiment.

- The split method was the same for every model on every figure. The
  split is code, not a model call.
- Gemma's prompt held 436 to 949 tokens in total for a whole figure, text
  included.
- "No output" figures had zero calls recorded and a time just over the
  budget or the timeout.

## 2. Findings

Each was confirmed with a probe before anything was changed. The probes
that can be rerun are in `../scripts/`.

| # | Finding | Evidence |
|---|---|---|
| F1 | **The panel split is ours and it misses packed panels.** It cuts at white gutters at least 1 % of the image side wide. Papers pack panels closer. | Gutters found: 4 px in a 717 px figure (B3), 11 px in a 3,074 px figure (B2). Panels found against the truth: B2 1 of 3, B3 1 of 5, B5 9 of 10, C3 2 fragments of 3, C4 1 of 2. |
| F2 | **A figure that was not split went to the model as "one chart panel"**, with a reply format that holds one panel. | The grounded prompt and schema in `readers/vlm.py` at round 1. This is the "panels merged" failure the judges put first for six of eight models. |
| F3 | **The text printed in a figure often never reached the model.** If the PDF text layer had three characters or more inside the figure box, the engine used it and dropped the OCR. | B3: 5 words used, 89 OCR lines unused, among them all 15 printed AUROC values. B4: 3 words (the watermark). B5: 4 words, no tick label on any of ten panels. C4: 7 words. |
| F4 | **Without tick labels there is no axis**, and the value the engine reports is the model's own estimate instead of a measured one. | Same four figures: no calibrated axis in round 1. |
| F5 | **A reply that reaches the token limit was thrown away whole.** | Reproduced on B2 and on A5 with Gemma 26B: the reply stops at about 20,000 characters, the JSON is cut, the parse fails, the panel is "not read". This is every "no output" on B2 in round 1. |
| F6 | **The reply format was three to four times longer than it needs to be.** Twelve keys per point, nulls spelled out. | B1: 12 points cost 1,601 output tokens (133 per point). Generation time is nearly all of a call's time. |
| F7 | **The 120 s budget per figure skipped panels.** A slow model read the first panels and left the rest. | Gemma 31B: 2 of 9 panels of B5, 2 of 4 of C1. |
| F8 | **The model could not say "this is not a chart".** The prompt begins "You read one chart panel". | Figures without data cost up to 667 s (the ECG traces) and produced invented series. |
| F9 | **Gemma sees every image at one low level of detail.** Through this Ollama (0.32.14) an image costs at most 258 to 268 tokens, whatever its size. | `probe_image_tokens.py`: 224² 51, 448² 83, 672² 198, 896² 258, and 258 to 268 from there to 6,400 x 4,944. Qwen 3.8 scales (4,034 tokens at 3,200 x 2,472). |
| F10 | **A point placed inside a bar stayed inside it.** The engine looked for the bar's edge within 4 % of the axis around the pointed position. | C1 in round 1: bars read 0.04 to 0.24 low. |
| F11 | **OCR misreads one tick label in a few figures**, and one wrong label broke the axis fit. | "300" read as "30" (B1), "0.8" as "80" (B3). |
| F12 | **Granite-Vision was not on equal footing.** It got the bundle's 1.5x crops; the Ollama models got 220 dpi renders. | B3 was 352 x 237 px for Granite and 717 x 482 for the others. Not rerun: round 2 covers three Gemma models by decision. |

F9 was followed up at the maintainer's request. Gemma 4 has image budgets
of 70 to 1,120 tokens. Ollama 0.32.14 ignores the request options
`image_max_tokens` and `max_soft_tokens` (tested: 284 prompt tokens either
way); the pull request that would have added the option was closed, and
its maintainers say that from 0.34.1 the budget is chosen from the image
size. Upgrading Ollama is the maintainer's decision and was not done. What
works on any version is to send smaller pieces: each crop gets the full
budget.

## 3. What was changed in the engine

All in `docling/engines/figure_data/`.

| # | Change | Answers |
|---|---|---|
| C1 | OCR (RapidOCR) on the work image, merged with the PDF words; an OCR line that covers PDF words is dropped; "words" without a letter or digit are dropped. | F3, F4 |
| C2 | Panels found by their tick labels: a run of three or more numbers, aligned and linear or logarithmic in position, is an axis; two or more charts are separated by cutting along the free band between them. Runs before the gutter method. | F1 |
| C3 | One overview call per figure: what it is, whether it holds data, how many charts. No data: not read, with the reason. Several charts that the code cannot separate: not read, with the reason. Two-label axes are accepted only when they give exactly the number of charts the model sees. | F2, F8 |
| C4 | The grounded prompt states the conventions per chart kind (bar end, stacked segment, box median and whiskers, interval ends, curve with a printed statistic, line without x ticks) and that a non-chart gets no points. | F2, F8 |
| C5 | Compact reply: `start_pos`, `lo_pos`, `hi_pos`, `err_lo`, `err_hi`, `label` are left out when they do not apply. | F6 |
| C6 | Replies are streamed. A call is cut at 120 s or when it repeats itself, and the complete points of a cut reply are kept. | F5 |
| C7 | The budget per figure is 600 s and only stops new calls. | F7 |
| C8 | A point on a bar's fill is followed outwards to where the fill ends. | F10 |
| C9 | Axis fit forgives one misread label among four or more. | F11 |
| C10 | Where no pixel edge backs a pointed position and the model's own reading differs from it by more than 5 % of the axis, the reading is kept and the panel says so. One point per (category or x, series). | found in step 4 |
| C11 | `timing.json` keeps the engine's notes per figure, so the next round can read causes without rerunning. | step 1 |

## 4. Iterations on the fast model

Gemma 4 26B-A4B (4-bit QAT), all 15 figures, about five minutes a pass.
"Named" and "names ignored" are values within 5 % of the axis range by
`compare_runs.py`; the second pairs values without their names and is an
upper bound.

| Pass | Named | Names ignored | Seconds | What happened |
|---|---|---|---|---|
| Round 1 | 55 | 55 | 535 | |
| v1 | 15 | | 367 | My reply format was wrong in three ways. Category was optional and the model left it out everywhere. I had renamed the interval positions to `lo` / `hi` and the model put axis values in them. One panel repeated a point 252 times until the 120 s cut. |
| v2 | 63 | 165 | 278 | Category required again, `_pos` names back, loop stop added. Series was still optional and left out on the grouped bar chart (B1: 12 right numbers without their legend entry). Box-plot medians measured from pointed positions were worse than in round 1. |
| v3 | 85 | 188 | 343 | Series and x required, C9 and C10 added, a tick label belongs to one axis only (C4 now splits in two). |

What v1 and v2 taught, beyond the fixes:

- **A model leaves out any field it is allowed to leave out.** Optional
  fields save tokens only for fields that are rare and whose absence is
  harmless. Category, series and x are not that.
- **Field names are part of the prompt.** `lo` reads as a value, `lo_pos`
  as a position.
- **Gemma reads a value against the axis better than it points at the
  mark.** On the box plots the pointed positions gave 13 of 30 medians
  within 5 %, the model's own readings (round 1, where no axis was
  calibrated) 19, and the cross-check of C10 23.

The engine was frozen at v3. More tuning on the same 15 figures would be
fitting the bench.

## 5. The two axes, separated

Same model, the v2 engine, with and without the new splitter.

| | Named | Names ignored | Seconds |
|---|---|---|---|
| Round 1 | 55 | 55 | 535 |
| Prompt, context and reply format only (old splitter) | 49 | 61 | 302 |
| Plus the splitter | 63 | 165 | 278 |

The prompt-and-context axis halves the time and fixes single-chart
figures (the interval plot, the bar panels). The split is what brings the
multi-panel figures in.

Repeated with the frozen v3 engine (`ablation/no-split/`): 69 named, 69
names ignored and 20 of 33 panels in 250 s without the splitter; 85, 188
and 33 of 33 in 343 s with it.

## 6. Tried and dropped

- **Panel boxes from the model.** Gemma counts the charts of a figure well
  and places them badly: equal thirds for B2, a 2 x 2 grid for the 3 + 2
  layout of B3, three stacked boxes for three pies side by side. Kept: the
  count. Dropped: the boxes.
- **A larger image for Gemma.** No effect on this Ollama (F9).
- **Trusting the pointed position wherever an axis is calibrated.** Worse
  than the model's reading on thin marks (step 4).

## 7. The blind Sonnet run

Run in parallel with step 2, before any engine change. Prompt, isolation
and tool log: [`sonnet/`](sonnet).

Its judge noted that the values on unlabelled marks were closer to the
truth than a reading by eye should be (about 0.2 % of the axis). The tool
log ruled out the truth files. To rule out memory of the published papers,
two charts were drawn from random numbers and read by a fresh agent with
Read and Write only: all 27 values within 0.3 % of the axis. Recorded in
`sonnet/AUDIT.md`.

## 8. The second wave, and what it showed about the cut

Three models, frozen engine, 56 GPU-minutes. Results in the README. One
thing the wave showed that the fast model could not: the 120 s cut per
call (C6) is sized for a model that writes about 50 tokens a second.
Gemma 31B at 8 bits writes about six. Its reply on the printed-count bar
chart was cut after 7 of 12 bars, so it lost a figure it had right in
round 1, where a call could run for up to 600 s.

Checked by rerunning the 31B on B1 and B2 with a 300 s cut
(`ablation/longer-cut/`): B1 12 of 12 in 184 s; B2 19 points in 511 s
(15 in 402 s with the 120 s cut). The cut should follow the model's speed,
or the model should not be offered for this step.

## 9. Open after this round

- Dense stacked bars (C3: 264 segments in three panels) stay out of reach
  at about 270 image tokens per panel. Cutting a panel into bands of rows
  is the next step there.
- Thin marks (medians, interval centres, line points) have no pixel
  snapping yet; bars do.
- The splitter needs tick labels. Pies and charts without numeric ticks
  fall back to the gutter method.
- A chart with a second y axis on the right would be cut in two.
- Values far outside the calibrated axis are flagged and still returned;
  OCR often misses the lone "0" tick, which makes that flag noisy.
- Vector charts: series named by fill colour, tick labels cut short (C4).
- The step as a standalone part of the conversion:
  `.claude/reference/figure-data/STANDALONE-STEP.md`.
