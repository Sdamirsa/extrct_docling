# Samples

Drop test PDFs in this folder (e.g. `samples/my-paper.pdf`). Files here are
gitignored except for this README.

## Convert (default — full artifact bundle)

```bash
uv run python -c "
from pathlib import Path
from docling.engines import PdfEngine

out = PdfEngine(images_scale=1.5).convert(
    Path('samples/my-paper.pdf'),
    output_dir=Path('samples/out'),
    make_html_preview=True,
)
print('status :', out.status)
print('pages  :', out.page_count)
print('saved  :', out.output_dir)
print('preview:', out.preview_html)
"
# then open the clickable viewer
xdg-open samples/out/my-paper/preview.html   # Linux
open samples/out/my-paper/preview.html       # macOS
```

## What lands in `samples/out/<pdf-stem>/`

| File | Content |
|---|---|
| `<pdf-stem>.md` | Primary markdown. Image placeholders are rewritten to `![](images/picture_NNN.png)` relative refs (controlled by `link_images=True`, default). Pictures flagged as noise (logos, repeated banners) are stripped and replaced with `<!-- noise picture: reason -->`. |
| `<pdf-stem>.embedded.md` | Standalone companion with images inlined as base64 (when `embed_images=True`, default). Same noise filtering applied. ~10–15× larger than primary. |
| `<pdf-stem>.html` | Standalone manuscript HTML (when `embed_images=True`, default): Docling's HTML export with figures inlined and noise pictures dropped; every block has `id` / `data-self-ref` / `data-page` / `data-bbox`, and a `<script id="extrct-manifest">` JSON holds the figures / tables / chunks rows and `run.json`. |
| `chunks.jsonl` | `HybridChunker` output, one chunk per line: `{index, text, token_count, headings, page_nos, self_refs}`. RAG-ready. |
| `tables.jsonl` | One row per table: caption, markdown rendering, HTML rendering, dimensions, flat cells with row/col offsets and spans, image_path. |
| `figures.jsonl` | One row per figure: caption_text, image_path, **figure_type** + **figure_type_confidence** (BiomedCLIP), **vlm_caption** (when picture description on), **generic_classifier_label** (noise filter only), **is_noise** + **noise_reason**, raw annotations. |
| `document.json` | Full `DoclingDocument` serialisation (canonical, round-trippable). |
| `nodes.jsonl` | One JSON object per node from `iterate_items()` — label, bbox/page (`prov`), text, captions, table cells, plus `_kind`, `_level`, and `image_path` for pictures/tables. |
| `run.json` | Reproducibility snapshot: schema version, source, status, timing, engine config, full `pipeline_options` (incl. model spec), per-stage models summary, environment (python, platform, machine, package versions), output summary, errors. |
| `images/page_NNNN.png` | Page renders. |
| `images/picture_NNN.png` | Extracted figures (`PictureItem.get_image()`). |
| `images/table_NNN.png` | Extracted tables (`TableItem.get_image()`). |
| `preview.html` | Bounding-box viewer — **click any box** to open a side panel with that node's full metadata (same data as `nodes.jsonl`). Press `Esc` to clear. |

## Useful flags

```python
PdfEngine(
    # Phase 1
    save_artifacts=True,         # default — full artifact bundle (also chunks/tables/figures jsonl + run.json)
    link_images=True,            # default — primary .md uses relative refs
    embed_images=True,           # default — also writes <stem>.embedded.md
    images_scale=1.5,
    # Phase 2 (chunking)
    chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2",
    chunk_max_tokens=512,
    # Phase 3 (opt-in heavy models)
    granite_vision_tables=False, # set True to swap TableFormer for Granite-Vision (2B)
    picture_description=None,    # "smolvlm" | "granite_vision" | "pixtral" | "qwen25_vl_3b"
    picture_description_engine="vllm",
    # Phase 3 (default-on noise filter)
    filter_noise_pictures=True,  # tags + strips logos/watermarks/repeated banners from md
)
```

## Run the full-page VLM comparison

```python
from pathlib import Path
from docling.engines import run_comparison

result = run_comparison(
    Path("samples/test-pdf-ai-manuscript.pdf"),
    Path("samples/out"),
    vlm_preset="granite_docling",   # default — DocTags response → comparable bundles
)
# writes:
#   samples/out/test-pdf-ai-manuscript/standard/       (regular PdfEngine output)
#   samples/out/test-pdf-ai-manuscript/full_page_vlm/  (VlmPipeline output)
#   samples/out/test-pdf-ai-manuscript/comparison.md   (side-by-side summary)
```

Tell Claude later: *"run the full-page VLM comparison on samples/foo.pdf"* and it'll invoke `run_comparison()` for you.

## URL inputs (no local file needed)

```python
out = PdfEngine().convert("https://arxiv.org/pdf/2206.01062")
```
