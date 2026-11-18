# Blind Sonnet run: prompt

Given on 2026-11-17 to one fresh `claude-sonnet-5-5` sub-agent
(general-purpose agent, tools on). `<blind>` is a folder outside the
repository that held nothing but the 15 figure images under neutral names
(`A1.png` ... `C5.png`: the engine's work images, the same pixels the local
models are sent, before the engine's downscale to 1600 px) and two empty
folders, `work/` and `out/`. Nothing else is changed.

How the run was kept blind is in [AUDIT.md](AUDIT.md).

```text
You are a participant in a blind chart-to-data benchmark. For each of 15 figure images taken from scientific papers, extract the numeric data the figure shows, or say that it shows none. Your files will be scored against a reference that you must not see, so the result only means something if you work from the images alone.

## Hard rules (the run is void if any is broken; your complete tool log is audited afterwards)
- Your whole world is this folder: <blind>/
  - figures/A1.png ... A5.png, B1.png ... B5.png, C1.png ... C5.png: the 15 inputs (read-only).
  - work/: your scripts, crops and notes.
  - out/: your 15 answer files.
- Do not read, list, search or open anything outside that folder: not the repository you start in, not any other folder under /tmp or the home directory, not the web. No Glob/Grep/ls/find/cat outside the folder. Do not start sub-agents. Reference answers and other participants' outputs exist on this machine; do not look for them. If you believe you need something from outside, do without it and say so in your report.
- You may look at the images (Read tool on the PNGs and on crops you make) and you may use Python (PIL and numpy are installed) to crop, enlarge and measure pixels. Run Python only like this, from the directory you start in, without cd:
  `CUDA_VISIBLE_DEVICES= uv run --no-sync python <blind>/work/<script>.py`
  Write scripts with the Write tool into work/. Never use `uv sync` or plain `uv run`. Commands containing the string ".venv" are rejected by a hook. Do not use the GPU or Ollama.

## What to produce
One file per figure: out/<ID>.json (ID = A1 ... C5), valid JSON:

{
  "figure_id": "B1",
  "is_data_chart": true,
  "panels": [
    {
      "id": "a",                        // the printed panel letter, else "1", "2", ... in reading order
      "bbox_px": [x0, y0, x1, y1],      // the panel's box in pixels of the input image
      "title": "..." or null,
      "kind": "bar" | "stacked_bar" | "grouped_bar" | "line" | "scatter" | "box" | "forest" | "kaplan_meier" | "pie" | "heatmap" | "other",
      "orientation": "vertical" | "horizontal" | null,
      "axes": {"x": {"name": ..., "unit": ..., "scale": "linear" | "log" | "categorical", "range": [min, max] or null},
               "y": {same}},
      "series": [{"name": "...", "color": "..."}],
      "data": [
        {"category": "..." or null,    // categorical position (tick label), exactly as printed
         "x": number or null,          // numeric x position, for line/scatter charts
         "series": "..." or null,      // legend entry exactly as printed; null when the panel has a single unnamed series
         "value": number,              // in axis units
         "err_lo": number or null, "err_hi": number or null,
         "label_printed": "..." or null,   // the number as printed at the mark, when one is printed
         "source": "printed" | "raster" | "vlm",
         "confidence": 0.0-1.0}
      ],
      "notes": []
    }
  ],
  "uncertain": ["..."],                 // what you could not read reliably
  "method": "one sentence: how you got the values for this figure"
}

Conventions:
- One panel per separate chart in the figure. A figure can hold many panels; return every one.
- One data row per (category or x value, series).
- A figure with no plotted or printed data values (a diagram, a schematic, a workflow, raw signal traces, a screenshot) gets "is_data_chart": false and "panels": []; say what it is in uncertain[0]. Do not force data out of it.
- `source`: "printed" when the value is a number printed in the figure (copy it exactly into label_printed too); "raster" when you measured the mark's pixel position and converted it with an axis you calibrated on tick labels; "vlm" when you estimated it by eye. Be honest about which; it is analysed separately.
- Intervals (error bars, confidence intervals, forest plots): the centre in `value`, the two ends in err_lo / err_hi as absolute axis values, not deltas.
- Box plots: `value` is the median, err_lo / err_hi the whisker ends; put quartiles and outliers in the panel notes.
- Stacked bars: one row per segment, value = that segment's own share (not the cumulative edge).
- Pies: one row per wedge, value = its percentage, no series.
- A curve with a summary statistic printed for it (for example an AUC in the legend): record the printed statistic; you need not trace the curve.
- A line chart with no printed x ticks: x = the point's ordinal position 1, 2, 3, ...
- Names exactly as printed (line breaks as spaces). Never invent a value; leave it out and list it under `uncertain`.
- Where precision matters, measure rather than guess: calibrate each numeric axis on at least three tick labels and check the fit on a gridline or a printed number.

Check before you finish that all 15 files exist and parse as JSON.

## Report back (under 300 words)
A table: figure id, data chart or not, panels, number of values, how many printed / raster / vlm. Then one line on anything you could not read, and one line confirming you touched nothing outside the folder (or saying exactly what you touched).
```
