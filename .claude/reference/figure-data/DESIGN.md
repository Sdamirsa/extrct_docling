<!-- last-reviewed: 2026-11-18 -->
# Figure-to-data: the measured engine (design, wiring and configs)

Since 2026-11-18 this engine is the `ollama` method of the
figure-to-data step. The step itself (prepare, three reading methods,
embed, the folder, the agent) is described in `STANDALONE-STEP.md`; this
file covers what happens inside the local method. The maintainer lifted
"local models only" that day: a cloud call and an agent are methods beside
this one, chosen by the user.

Approved direction (maintainer, 2026-11-09): measurement-first pipeline
(proposal: https://claude.ai/code/artifact/74a18144-3313-4896-b3b1-8bb78054c6a9),
local models only, configurable down to a simple VLM table reader, validated on
50 self-made labelled figures. Minimal test first: 5 figures, Gemma 4, ≤ 1 GPU
hour.

## Decisions

| Topic | Decision |
|---|---|
| Grounded reader (first guess) | `gemma4:26b-a4b-it-q8_0` via Ollama (28 GB). Dense alternative `gemma4:31b-it-q8_0` (34 GB). |
| Models to compare (next session) | Gemma 4 26B-A4B (MoE) and 31B (dense); Qwen 3.6 35B-A3B (MoE, `qwen3.6:35b-a3b-q8_0`, 39 GB) and 27B (dense, `qwen3.6:27b-q8_0`, 30 GB). |
| Engine | Ollama HTTP API (`/api/chat`, images + `format` JSON schema, `keep_alive` for load/unload, `ollama ps` to inspect). vLLM later if throughput matters. |
| Escalation | **Local only.** The escalation step sends the figure crop plus the words/ticks read from it, i.e. paper content, which can be unpublished or clinical. No outside engine. Escalation model = the dense 31B at q8. |
| Modes | `off` · `simple` (one VLM call → table, like Docling's chart2csv) · `measured` (panels → evidence → grounded read → geometry → verify). Default after validation; `simple` stays available. |
| Baseline | Docling's Granite-Vision `chart2csv` stage, run through the same scorer. |
| Validation | 50 figures labelled by humans with the local HTML kit (`tools/figure-labeler/`); 5 figures labelled by agents now for the smoke test. |

## Wiring

```
PictureItem (after noise filter, BiomedCLIP type)
  └─ eligibility ──► FigureJob(crop at native resolution, page bbox, words-in-box, paths-in-box)
        └─ evidence ──► words with coords (text layer + OCR of the work image), ticks → axis maps, vector marks
              └─ panel_split ──► [Panel(bbox_px, letter)]     (tick-label axes first; else letters + gutters)
                    └─ overview ──► one VLM call: is it data at all, how many charts (gate + check on the split)
                    └─ read ──► ChartData draft      (vector reader | grounded VLM per chart via Ollama | simple VLM)
                          └─ verify ──► ChartData + per-value source/confidence + issues
                                └─ publish ──► figures.jsonl[chart_data], meta.amir__chart_data,
                                               meta.tabular_chart (Docling TableData), md marked table,
                                               HTML manifest, preview overlay, check.json counts
```

Module layout (all under `docling/engines/figure_data/`):
`schema.py` (pydantic: ChartData, Panel, Axis, Series, Value, FigureJob),
`eligibility.py`, `panels.py`, `evidence.py` (pdfium words/paths, RapidOCR
on the work image, axis calibration), `readers/vector.py`,
`readers/vlm.py` (Ollama client + prompts + JSON schema), `readers/raster.py`
(bar/segment pixel measurement), `verify.py`, `publish.py`, `scoring.py`
(truth vs prediction), `cli.py` (`amir-figdata`: run on bundles, score, time).
Entry point: `pipeline.read_figure(job, options, client)`, called by
`methods/ollama.py` on a prepared figure folder. The conversion engine has no
figure-data hook any more: `amir-batch --figure-data ollama` and
`amir-figdata step` run the step on the finished bundle (`step.py`).

## Config (pydantic, recorded with every run in figure-to-data/runs/)

The fields the local method reads (the step's own are in `schema.py`):

```python
class FigureDataOptions(BaseModel):
    method: Literal["ollama", "cloud", "agent"] = "ollama"
    mode: Literal["simple", "measured"] = "measured"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "gemma4:26b-a4b-it-qat"     # the bench's pick (round 2)
    keep_alive: str = "10m"
    samples: int = 1                     # N-sample agreement when > 1
    panel_split: Literal["auto", "off", "vlm"] = "auto"
    crop_dpi: int = 220                  # native bitmap when available
    min_confidence_for_markdown: float = 0.7
    eligible_types: frozenset[str] = {"bar_chart","line_chart","scatter_plot","box_plot",
                                      "forest_plot","kaplan_meier","roc_curve","heatmap","pie_chart"}
    time_budget_s_per_figure: float = 600   # no new call once a figure took this long
    time_budget_s_per_call: float = 120     # a call is cut here and keeps its complete points
```
`panel_split` also takes `gutters` (the splitter without the axes step, for comparison).

## Round 2 (2026-11-17): what the mini bench changed

Round 1 of `docs/mini-bench/chart-to-data/` showed every model failing the
same ways; most of it was the call path, not the model. The findings,
the changes and the numbers are in `docs/mini-bench/chart-to-data/round-2/`
(`LOG.md` in order, `README.md` for results). What holds from now on:

- **Words = text layer + OCR of the work image.** A bitmap chart keeps its
  tick labels in the pixels even when the box holds a few PDF words.
- **Charts are found by their tick labels** (a run of three aligned numbers,
  linear or log in position), then separated along the free band between
  them. Gutter width is not a usable signal: papers pack panels 4 px apart.
- **One overview call per figure**: not data → not read; several charts
  that the code cannot separate → not read, with the reason in `uncertain`.
  The model's count is trusted, its boxes are not.
- **One grounded call per chart, on its own crop.** Through Ollama 0.32
  Gemma 4 spends at most about 270 tokens on an image of any size; the
  crop is what gives it detail.
- **Reply format:** the fields a model may leave out are only those that
  are rare and harmless to lose (`start_pos`, `lo_pos`, `hi_pos`, `err_lo`,
  `err_hi`, `label`). It leaves out anything it is allowed to. Position
  fields carry `_pos` in their name or get filled with axis values.
- **Replies are streamed**, cut at the per-call budget or when they repeat
  themselves, and the complete points of a cut reply are kept.
- **Pixels beat pointing, reading beats pointing.** A bar end is followed
  to where the fill stops. Where nothing in the pixels backs a pointed
  position and the model's own reading differs by more than 5 % of the
  axis, the reading is kept.

Next: the step as its own part of the conversion, `STANDALONE-STEP.md`.

## Schema v1 (`extrct.figure-data/1`) — used by predictions AND ground truth

```json
{
  "schema": "extrct.figure-data/1",
  "figure": {"bundle": "AMIE-Mx", "self_ref": "#/pictures/5", "image_path": "images/picture_006.png",
             "page": 6, "bbox": [l, t, r, b]},
  "source_kind": "vector | raster | mixed | unknown",
  "panels": [{
    "id": "a",                              "bbox_px": [x0, y0, x1, y1],
    "title": "Top-3 DDx Accuracy on MIMIC (Llama-3.3-70B)",
    "kind": "bar | stacked_bar | grouped_bar | line | scatter | box | forest | kaplan_meier | pie | heatmap | other",
    "orientation": "vertical | horizontal | null",
    "axes": {"x": {"name": "Visit", "unit": null, "scale": "categorical", "range": null, "ticks": ["1","2","3"]},
             "y": {"name": "Accuracy", "unit": null, "scale": "linear", "range": [0.2, 0.8], "ticks": [0.2,0.4,0.6,0.8]}},
    "series": [{"name": "AMIE", "color": "red"}],
    "data": [{"category": "CoT", "x": null, "series": "AMIE", "value": 0.42,
              "err_lo": 0.37, "err_hi": 0.47, "label_printed": null,
              "source": "printed | vector | raster | vlm | human | agent", "confidence": 0.9}],
    "notes": ["legend overlays rows 21-23"]
  }],
  "labeler": {"kind": "human | agent | engine", "name": "…", "date": "2026-11-09", "time_minutes": 12},
  "uncertain": ["panel c values read by eye, ±1 unit"]
}
```

Rules: `bbox_px` in pixels of the bundle's crop (`image_path`); one `data`
row per (category/x, series); `value` is the plotted quantity in axis units;
`err_lo`/`err_hi` are absolute positions, not deltas; for `pie`, `value` is
the slice value or percentage and `axes` is null; for `forest`, `value` is the
point estimate with `err_lo`/`err_hi` the CI; for `heatmap`, rows are
(category = row label, x = column label, value); for `kaplan_meier`, rows are
(x = time, series = arm, value = survival) at the labelled time points only;
`box` uses `value` = median with `err_lo`/`err_hi` = whiskers and notes for
quartiles. Unknown numbers are `null`, never guessed. `confidence` for
humans/agents is how sure the labeler is (1.0 when the number is printed).

## Scoring (`scoring.py`)

Per figure: panel detection IoU ≥ 0.5 (precision/recall), per panel kind
match, series and category F1 (normalised strings, Levenshtein ≤ 0.2),
values matched by (category/x, series): axis-normalised error
|pred−true| / (axis range) with hits at ≤ 0.02 and ≤ 0.05, MAPE on printed
values, missing/extra counts. Totals per source and per model; wall time and
GPU memory per figure (from `ollama ps` and `/api/chat` durations).

## Minimal test (this session, ≤ 1 GPU hour)

Figures (`tests/data/figure_data/testset-5.json`): see that file. Steps:
agents label the 5 figures (clean-memory Fable sub-agents, one per figure) →
code `simple` + `measured` → run Gemma 4 26B-A4B q8 on the 5 → score → time
cost per figure and projected per paper (× chart-like figures per paper,
median 3 in the 14v1 batch) → write-up. Next session: 50 human labels, four
models, pick the default.
