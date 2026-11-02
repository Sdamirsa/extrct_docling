# Docling — Condensed Repo Context

> Python SDK + CLI that converts PDFs, Office, HTML, Markdown, audio, images, XML, LaTeX, etc. into a unified `DoclingDocument`. Powers the **Amir Engine** (see [AMIR_TODO.md](AMIR_TODO.md)).

## High-level flow

```
input file/URL ─► Backend (parse) ─► Pipeline (orchestrate models)
                                       │
                                       ├─ Layout / Table / OCR / VLM / ASR models
                                       │
                                       └─► DoclingDocument ─► Exporters (md / html / json / DocTags / WebVTT)
```

Entry point for SDK use: [`docling/document_converter.py`](../docling/document_converter.py) → `DocumentConverter().convert(source)` returns a `ConversionResult` whose `.document` is a `DoclingDocument`.

Structured extraction (beta): [`docling/document_extractor.py`](../docling/document_extractor.py).

## Package map

```
docling/
├── document_converter.py    # main entry: DocumentConverter
├── document_extractor.py    # structured info extraction (beta)
├── engines/                 # ⭐ Amir Engine (project-local, not upstream Docling)
│   ├── pdf_engine.py        #   thin facade over DocumentConverter
│   ├── schemas.py           #   PdfConversionOutput, PageSummary, PdfEngineError
│   ├── validation.py        #   classify_source / validate_pdf_source
│   ├── artifacts.py         #   write_artifacts → document.json + nodes.jsonl + image crops
│   ├── chunker.py           #   write_chunks → chunks.jsonl (HybridChunker)
│   ├── structured_outputs.py # write_structured_outputs → tables.jsonl + figures.jsonl
│   ├── picture_filter.py    #   classify_pictures → noise flags (logos/banners)
│   ├── vlm_specs.py         #   build_picture_description_options (incl. Qwen2.5-VL-3B vLLM)
│   ├── compare_pipelines.py #   run_comparison → standard/ vs full_page_vlm/
│   ├── run_snapshot.py      #   write_run_snapshot → run.json (env + timing + models)
│   └── visualizer.py        #   render_html_preview → clickable bbox viewer w/ side panel
├── backend/                 # format parsers (one per input type)
│   ├── pdf_backend.py, docling_parse_v4_backend.py, pypdfium2_backend.py
│   ├── html_backend.py, md_backend.py, msword_backend.py, msexcel_backend.py
│   ├── mspowerpoint_backend.py, webvtt_backend.py, latex_backend.py, ...
├── pipeline/                # orchestrators that run models over backend output
│   ├── standard_pdf_pipeline.py, threaded_standard_pdf_pipeline.py
│   ├── vlm_pipeline.py, asr_pipeline.py, extraction_vlm_pipeline.py
│   └── simple_pipeline.py
├── models/                  # ML model wrappers (layout, tables, OCR, VLM, ASR, picture-desc)
│   ├── base_*_model.py, factories/, inference_engines/, stages/, vlm_pipeline_models/
├── datamodel/               # Pydantic schemas + options
│   ├── document.py          # DoclingDocument-adjacent types
│   ├── pipeline_options.py, pipeline_options_vlm_model.py
│   ├── extraction_options.py, accelerator_options.py, settings.py
├── chunking/                # chunkers for downstream RAG
├── cli/                     # `docling` CLI
├── service_client/          # KServe / remote inference clients
├── utils/, exceptions.py, experimental/
```

## Where to plug Amir Engine in

| Amir need | Docling primitive to use | File |
|---|---|---|
| PDF → structured doc | `DocumentConverter` | [`docling/document_converter.py`](../docling/document_converter.py) |
| Pipeline customisation | Subclass `StandardPdfPipeline` or assemble own | [`docling/pipeline/standard_pdf_pipeline.py`](../docling/pipeline/standard_pdf_pipeline.py) |
| Table extraction | `TableStructureModel` (in `models/`) via pipeline | [`docling/models/`](../docling/models/) |
| Image / chart / picture description | `picture_description_base_model.py`, `vlm_pipeline_models/` | [`docling/models/`](../docling/models/) |
| VLM (GraniteDocling) | `VlmPipeline` + VLM model specs | [`docling/pipeline/vlm_pipeline.py`](../docling/pipeline/vlm_pipeline.py), [`docling/datamodel/vlm_model_specs.py`](../docling/datamodel/vlm_model_specs.py) |
| Bounding boxes / page layout | `DoclingDocument` items expose `prov` with bbox + page | [`docling/datamodel/document.py`](../docling/datamodel/document.py) |
| Structured info extraction | `DocumentExtractor` (beta) | [`docling/document_extractor.py`](../docling/document_extractor.py) |
| Pydantic-typed options | `pipeline_options.py`, `extraction_options.py` | [`docling/datamodel/`](../docling/datamodel/) |
| **Single-call PDF pipeline (Amir)** | `PdfEngine` | [`docling/engines/pdf_engine.py`](../docling/engines/pdf_engine.py) |
| **Per-PDF persistent artifacts** | `write_artifacts` | [`docling/engines/artifacts.py`](../docling/engines/artifacts.py) |
| **HybridChunker → chunks.jsonl** | `write_chunks` | [`docling/engines/chunker.py`](../docling/engines/chunker.py) |
| **Tables / figures clean JSON** | `write_structured_outputs` | [`docling/engines/structured_outputs.py`](../docling/engines/structured_outputs.py) |
| **Noise picture filter** | `classify_pictures` | [`docling/engines/picture_filter.py`](../docling/engines/picture_filter.py) |
| **Picture description VLM presets** | `build_picture_description_options` | [`docling/engines/vlm_specs.py`](../docling/engines/vlm_specs.py) |
| **Standard vs full-page VLM A/B** | `run_comparison` | [`docling/engines/compare_pipelines.py`](../docling/engines/compare_pipelines.py) |
| **Run reproducibility snapshot** | `write_run_snapshot` | [`docling/engines/run_snapshot.py`](../docling/engines/run_snapshot.py) |
| **Clickable bbox preview** | `render_html_preview` | [`docling/engines/visualizer.py`](../docling/engines/visualizer.py) |

