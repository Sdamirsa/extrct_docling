# figure-to-data

The numbers behind this paper's chart figures, read from the figure images
by a model. Nothing in this folder comes from the paper's text or tables,
and none of it was checked by a person.

- `prepare.json`: every picture of the paper: prepared for reading, or why not.
- `<pictures_N>/figure.png`: the figure, captured from the PDF at high resolution.
- `<pictures_N>/figure.txt`: what the reader was told beside the image.
- `<pictures_N>/evidence.json`: the same evidence for programs.
- `<pictures_N>/figure-to-data.md`: the reading, for people and agents.
- `<pictures_N>/figure-to-data.json`: the same reading, `extrct.figure-data/1`.
- `<pictures_N>/result.json`: how that reading was obtained (calls, time, checks).
- `runs/<run id>.json`: each run of the step: method, model,
  options, prompts, and what came of every figure.

A figure folder holds the reading of the latest run. Written by
`amir-figdata` (extrct_docling), step version 3.
