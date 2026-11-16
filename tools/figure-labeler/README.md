# Figure labelling kit

This folder holds chart figures cut out of research papers. You read the
numbers off each chart and save them as one JSON file per figure. Those files
are the ground truth for the figure-to-data engine (schema
`extrct.figure-data/1`, in `schema.json`).

Everything runs offline. Nothing is uploaded and nothing needs installing.

## Open

Double-click `index.html` (Chrome, Edge or Firefox; a laptop screen of 1280 px
or wider). Keep the folder together: the page loads `manifest.js` and the
images in `figures/` from beside it.

## Label (about 5–20 minutes per figure)

1. Pick a figure on the left. The timer runs while you work (it pauses after
   2 minutes without input) and fills `labeler.time_minutes`.
2. Press **P** and drag a box around each sub-panel (a, b, c… in reading
   order). For a single chart click **+ whole image**.
3. On the right set the panel **kind**, **orientation**, **title** and each
   axis: name, unit, scale (linear / log / categorical), range and ticks.
4. **Calibrate** the value axis: click *pick ref 1*, then click a tick label on
   the image (its centre and text are taken; check the value), then *pick
   ref 2* on a tick far from the first. For a categorical axis fill *ticks*
   first, then pick the first and the last category.
5. Add the legend entries under **Series** (name and colour).
6. Press **A** and click each mark (bar end, point, line vertex). A row
   appears with the value in axis units and, when the other axis is
   calibrated, its category or x. **Shift**+click sets `err_hi`, **Alt**+click
   `err_lo` of the selected row (or choose what clicks fill in the toolbar,
   keys 1/2/3). Once both axes are calibrated, a dot is drawn where each row
   lands (with its error bar): the dots must sit on the marks, which also
   checks typed or pasted values.
7. Printed numbers win. Focus a `printed` cell and click the printed number on
   the image: the text is copied, the value is parsed from it and confidence
   becomes 1. Labels like `1.23 (0.98–1.55)` also fill `err_lo`/`err_hi`.
8. Tick **done** (or press D) when the figure is finished.

The word boxes on the image (toggle with **W**) are the words Docling found in
the figure (blue) and the PDF text layer (green). Clicking a word copies it
into the form field that has focus, which saves typing titles, axis names,
series names and tick lists (clicks append in the *ticks* field).

You can also paste rows from a spreadsheet in **Paste CSV** (header row
required). Long format uses the grid's column names
(`category,series,value,err_lo,err_hi,…`); wide format is
`category,<series 1>,<series 2>…` with one value per cell.

## Rules (from the schema contract)

- One data row per (category or x, series). `value` is the plotted quantity
  **in axis units** (a bar at 42 % is `42`, not `0.42`, when the axis is in %).
- `err_lo` / `err_hi` are **absolute positions** (the ends of the error bar or
  CI), not deltas.
- An unknown or unreadable number is **empty (null). Never guess.**
- `confidence` is how sure you are of the value: 1.0 when the number is
  printed, about 0.8 when read carefully against gridlines, lower when the
  mark is tiny, overlapping or between distant ticks.
- `source` stays `human` for your own labels; `label_printed` holds the
  printed text verbatim when there is one.
- `bbox_px` is in pixels of `figures/<id>.png` (the bundle crop). The hi-res
  display image is scaled to the same coordinates, so you never convert.
- Kinds: `pie` has no axes (tick *no axes*), value = slice value or %;
  `forest`: value = point estimate, errors = CI; `box`: value = median, errors
  = whiskers, quartiles in the panel notes; `heatmap`: category = row label,
  x = column label; `kaplan_meier`: x = time, series = arm, value = survival,
  only at labelled time points; `stacked_bar`: value is the segment's own
  size (the point tool subtracts the segments already entered below it).
- Put doubts in **Uncertain** (figure level) or panel **notes**.

## Export and send back

- **Export figure** (Ctrl+S) downloads `<bundle>__pictures<N>.json`;
  **Export all** downloads one file per labelled figure (allow multiple
  downloads if the browser asks).
- Move the files into this folder's `labels/` directory, zip the whole folder
  and send it back.
- Work also autosaves in the browser per figure, but only the exported files
  count. **Import…** loads exported files back (to continue or review).
- Export is refused while the figure has schema problems; the box at the
  bottom of the form lists them.

## For agents

The same folder works without the browser:

1. Read the manifest:
   `json.loads(Path("manifest.js").read_text().split("=", 1)[1].strip().rstrip(";"))`.
   Per figure it has `id`, `image` (crop), `image_hires` (PDF render, display
   only, same box), `width`/`height` (crop pixels), `bundle`, `self_ref`,
   `image_path`, `page`, `bbox` (`[l, t, r, b]` page points from the top-left,
   as in the label), `caption_text`,
   `figure_type`, `vlm_caption`, and words with `bbox_px` in crop pixels:
   `words_docling` (Docling text items inside the picture: text layer or OCR)
   and `words_pdf` (PDF text layer, empty for raster-only figures).
2. Look at `figures/<id>.png` (or the `@hi` render), write
   `labels/<id>.json` following `schema.json` with `labeler.kind = "agent"`
   and `source = "agent"`.
3. Check: `uv run --no-sync python tools/figure-labeler/validate.py <this folder>`
   (from the extrct_docling repo) prints valid/invalid files, panel and row
   counts, missing fields and unlabelled figures.

## Shortcuts

| Key | Action | Key | Action |
|---|---|---|---|
| V / P / A | select · draw panel · add point | [ / ] | previous / next figure |
| 1 / 2 / 3 | clicks fill value · err_lo · err_hi | W | toggle word boxes |
| F / 0 / + / - | fit · 1:1 · zoom (or wheel) | Space+drag | pan (or drag empty area in Select) |
| Del | delete selected panel | Esc | cancel pick / back to Select |
| Ctrl+S | export this figure | D | toggle done |
| Enter / Shift+Enter, ↑ ↓ | grid: next / previous row (Enter on last row adds one) | Ctrl+Enter · Ctrl+D · Ctrl+Delete | grid: insert · duplicate · delete row |

## Making a pack (maintainers)

```
uv run --no-sync python tools/figure-labeler/pack.py <bundle_dir>... --out <folder> \
    [--refs "#/pictures/4,HeartAgent#/pictures/1"] [--types bar_chart,line_chart] \
    [--pdf-dir samples/aca-papers] [--hires-scale 3]
```

Without `--refs` it packs every non-noise figure whose BiomedCLIP
`figure_type` is chart-like (bar, line, scatter, box, forest, Kaplan–Meier,
ROC, heatmap, pie). The PDF is found through `--pdf-dir/<bundle>.pdf` or the
bundle's `run.json`; without it there are no PDF words and no hi-res images.
`labels/` is never overwritten.
