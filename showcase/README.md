# Showcase: one paper, three conversion configs, and the figure-to-data step

Same input, three `amir-batch` configurations, full output committed for each;
then the figure-to-data step on the default bundle with each of its two
recommended configs. Pick the folder that matches your hardware and open its
`preview.embedded.html`.

**Input:** [`Public-test-manuscript.pdf`](Public-test-manuscript.pdf):
*Vision-Language and Large Language Model Performance in Gastroenterology*
(arXiv preprint, 68 pages, 15 figures, 17 tables), Safavi-Naini et al.,
[arXiv:2409.00084](https://arxiv.org/abs/2409.00084); published in *npj Digital
Medicine* 8, 797 (2025), [doi:10.1038/s41746-025-02174-0](https://doi.org/10.1038/s41746-025-02174-0).

**License:** the paper and all output folders are **CC BY-NC-ND 4.0**
(© The Author(s)), not the repository's MIT license; see [`LICENSE`](LICENSE).

## ⚡ Which one should I look at?

| Folder | Command | Figures | Tables | GPU | Time* |
|---|---|---|---|---|---|
| [`fast/`](fast/Public-test-manuscript/) | `amir-batch paper.pdf --picture-description off --no-granite-vision-tables` | caption + figure type | TableFormer | not required (peak 1.6 GiB) | **55 s** |
| [`figures-vlm/`](figures-vlm/Public-test-manuscript/) | `amir-batch paper.pdf --no-granite-vision-tables` | + VLM description | TableFormer | ≥ 16 GB (peak 11.5 GiB) | **3.6 min** |
| [`default/`](default/Public-test-manuscript/) | `amir-batch paper.pdf` | + VLM description | each table by the model that has its text | ≥ 24 GB (peak 18.8 GiB) | **5.2 min** |
| [`figure-to-data/cloud/`](figure-to-data/cloud/Public-test-manuscript/) | `default/` + `amir-figdata step <bundle> --config configs/figure-to-data/recommended-cloud.toml` | + the numbers behind the charts, read by Claude Sonnet 5.5 | as `default/` | as `default/` | + **5.0 min**, 0.69 USD |
| [`figure-to-data/local/`](figure-to-data/local/Public-test-manuscript/) | `default/` + `amir-figdata step <bundle> --config configs/figure-to-data/recommended-local.toml` | + the numbers behind the charts, read by Gemma 4 26B in Ollama | as `default/` | as `default/` plus Ollama | + **52 min** |

\*The runs that produced these folders: NVIDIA GB10 (DGX Spark), release
`extrct_docling-v2.131.0-r7` (Docling v2.131.0), BiomedCLIP figure typing on,
with a conversion of another set running on the same GPU, so the times are
upper bounds. Time = the `amir-batch` duration (conversion + figure typing +
all outputs) as `run.json` records it, or the duration of the step. The peaks
are the GPU memory of the conversion process as measured with release r3,
nothing else on the GPU.

The conversion calls no external API: it runs locally. Its only VLM is
[Granite-Vision 4.1-4B](https://huggingface.co/ibm-granite/granite-vision-4.1-4b)
(HF `transformers`; vLLM is used instead when installed). The figure-to-data
step with the cloud config sends the chart images to OpenRouter.

## 🔍 What actually changes between configs

**Same in all three conversions:** 68 pages · 15 figures · 17 tables · 0
errors · 1,919 `document.json` items, same `self_ref` IDs, same viewer, same
figure types. Chunks: 128 (`fast`), 139 (`figures-vlm`), 138 (`default`): VLM
descriptions add text to figure chunks.

**Figures:** `fast` gives you the printed caption and a figure type from
BiomedCLIP (`figures.jsonl[*].figure_type`: `bar_chart`, `flow_diagram`,
`heatmap`, ... plus medical types like `ct` or `ecg`). The VLM configs add a
paragraph in `figures.jsonl[*].vlm_caption`. For Figure 4:

> *fast:* `Figure 4. LLM Performance on Text-Only Gastroenterology Multiple-choice Questions.` · `bar_chart` (confidence 1.00)
>
> *VLM:* "The chart is a horizontal bar graph titled 'All 2022 ACG questions (N = 300)' and displays the performance of various language models... The bars are segmented into different colors: green for correct answers, red for incorrect answers..."

⚠️ VLM descriptions read well but can misstate numbers. The same paragraph
calls GPT-4's 73.7% "near-perfect". Use them for search and context, and
check figures themselves before citing a value.

Figure types are right for 13 of 15 figures here (counting `forest_plot` for
Figure 3, a mix of bar charts and dot plots). The two misses are line charts:
Figure 6 → `kaplan_meier` (confidence 0.49) and Figure 7 → `box_plot`
(0.66). Low confidence is the hint to double-check. The type is kept out of
the markdown and chunk text on purpose; join on `self_ref` to
`figures.jsonl` when you need it.

**Tables:** since r7 a table whose box holds the PDF's text is made by
TableFormer in every config, which fills its cells from that text; `default`
gives Granite-Vision the tables the PDF has no text for. Here that is one:
table 15, a heatmap of a confusion matrix printed as an image. The other 16
grids are the same in all three folders. `tables.jsonl[*].structure_model`
says which model made each one.

| Table | Truth | TableFormer (all three) | Granite-Vision (`default`, r3 to r6) |
|---|---|---|---|
| 3 (wide, 11 cols) | 8 × 11 | ✅ 8 × 11 | ❌ 14 × 10 |
| 14 (temperature) | 8 × 3 | ❌ 7 × 3 | ✅ 8 × 3 |
| 15 (heatmap of a confusion matrix, an image) | ~10 × 8 | ❌ 11 × 8 (`fast`, `figures-vlm`) | ❌ 12 × 8 (`default`, also r7) |
| 17 (sparse, many empty cols) | ~9 cols | ❌ | ❌ |

Why TableFormer for tables with text: Granite-Vision retypes every cell from
the image. On 65 trial papers and supplements it left printed rows out and
misread digits in tables the self-check passed (177 for 172, 118/1379 for
1178/1379); on single pages of those papers 68 of 80 tables the check flagged
held 0.95 of their printed words with the routing, none without
(`.claude/reference/quality/2026-11-20-r5-bundles-tables-and-text.md`). In r6
three tables of `default/` here had Granite-Vision cells holding 0.90 to
0.94 of their words; in r7 none is under 0.95.

## 📈 The figure-to-data step

`figure-to-data/cloud/` and `figure-to-data/local/` are `default/` with the
step run on it: for every chart, the values it shows, written at the figure
in the HTML, the markdown, the chunks, `document.json` and the viewer (a
`data` tag on the figure), each with the note that these are a model's
readings, not the authors' numbers. The full reading of a figure is in
`figure-to-data/<figure>/figure-to-data.md`, with what the model was given.

| | Chart candidates | Read | No data | Not read | Values | Time | Cost |
|---|---|---|---|---|---|---|---|
| cloud: Claude Sonnet 5.5 through OpenRouter, effort medium | 12 | 9 | 1 | 2 | 517 | 5.0 min | 0.69 USD |
| local: Gemma 4 26B in Ollama | 12 | 11 | 0 | 1 | 1,195 | 52 min | none |

Measured on this paper against a hand-made truth of its six main figures
(573 values, the chart-to-data mini bench, `docs/mini-bench/chart-to-data/`,
round 5 and a check run of 2026-11-20): the cloud config returned 258 of
them within 5 % of the axis at effort medium (378 at high, which costs half
as much again), the local one 148 (it returns more values, as here, and far fewer of them are
right); of the values the cloud model returned at
medium, 96 % were right. Unlabelled values of dense charts are what medium
leaves out. Both configs are in
[`../configs/figure-to-data/`](../configs/figure-to-data/README.md).

## 📦 Inside each folder

```
Public-test-manuscript/
├── preview.embedded.html   👀 viewer, one file (download → open in a browser)
├── preview.html            👀 same viewer, needs images/ next to it
├── *.md / *.embedded.md    📝 markdown (linked / inlined images)
├── *.html                  📄 standalone manuscript HTML, keeps everything Docling extracted
├── chunks.jsonl            🤖 text chunks with headings, pages, self_refs
├── tables.jsonl            🤖 one row per table, with the model that made it
├── figures.jsonl           🤖 one row per figure: figure_type (+ vlm_caption, + chart_data)
├── nodes.jsonl             🤖 every node with bbox
├── document.json           🤖 full DoclingDocument
├── structure.json          🤖 sections, roles, numbered tables and figures
├── run.json                🧾 engine release + commit, exact options, models, package versions, timing
├── check.json              ✅ self-check of the bundle (see below)
├── figure-to-data/         📈 figure-to-data folders only: one folder per chart, the run records
└── images/                 🖼️ page renders + crops
```

GitHub shows `.html` as source: download the file (or clone) and open it locally.

`check.json` is the bundle's self-check, and every folder passes (`ok: true`,
no issues): every one of the 1,919 `document.json` items is tagged once in
the HTML, PDF text-layer recall is 0.997 for the document and at least 0.948
on each page with enough text to check (lowest: page 30), the markdown keeps
100 % of the text and the chunks 99.9 %, no ligature splits, no empty
chunks, no degenerate table, no table whose cells miss printed words.

## 🧾 Versions

All folders were regenerated on 2026-11-20 from release
`extrct_docling-v2.131.0-r7` (Docling v2.131.0, with BiomedCLIP figure
typing), on a clean checkout of the tag (`git_dirty: false`).

Each `run.json` has the engine release, the git commit and the exact package
versions. Reproduce any folder with the command in the table above plus
`-o <dir>`.
