# Intermittent segfault in RapidOCR's `cv2.resize` (OpenCV 5.0.0, aarch64)

| | |
|---|---|
| **Severity** | High for batches — a native crash kills the whole `amir-batch` process, so every PDF queued after it is lost |
| **Status** | Open; workaround in use (one process per PDF + retry) |
| **First-seen** | 2026-10-01, processing `samples/archived/S_20pdfs/` on the DGX Spark (GB10, Linux aarch64) |
| **Affects** | OCR stage: `docling/models/stages/ocr/rapid_ocr_model.py` → `rapidocr/ch_ppocr_det/utils.py::resize` → `cv2.resize`; `opencv-python` 5.0.0, `onnxruntime` 1.29.0 (CPU), torch 2.14.0+cu130, Python 3.13 |
| **Upstream issue** | _not filed_ |

## Symptom

`amir-batch` exits with code 139 (SIGSEGV), no Python traceback. With
`PYTHONFAULTHANDLER=1` the faulting frame is always RapidOCR's text-detector
preprocessing:

```
rapidocr/ch_ppocr_det/utils.py, line 106 in resize   # cv2.resize(img, (w, h))
rapidocr/main.py, line 301 in detect_and_crop
docling/models/stages/ocr/rapid_ocr_model.py, line 687 in __call__
docling/pipeline/standard_pdf_pipeline.py, line 361 in _process_batch
```

gdb shows the fault inside `cv2/cv2.abi3.so` itself.

## Reproducer

Local-only (the `samples/` tree is gitignored — the PDF is a copyrighted
paper): `samples/archived/S_20pdfs/19859766.pdf` (3 pages), fast config:

```bash
uv run --frozen amir-batch samples/archived/S_20pdfs/19859766.pdf -o /tmp/x \
  --picture-description off --no-granite-vision-tables --no-preview
```

Crashed 5 of 6 consecutive runs with artifacts on (`images_scale=1.5`, page +
picture images). Succeeded every time with `save_artifacts=False`, once under
gdb, and once inside a 12-PDF per-process loop.

## What it is not (tested)

- **Not image size.** The crop that crashes is an ordinary 1986×1542×3 uint8
  C-contiguous array; RapidOCR resizes it to 1984×1536 (ratio 1.0). The same
  saved array resizes fine standalone — on the main thread, in a worker
  thread, and with torch / onnxruntime imported first.
- **Not OpenCV's thread pool.** `cv2.setNumThreads(1)` before conversion
  still crashes.
- **Not the picture classifier.** `filter_noise_pictures=False` still
  crashes.

Correlation observed: crash runs OCR the large crop *first*; successful runs
OCR a small (78×639) crop first. Thread scheduling decides the order, which
fits the run-to-run nondeterminism. Root cause unknown; suspects are OpenCV
5.0's aarch64 resize path (KleidiCV HAL) interacting with process state, or
heap corruption from a concurrent native library (e.g. pdfium page rendering
in another pipeline thread).

## Workaround (tested)

Run each PDF in its own process and retry on exit codes ≥ 128 — a crash then
costs one attempt of one PDF instead of the rest of the batch. Used for the
2026-10-01 S_20pdfs re-run:

```bash
for pdf in samples/archived/S_20pdfs/*.pdf; do
  for attempt in 1 2 3; do
    uv run --frozen amir-batch "$pdf" -o samples/archived/S_20pdfs_out; rc=$?
    [ $rc -lt 128 ] && break
  done
done
```

Untested candidates: pin `opencv-python(-headless)<5`; switch the OCR engine
(EasyOCR / Tesseract via `PdfPipelineOptions.ocr_options` — `amir-batch` has
no flag for it yet); make `amir-batch` itself run each PDF in a subprocess.
