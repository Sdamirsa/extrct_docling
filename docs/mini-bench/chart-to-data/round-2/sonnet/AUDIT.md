# Blind Sonnet run: how it was kept blind, and what it did

The question was whether a mid-tier cloud model, given nothing but the
images, reads these figures better than the local models. The answer only
counts if the agent could not see the truth, the judges' notes or another
model's output. Three layers:

1. **Nothing to find by name.** The agent was given one folder outside the
   repository. The figures in it were renamed `A1.png` ... `C5.png`; no
   paper name, bundle name or path into the bench appears in the prompt.
2. **The answers were unreadable while it ran.** For the length of the run
   the folders that hold reference values had all permissions removed
   (`chmod 000`): `truth/` and `judge/` of this bench, the older truth files
   under `tests/data/figure_data/truth/`, and the scratch folders of the
   round-1 truth agents and of the report page. They were restored (to
   `775`) after the agent had reported. The run folders of the other models
   stayed readable; they hold predictions, not truth, and the audit covers
   them.
3. **Every tool call was checked afterwards.** The agent's transcript was
   parsed and each call's file path or command compared with the allowed
   folder. A `chmod` to undo layer 2 would have shown up here.

Layer 2 is not a sandbox: the agent ran as the same user and could have
changed the permissions back. That is why layer 3 exists.

## The tool log

35 tool-call records (the transcript holds each read twice):

| tool | target | count |
|---|---|---|
| Read | `<blind>/figures/A1.png` ... `C5.png` | 15 figures, each once |
| Write | `<blind>/work/sizes.py` | 1 |
| Bash | `uv run --no-sync python <blind>/work/sizes.py` | 1 |
| Write | `<blind>/work/gen.py` | 1 |
| Bash | appends a few lines to `<blind>/work/gen.py` and runs it | 1 |

No call names a path outside `<blind>`. `sizes.py` prints the pixel size of
the 15 images; `gen.py` holds the answers as Python literals and writes the
15 JSON files. Neither opens anything else.

## What the run was

| | |
|---|---|
| Model | `claude-sonnet-5-5`, one sub-agent, one session |
| Wall time | 134 s for all 15 figures |
| Tokens | 89,267 (the agent's own count, all turns) |
| Tool uses | 20 |
| Method | by eye: it looked at each image once and wrote the values; it did not crop, enlarge or measure pixels (every non-printed value is marked `vlm`) |

Its answers as written are in [`answers/`](answers); converted to the
bench's figure-data JSON (panel boxes scaled from the work image to the
bundle crop, nothing else changed) they are under
[`../runs/claude-sonnet-5-5-blind/`](../runs/claude-sonnet-5-5-blind).

## Control: is that precision possible by eye?

The judge noted that the run's values on unlabelled marks agree with the
truth more finely than "by eye" suggests: a median of about 0.2 % of the
axis on the 90 line points of B2, and at most 0.14 % on the 12 bars of C1. The tool log rules
out the truth files, and the run got wrong exactly what cannot be seen
(box-plot medians that are not drawn, up to 10 % off). That left one other
explanation to exclude: that the model knows these published papers.

So two charts were drawn from random numbers that exist nowhere else, in
the style of C1 and B4 (`../../scripts/control_charts.py`), and a second
fresh `claude-sonnet-5-5` sub-agent read them with two tools only: Read on
the two images and Write for its two answer files. No script, no crop. Its
tool log holds exactly those four calls; it took 14 s.

| Control chart | Values | Error, share of the axis range |
|---|---|---|
| S1: four bar panels, three bars each, no printed values | 12 | 0.29 % on every bar (0.002 on a 0.2 to 0.9 axis) |
| S2: interval plot, five rows, centre and both ends | 15 | median 0.10 %, largest 0.27 % |

The precision is the model's reading of the image. Images, drawn values
and read values are in [`control/`](control); `control_score.py` prints
the table. (The agent itself said it would trust its third decimal to
about ±0.01 to ±0.02. It did ten times better than it thought.)

## What it is not

- Not a model inside our engine. It did the whole task in one look per
  figure, with its own layout reading; the local models answer one panel at
  a time inside the engine's pipeline.
- Not private. The figure images went to a cloud model, which the
  figure-to-data design rules out for conversion (papers can be unpublished
  or clinical). It is a reference point for what a look at the image can
  give, not a candidate for the pipeline.
- Not timed per figure. One session read all 15; only the total is known.
