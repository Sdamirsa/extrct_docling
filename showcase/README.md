# Showcase: one paper, three configs

Same input, three `amir-batch` configurations, full output committed for each.
Pick the folder that matches your hardware and open its `preview.embedded.html`.

**Input:** [`Public-test-manuscript.pdf`](Public-test-manuscript.pdf):
*Vision-Language and Large Language Model Performance in Gastroenterology*
(arXiv preprint, 68 pages, 15 figures, 17 tables), Safavi-Naini et al.,
[arXiv:2409.00084](https://arxiv.org/abs/2409.00084); published in *npj Digital
Medicine* 8, 797 (2025), [doi:10.1038/s41746-025-02174-0](https://doi.org/10.1038/s41746-025-02174-0).

**License:** the paper and all three output folders are **CC BY-NC-ND 4.0**
(© The Author(s)), not the repository's MIT license; see [`LICENSE`](LICENSE).

## ⚡ Which one should I look at?

| Folder | Command | Figures | Tables | GPU | Time* |
|---|---|---|---|---|---|
| [`fast/`](fast/Public-test-manuscript/) | `amir-batch paper.pdf --picture-description off --no-granite-vision-tables` | caption + figure type | TableFormer | not required (peak 1.6 GiB) | **65 s** |
| [`figures-vlm/`](figures-vlm/Public-test-manuscript/) | `amir-batch paper.pdf --no-granite-vision-tables` | + VLM description | TableFormer | ≥ 16 GB (peak 11.5 GiB) | **2.4 min** |
| [`default/`](default/Public-test-manuscript/) | `amir-batch paper.pdf` | + VLM description | Granite-Vision VLM | ≥ 24 GB (peak 18.8 GiB) | **11.8 min** |

\*The runs that produced these folders: NVIDIA GB10 (DGX Spark), Docling
v2.131.0, nothing else on the GPU, BiomedCLIP figure typing on. Time = the
`amir-batch` duration (conversion + figure typing + all outputs); peak = GPU
memory of the conversion process.

No config calls an external LLM API: everything runs locally. The only VLM is
[Granite-Vision 4.1-4B](https://huggingface.co/ibm-granite/granite-vision-4.1-4b)
(HF `transformers`; vLLM is used instead when installed).

## 🔍 What actually changes between configs

**Same in all three:** 68 pages · 15 figures · 17 tables · 0 errors, same
`self_ref` IDs, same viewer, same figure types. Chunks: 126 (`fast`), 132
(`figures-vlm`), 133 (`default`): VLM descriptions add text to figure chunks.

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

**Tables:** TableFormer and Granite-Vision agree on 15 of 17 tables.

| Table | Truth | TableFormer | Granite-Vision |
|---|---|---|---|
| 3 (wide, 11 cols) | 8 × 11 | ✅ 8 × 11 | ❌ 14 × 10 (was ✅ before the Docling v2.131.0 sync) |
| 14 (temperature) | 8 × 3 | ❌ 7 × 3 | ✅ 8 × 3 |
| 17 (sparse, many empty cols) | ~9 cols | ❌ | ❌ |

Takeaway: `figures-vlm` is ~5× faster than `default`, and on this paper each
table model wins one table (TableFormer table 3, Granite-Vision table 14).
`default` stays the suggested config (see the main README); try both on your
own documents.

## 📦 Inside each folder

```
Public-test-manuscript/
├── preview.embedded.html   👀 viewer, one file (download → open in a browser)
├── preview.html            👀 same viewer, needs images/ next to it
├── *.md / *.embedded.md    📝 markdown (linked / inlined images)
├── chunks.jsonl            🤖 text chunks with headings, pages, self_refs
├── tables.jsonl            🤖 one row per table
├── figures.jsonl           🤖 one row per figure: figure_type (+ vlm_caption)
├── nodes.jsonl             🤖 every node with bbox
├── document.json           🤖 full DoclingDocument
├── run.json                🧾 exact options, models, package versions, timing
└── images/                 🖼️ page renders + crops
```

GitHub shows `.html` as source: download the file (or clone) and open it locally.

## 🧾 Versions

All three folders were regenerated on 2026-10-02 from the same code (Docling
v2.131.0, docling-core 2.98.0, with BiomedCLIP figure typing).

Each `run.json` has the exact package versions. Reproduce any folder with the
command in the table above plus `-o <dir>`.
