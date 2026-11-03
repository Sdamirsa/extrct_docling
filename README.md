# extrct_docling · the Amir Engine 📌

> **A fork of [Docling](https://github.com/docling-project/docling) that turns one PDF into one folder an AI agent (or a tired human) can actually use.**
> Upstream Docling docs follow [further down](#docling-upstream).

## ⚡ TL;DR

```bash
git clone https://github.com/Sdamirsa/extrct_docling.git && cd extrct_docling
uv sync --frozen --no-group docs --extra standard --extra feat-ocr-rapidocr-onnx --extra models-vlm-inline   # install
uv run amir-batch my-paper.pdf -o out                                   # convert → out/my-paper/
```

Then open `out/my-paper/preview.embedded.html` in any browser (one file, works offline).
That's it. Everything below is optional reading.

### 💻 Platform notes (Linux · DGX Spark · Windows)

Same install command everywhere (`uv sync --frozen --no-group docs --extra standard --extra feat-ocr-rapidocr-onnx --extra models-vlm-inline`); only the PyTorch step differs. Needs [uv](https://docs.astral.sh/uv/) and Python 3.10+.

| Platform | Install | GPU |
|---|---|---|
| **Linux x86_64** + NVIDIA | install command only | CUDA torch comes from PyPI automatically |
| **DGX Spark / Jetson (Linux aarch64)** | install command only. Do **not** use `--all-extras` / `make setup` (no `onnxruntime-gpu` wheel for aarch64) | CUDA torch from PyPI; this is the tested machine |
| **Windows 10/11** + NVIDIA | install command, then<br>`uv pip install --reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu128`<br>and from then on run with **`uv run --no-sync amir-batch ...`** | PyPI torch on Windows is **CPU-only**. `--no-sync` stops uv from swapping the CUDA build back to the CPU one |
| macOS (Apple Silicon) | install command only | runs on MPS/CPU; the default VLM config is slow, prefer fast mode |

Check the GPU is visible: `uv run python -c "import torch; print(torch.cuda.is_available())"`.
Paths work with either slash style (`out\my-paper` on Windows is fine); all outputs are UTF-8 and use `/` in their internal links, so a bundle made on Linux opens on Windows and vice versa.

## 🖥️ Hardware for the suggested config

| Mode | Command | GPU | Speed (68-page paper) |
|---|---|---|---|
| **Suggested (default)** — VLM figure descriptions + VLM tables | `amir-batch paper.pdf` | **≥ 24 GB GPU** (measured peak **18.8 GiB**) | ~12 min |
| Middle — VLM figure descriptions, TableFormer tables | `amir-batch paper.pdf --no-granite-vision-tables` | **≥ 16 GB GPU** (measured peak 11.5 GiB) | ~2.4 min |
| Fast — no VLMs | `amir-batch paper.pdf --picture-description off --no-granite-vision-tables` | not required (peak 1.6 GiB when a GPU is present; CPU-only is slower, untimed) | ~1 min |

Measured on an NVIDIA GB10 (DGX Spark, 128 GB unified memory) with Docling v2.131.0, HF `transformers` backend, nothing else on the GPU, BiomedCLIP figure typing on (every mode; `--no-figure-types` to skip, ~15 ms per figure). Peak = GPU memory of the conversion process; the minimums leave ~4–5 GiB headroom but haven't been tested on discrete 24 GB / 16 GB cards. First run downloads the Granite-Vision 4.1-4B weights (~13 GB on disk here).

## 🧠 The suggested config (what `amir-batch` does by default)

| Stage | Model | Why |
|---|---|---|
| Layout + reading order | Docling **Heron** layout model | upstream default, fast |
| Tables | **Granite-Vision 4.1-4B** (VLM, same weights as figures) | better than TableFormer on messy clinical tables |
| Figure descriptions | **Granite-Vision 4.1-4B** (VLM) | one paragraph per figure → `figures.jsonl[*].vlm_caption` |
| Figure type | **BiomedCLIP** (zero-shot, PubMed-trained) | `ct`, `angiography`, `ecg`, `kaplan_meier`, `bar_chart`, ... → `figures.jsonl[*].figure_type` (83.5 % on a 97-figure medical sample vs 16.5 % for Docling's generic classifier) |
| Noise filter | Docling generic picture classifier + bbox-repeat heuristic | tags + strips logos / badges / QR codes / repeated banners ("noise"); its generic label is *not* a figure type |
| Chunking | Docling `HybridChunker`, MiniLM tokenizer, 512 tokens | ready for embeddings / RAG |

VLM runtime: HF `transformers` by default; if [vLLM](https://github.com/vllm-project/vllm) is installed it is picked up automatically (`picture_description_engine="vllm"` to force). No LLM API calls: everything runs locally. The outputs are shaped so *your* LLM can read them (chunks, tables, figures as JSONL).

## 📦 What you get per PDF

```
out/<pdf-name>/
├── <pdf-name>.html         📄 the manuscript as ONE readable HTML file, figures inlined; every block
│                              tagged with self_ref/page/bbox + a JSON manifest for agents; nothing
│                              Docling extracted is dropped (headers, logos, figure text are marked)
├── preview.embedded.html   👀 clickable viewer, ONE file, images inlined: share this
├── preview.html            👀 same viewer, links to images/ (small; keep the folder together)
├── <pdf-name>.md           📝 markdown, figures linked from images/
├── <pdf-name>.embedded.md  📝 markdown, figures inlined (one file)
├── chunks.jsonl            🤖 text chunks + headings + page numbers + self_refs
├── tables.jsonl            🤖 one row per table: caption, markdown, html, cells
├── figures.jsonl           🤖 one row per figure: caption, figure type, VLM description, noise flag
├── nodes.jsonl             🤖 every document node with bbox
├── document.json           🤖 full DoclingDocument (lossless)
├── run.json                🧾 engine release + git commit, models, options, timing, package versions
└── images/                 🖼️ page renders + figure/table crops
```

**Citable:** every chunk/table/figure carries a `self_ref` (e.g. `#/texts/12`). Open `preview.html?ref=%23%2Ftexts%2F12` to jump to the highlighted box on the page, or `<pdf-name>.html#texts-12` for the same block in the reading view (its `data-page` / `data-bbox` give the page region). See [docs/hand-off-notes/hand-off-note-for-citation.md](docs/hand-off-notes/hand-off-note-for-citation.md).

## 🔬 Worked example: one paper, three configs (real output, committed)

Input: [`showcase/Public-test-manuscript.pdf`](showcase/Public-test-manuscript.pdf): *Vision-Language and Large Language Model Performance in Gastroenterology* (arXiv preprint, 68 pages; Safavi-Naini et al., [arXiv:2409.00084](https://arxiv.org/abs/2409.00084), published in *npj Digital Medicine* 2025). The paper and its outputs are CC BY-NC-ND 4.0, not MIT: see [`showcase/LICENSE`](showcase/LICENSE).

| Config | Output | Time |
|---|---|---|
| Fast (no VLM) | [`showcase/fast/`](showcase/fast/Public-test-manuscript/) | 65 s |
| Middle (VLM on figures only) | [`showcase/figures-vlm/`](showcase/figures-vlm/Public-test-manuscript/) | 2.4 min |
| Suggested default | [`showcase/default/`](showcase/default/Public-test-manuscript/) | 11.8 min |

All three: **68 pages · 15 figures · 17 tables · 126–133 chunks · 0 errors.**
➡️ **[showcase/README.md](showcase/README.md)** compares them side by side (figure descriptions, table accuracy, versions) and helps you pick one.

Known rough edges: some supplementary figures/tables have no detected caption, the figure typer mislabels some charts (2 of 15 here, both with low confidence), and VLM descriptions can misstate numbers. Check the figure itself before citing a value.

## 🧩 What this fork adds on top of Docling

- `docling/engines/`: the Amir Engine (`PdfEngine`), the only new code subtree
- `amir-batch` CLI: batch conversion with a rich summary table (`--compare` A/Bs against full-page GraniteDocling)
- Clickable HTML bbox viewer, linked + standalone versions, deep-linkable by `self_ref`
- Agent-ready JSONL (chunks / tables / figures / nodes) + `run.json` provenance
- Standalone `<pdf-name>.html` that keeps everything Docling extracted (page headers/footers, text inside figures, table footnotes, reference numbers, formula text), marked rather than dropped
- Noise filter for journal logos and repeated banners, which never hides a picture BiomedCLIP confidently calls a medical image
- BiomedCLIP medical figure types (`ecg`, `ct`, `ultrasound`, `kaplan_meier`, ...)
- Repair of words the PDF parser splits around ligatures ("speci fi city" → "specificity"), checked against the PDF's own text
- Granite-Vision 4.1-4B figure-description preset + Granite-Vision tables, with fixes so they load under current `transformers`

More: [RUN.md](RUN.md) (CLI reference) · [.claude/HANDOFF.md](.claude/HANDOFF.md) (architecture + defaults).

## 📌 Releases: pin a version

Releases of this fork are git tags named `extrct_docling-v<docling version>-r<n>`: the upstream Docling version the fork is built on, plus `-r<n>`, the fork's revision on that base (`-r2` is the next fork release on the same Docling, a Docling upgrade restarts at `-r1`). Every bundle's `run.json` has an `engine` block with that version and, when run from a git checkout, the exact commit (`git_commit`) and whether tracked files had uncommitted changes (`git_dirty`). Any output can be traced back to the code that produced it.

| Release | Date | Based on | What's in it |
|---|---|---|---|
| [`extrct_docling-v2.131.0-r2`](https://github.com/Sdamirsa/extrct_docling/tree/extrct_docling-v2.131.0-r2) | 2026-11-03 | Docling v2.131.0 | The HTML also keeps captions and footnotes of code blocks (a boxed prompt Docling reads as code loses its "Table SI.x" caption in Docling's HTML) and any other child of a text item; `html_written_by` in the manifest names the release that wrote the HTML when it differs from the one that converted the PDF (`rebuild_document_html`) |
| [`extrct_docling-v2.131.0-r1`](https://github.com/Sdamirsa/extrct_docling/tree/extrct_docling-v2.131.0-r1) | 2026-11-03 | Docling v2.131.0 | First release: everything listed above, plus a cap on Granite-Vision table generation (it used the tokenizer's unset ~1e30 `model_max_length`, so a boxed prompt laid out like a table generated for over an hour) and, for a table whose model-typed cells miss words printed in its box, that box's PDF text in the HTML |

Pin it from another project:

```bash
# as a git submodule
git submodule add https://github.com/Sdamirsa/extrct_docling.git vendor/extrct_docling
git -C vendor/extrct_docling checkout extrct_docling-v2.131.0-r2

# or as a dependency (uv.lock then records the resolved commit)
uv add "docling-slim[standard,feat-ocr-rapidocr-onnx,models-vlm-inline] @ git+https://github.com/Sdamirsa/extrct_docling@extrct_docling-v2.131.0-r2"
```

In code, `docling.engines.ENGINE_VERSION` gives the release (`"2.131.0-r2"`).

---

<a id="docling-upstream"></a>

<p align="center">
  <a href="https://github.com/docling-project/docling">
    <img loading="lazy" alt="Docling" src="https://github.com/docling-project/docling/raw/main/docs/assets/docling_processing.png" width="100%"/>
  </a>
</p>

# Docling (upstream)

<p align="center">
  <a href="https://trendshift.io/repositories/17240" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17240" alt="DS4SD%2Fdocling | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</p>

[![arXiv](https://img.shields.io/badge/arXiv-2408.09869-b31b1b.svg)](https://arxiv.org/abs/2408.09869)
[![Docs](https://img.shields.io/badge/docs-live-brightgreen)](https://docling-project.github.io/docling/)
[![PyPI version](https://img.shields.io/pypi/v/docling)](https://pypi.org/project/docling/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/docling)](https://pypi.org/project/docling/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
[![prek](https://img.shields.io/badge/prek-enabled-brightgreen)](https://pypi.org/project/prek/)
[![License MIT](https://img.shields.io/github/license/docling-project/docling)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://static.pepy.tech/badge/docling/month)](https://pepy.tech/projects/docling)
[![Docling Actor](https://apify.com/actor-badge?actor=vancura/docling&fpr=docling)](https://apify.com/vancura/docling)
[![Chat with Dosu](https://dosu.dev/dosu-chat-badge.svg)](https://app.dosu.dev/097760a8-135e-4789-8234-90c8837d7f1c/ask?utm_source=github)
[![Discord](https://img.shields.io/discord/1399788921306746971?color=6A7EC2&logo=discord&logoColor=ffffff)](https://docling.ai/discord)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/10101/badge)](https://www.bestpractices.dev/projects/10101)
[![LF AI & Data](https://img.shields.io/badge/LF%20AI%20%26%20Data-003778?logo=linuxfoundation&logoColor=fff&color=0094ff&labelColor=003778)](https://lfaidata.foundation/projects/)

## What is Docling ?

Docling simplifies document processing by parsing diverse formats — including advanced PDF understanding — and providing seamless integrations with the generative AI ecosystem.

## Features

- 🗂️ Parsing of [multiple document formats][supported_formats] including PDF, DOCX, PPTX, XLSX, HTML, EPUB, Apple Pages, WAV, MP3, WebVTT, Box Notes, email formats (EML, MSG), images (PNG, TIFF, JPEG, ...), LaTeX, DocLang, plain text, and more
- 📑 Advanced PDF understanding incl. page layout, reading order, table structure, code, formulas, image classification, and more
- 🧬 A unified, expressive [DoclingDocument][docling_document] representation format
- ↪️ Various [export formats][supported_formats] and options, including Markdown, HTML, WebVTT, DocLang, [DocTags](https://arxiv.org/abs/2503.11576) and lossless JSON
- 📜 Support for several application-specific XML schemas including [DocLang](https://doclang.ai), [USPTO](https://www.uspto.gov/patents) patents, [JATS](https://jats.nlm.nih.gov/) articles, and [XBRL](https://www.xbrl.org/) financial reports.
- 🔒 Local execution capabilities for sensitive data and air-gapped environments
- 🤖 Plug-and-play [integrations][integrations] incl. LangChain, LlamaIndex, Crew AI & Haystack for agentic AI
- 🔍 Extensive OCR support for scanned PDFs and images
- 👓 Support for several Visual Language Models, such as ([GraniteDocling](https://huggingface.co/ibm-granite/granite-docling-258M))
- 🎙️ Audio support with Automatic Speech Recognition (ASR) models
- 🔌 Connect to any agent using the [MCP server](https://docling-project.github.io/docling/usage/mcp/)
- 🌐 Run Docling as a service with the [API server](https://docling-project.github.io/docling/usage/api_server/) (docling-serve)
- 💻 Simple and convenient CLI

### What's new

- 🎬 Parsing of video files (MP4, AVI, MOV, MKV, and WebM) with an ASR transcript and representative keyframes
- 📄 Parsing of ODF (OpenDocument Format) files for text documents (`.odt`), spreadsheets (`.ods`), and presentations (`.odp`)
- 💼 Parsing of XBRL (eXtensible Business Reporting Language) documents for financial reports
- 📧 Parsing of email files (`.eml`, `.msg`)
- 📚 Parsing of EPUB (Electronic Publication) files for e-books
- 🍎 Parsing of Apple Pages (`.pages`) documents and Keynote (`.key`) presentations
- 📝 Parsing of plain-text files (`.txt`, `.text`) and Markdown supersets (`.qmd`, `.Rmd`)
- 📊 Chart understanding (Barchart, Piechart, LinePlot): convert them into tables or code and add detailed descriptions

### Coming soon

- 📝 Metadata extraction, including title, authors, references & language
- 📝 Complex chemistry understanding (Molecular structures)

## Quickstart

### 1. Install

```bash
pip install docling
```

> **Note:** Python 3.9 support was dropped in docling version 2.70.0. Please use Python 3.10 or higher.

Works on macOS, Linux and Windows environments for both x86_64 and arm64 architectures.

More [detailed installation instructions](https://docling-project.github.io/docling/getting_started/installation/) are available in the docs.

## 2. Convert a document (CLI)

```bash
docling https://arxiv.org/pdf/2206.01062
```

This generates a .md file in the current directory containing structured document content.

You can also use 🥚[GraniteDocling](https://huggingface.co/ibm-granite/granite-docling-258M) and other VLMs via Docling CLI:

```bash
docling --pipeline vlm --vlm-model granite_docling https://arxiv.org/pdf/2206.01062
```

## 3. Python usage (recommended)

```python
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # a document via a local path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"
```

More advanced [usage](https://docling-project.github.io/docling/usage/) and [configuration](https://docling-project.github.io/docling/getting_started/installation/) options.

## Documentation

Check out Docling's [documentation](https://docling-project.github.io/docling/) for details on
installation, usage, concepts, recipes, extensions, and more.

## Examples

Go hands-on with our [examples](https://docling-project.github.io/docling/examples/),
demonstrating how to address different application use cases with Docling.

## Integrations

To further accelerate your AI application development, check out Docling's native
[integrations](https://docling-project.github.io/docling/integrations/) with popular frameworks
and tools.

## Get help and support

Please feel free to connect with us using the [discussion section](https://github.com/docling-project/docling/discussions).

## Technical report

For more details on Docling's inner workings, check out the [Docling Technical Report](https://arxiv.org/abs/2408.09869).

## Contributing

Please read [Contributing to Docling](https://github.com/docling-project/docling/blob/main/CONTRIBUTING.md) for details.

## References

If you use Docling in your projects, please consider citing the following:

```bib
@techreport{Docling,
  author = {Deep Search Team},
  month = {8},
  title = {Docling Technical Report},
  url = {https://arxiv.org/abs/2408.09869},
  eprint = {2408.09869},
  doi = {10.48550/arXiv.2408.09869},
  version = {1.0.0},
  year = {2024}
}
```

## License

The Docling codebase is under MIT license.
For individual model usage, please refer to the model licenses found in the original packages.

## LF AI & Data

Docling is hosted as a project in the [LF AI & Data Foundation](https://lfaidata.foundation/projects/).

### IBM ❤️ Open Source AI

The project was started by the AI for knowledge team at IBM Research Zurich.

[supported_formats]: https://docling-project.github.io/docling/usage/supported_formats/
[docling_document]: https://docling-project.github.io/docling/concepts/docling_document/
[integrations]: https://docling-project.github.io/docling/integrations/
[extraction]: https://docling-project.github.io/docling/_generated/examples/extraction/
