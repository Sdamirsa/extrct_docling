# Brief for the truth of the split check

You are given figure images taken from scientific papers. For each one, say
which charts it holds and draw one box around each chart. Your boxes are
the reference that automatic splitters will be measured against, so they
have to be right and you work alone: nobody else's answer is available to
you, and none may be looked for.

## Rules of the job

- Use only the files in the folder you were given (`{folder}`): the images
  in `images/`, the script `draw_boxes.py`, and the files you write there.
  Open no other file on this machine, search for nothing, and start no
  other agent. In particular do not look for earlier results about these
  figures; there are some elsewhere, and reading them would spoil the
  check.
- The figure ids (`T01`, ...) say nothing about the figure. Judge each
  image by what is in it.

## What a chart is

- Every plot with its own axes is one chart, and every pie is one chart.
  This holds when the plots sit in a grid, share a legend, share an axis
  title, or stand together under one panel letter: six small plots under
  the letter "a" are six charts.
- One set of axes is one chart, however much is drawn in it. Bars drawn in
  groups or blocks along one axis line are one chart. A chart with a second
  y axis on the right is one chart.
- A heatmap or a confusion matrix is one chart, together with its colour
  bar.
- A forest plot is one chart: the plot together with its row labels and the
  columns of numbers printed beside it.
- A small plot drawn inside the plot area of another (an inset) belongs to
  the chart it sits in and is not counted.
- Not a chart: a diagram, a workflow, a photo, a screenshot, a raw signal
  trace (ECG, waveform), a table of text printed as an image. A figure may
  mix charts with such parts; box the charts only.

## What a box holds

Draw the box tight around everything that belongs to that one chart:

- the plot area, the tick labels and the axis titles of both axes;
- the chart's own title and its panel letter;
- the chart's own legend, and numbers or notes printed for it.

Leave out what belongs to several charts at once: a legend shared by the
charts, an axis title that runs along a whole row or column of charts, a
headline over the whole figure. Nothing of a neighbouring chart may be in
the box, and no label of the chart itself may be cut by its edge.

Boxes are `[x0, y0, x1, y1]` in whole numbers on a 0-1000 grid of the
image: x runs from the left edge (0) to the right edge (1000), y from the
top edge (0) to the bottom edge (1000), whatever the image's size in
pixels.

## How to work, figure by figure

1. Open the image `{folder}/images/<id>.png` and decide what the charts are.
2. Write `{folder}/<id>.json`:

   ```json
   {
     "id": "T01",
     "charts": [
       {"label": "a", "box": [12, 30, 495, 480]},
       {"label": "b", "box": [505, 30, 990, 480]}
     ],
     "not_chart": false,
     "note": ""
   }
   ```

   `label` is the chart's printed letter or title when it has one, else
   `1`, `2`, ... in reading order. List the charts in reading order (rows
   from the top, each row from the left). A figure without any chart gets
   `"charts": []` and `"not_chart": true`. Use `note` for a doubt about
   what counts as a chart in this figure.
3. Draw your boxes and look at them. From the repository root:

   ```
   uv run --no-sync python {folder}/draw_boxes.py <id>
   ```

   This writes `{folder}/check/<id>.png` (the figure with all boxes) and
   `{folder}/check/<id>-<n>.png` (box n enlarged, with some of the figure
   around it). Open them. A grid estimate from the image alone is often off
   by a few percent of the image, so expect to correct.
4. Correct the JSON and draw again until every box holds its whole chart
   and nothing else. Check the edges in the enlarged views: tick labels and
   axis titles inside, the neighbour's labels outside. For a figure with
   many charts, check every box, not a sample.

## When you are done

Reply with one line per figure: the id, the number of charts, and any
doubt you noted. Say plainly if a figure was hard to decide or if a box
could not be made clean (charts that overlap, a legend that sits between
two charts).