## Conventions to follow when extending

- New input format → add a backend in `docling/backend/` inheriting from `abstract_backend.py`.
- New model → inherit from `base_model.py` (or the specific `base_*_model.py`) and register via `models/factories/`.
- New orchestration → add a pipeline in `docling/pipeline/` inheriting from `base_pipeline.py`.
- New options → Pydantic v2 model in `docling/datamodel/`, not loose dicts.
- Public APIs typed; Python 3.10+; `pathlib.Path` everywhere; no `hasattr` probing.

## Key commands

```bash
make setup       # install dev env (⚠ broken on aarch64 — see below)
make test        # pytest
make check       # read-only checks
make validate    # mutating hooks on current changeset (run before done)
uv run pytest tests/test_<area>.py   # targeted tests
DOCLING_GEN_TEST_DATA=1 uv run pytest  # regen golden data (only when intended)
```

### aarch64 / Jetson / Grace Hopper install

`make setup` (`uv sync --frozen --all-extras`) fails on Linux aarch64 because
`onnxruntime-gpu` only publishes x86_64 wheels on PyPI. Use the targeted set
instead — same coverage minus the ONNX-GPU OCR variant:

```bash
uv sync --frozen --group dev --no-group docs --no-group examples --extra standard --extra models-vlm-inline
```

The `standard` extra pulls `format-pdf`, `models-local` (torch), `feat-ocr-rapidocr`,
office/web/latex backends, chunking, CLI and extract-core — enough for the full
Amir Engine build through Phase 4. To restore ONNX-GPU on aarch64, install
NVIDIA's Jetson `onnxruntime-gpu` wheel manually (Jetson Zoo) or patch
`pyproject.toml` so `models-onnxruntime` falls back to CPU `onnxruntime` on
aarch64.

## Amir Engine usage (Phase 1)

```python
from pathlib import Path
from docling.engines import PdfEngine

out = PdfEngine(images_scale=1.5).convert(
    Path("samples/test-pdf-ai-manuscript.pdf"),
    output_dir=Path("samples/out"),
    make_html_preview=True,
)
# samples/out/<pdf-stem>/{<pdf-stem>.md, document.json, nodes.jsonl, run.json,
#   images/page_*.png, images/picture_*.png, images/table_*.png, preview.html}
```

`PdfEngine` flags (Phase 1+2+3):
- `save_artifacts=True` (default) — `document.json`, `nodes.jsonl`, `chunks.jsonl`, `tables.jsonl`, `figures.jsonl`, `run.json`, image crops. Auto-enables page + picture image generation.
- `link_images=True` (default) — primary `<stem>.md` rewrites `<!-- image -->` placeholders to `![](images/picture_NNN.png)`.
- `embed_images=True` (default) — additionally writes `<stem>.embedded.md` with base64 data URIs and `<stem>.html` (`docling/engines/html_export.py`: Docling HTML + per-block `data-self-ref`/`data-page`/`data-bbox` + JSON manifest; `rebuild_document_html(pdf_dir)` regenerates it from a bundle).
- `filter_noise_pictures=True` (default) — flags logos / watermarks / repeated banners (classifier + bbox-repeat heuristic). Strips them from both markdown files; tags `is_noise` in `figures.jsonl`. Uses Docling's generic DocumentFigureClassifier, whose labels have no medical classes — trusted for noise only (`generic_classifier_label`).
- `figure_types=True` (default) — BiomedCLIP zero-shot figure type (`ct`, `angiography`, `ecg`, `kaplan_meier`, `bar_chart`, ...) in `docling/engines/figure_typing.py` → `figures.jsonl[*].figure_type` + `PictureItem.meta.amir__figure_type`. Needs `models-vlm-inline` extra.
- `chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2"`, `chunk_max_tokens=512` — chunker config.
- `granite_vision_tables=False` — opt-in: swap TableFormer for Granite-Vision VLM table structure (~2B model).
- `picture_description=None` — set to `"smolvlm"`, `"granite_vision"`, `"pixtral"`, `"qwen25_vl_3b"` to add VLM captions to figures. `picture_description_engine="vllm"` (default) | `"transformers"` | `"default"`.

Compare standard vs. full-page VLM:
```python
from pathlib import Path
from docling.engines import run_comparison
run_comparison(
    Path("samples/my-paper.pdf"),
    Path("samples/out"),
    vlm_preset="granite_docling",   # DocTags → comparable bundles
)
# writes samples/out/my-paper/{standard,full_page_vlm,comparison.md}
```

## External docs

- Live docs: https://docling-project.github.io/docling/
- DoclingDocument format & DocTags: see `docs/` and the arXiv references in [README.md](../README.md).
- GraniteDocling VLM: https://huggingface.co/ibm-granite/granite-docling-258M
