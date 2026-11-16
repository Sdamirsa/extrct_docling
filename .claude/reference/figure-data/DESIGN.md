<!-- last-reviewed: 2026-11-09 -->
# Figure-to-data: design, wiring and configs (v1)

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
        └─ panel_split ──► [Panel(bbox_px, letter)]           (letters + gutters; VLM boxes as fallback)
              └─ evidence ──► words with coords (text layer | OCR), ticks → axis maps, vector marks | raster marks
                    └─ read ──► ChartData draft      (vector reader | grounded VLM via Ollama | simple VLM)
                          └─ verify ──► ChartData + per-value source/confidence + issues
                                └─ publish ──► figures.jsonl[chart_data], meta.amir__chart_data,
                                               meta.tabular_chart (Docling TableData), md marked table,
                                               HTML manifest, preview overlay, check.json counts
```

Module layout (all under `docling/engines/figure_data/`):
`schema.py` (pydantic: ChartData, Panel, Axis, Series, Value, FigureJob),
`eligibility.py`, `panels.py`, `evidence.py` (pdfium words/paths, OCR words
from picture children, axis calibration), `readers/vector.py`,
`readers/vlm.py` (Ollama client + prompts + JSON schema), `readers/raster.py`
(bar/segment pixel measurement), `verify.py`, `publish.py`, `scoring.py`
(truth vs prediction), `cli.py` (`amir-figdata`: run on bundles, score, time).
Engine hook: `PdfEngine(figure_data="off|simple|measured", figure_data_model=...)`;
CLI `amir-batch --figure-data ... --figure-data-model ...`. Standalone runs on
existing bundles (no reconversion): `amir-figdata run <bundle...> --mode measured`.

## Config (pydantic, recorded in run.json engine_config.figure_data)

```python
class FigureDataOptions(BaseModel):
    mode: Literal["off", "simple", "measured"] = "off"
    engine: Literal["ollama"] = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "gemma4:26b-a4b-it-q8_0"
    escalation_model: str | None = "gemma4:31b-it-q8_0"   # local; None disables
    keep_alive: str = "10m"
    samples: int = 1                     # N-sample agreement when > 1
    panel_split: Literal["auto", "off", "vlm"] = "auto"
    crop_dpi: int = 220                  # native bitmap when available
    min_confidence_for_markdown: float = 0.7
    eligible_types: frozenset[str] = {"bar_chart","line_chart","scatter_plot","box_plot",
                                      "forest_plot","kaplan_meier","roc_curve","heatmap","pie_chart"}
    time_budget_s_per_figure: float = 120
```

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
