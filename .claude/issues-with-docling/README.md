# Issues with upstream Docling

Tracking known limitations / bugs in upstream Docling that affect the
**Amir Engine** build. Each issue file describes a single failure mode with
a reproducer, root-cause hypothesis, and tested workarounds (if any).

## Conventions

- One markdown file per issue, kebab-case filename.
- Front-matter as a header table: `Severity`, `Status`, `First-seen`, `Upstream-issue`.
- Reproducer must be a concrete file in this repo (e.g. under `samples/` or
  `tests/data/`) — no "I once saw this".
- Workarounds must say whether they were *tested* or *hypothesised*.

## Index

| File | One-line summary |
|---|---|
| [reading-order-mixed-layout-page.md](reading-order-mixed-layout-page.md) | Column-flip on a page that mixes full-width (abstract spillover) and two-column body regions. |
| [cross-page-merge-bbox-page-height.md](cross-page-merge-bbox-page-height.md) | Continuation of a paragraph on a page of another size is boxed with the first page's height (patched in the fork). |
| [watermark-cell-swallows-page.md](watermark-cell-swallows-page.md) | A diagonal watermark's page-sized cell box folds each page into one text block: no headings, no paragraphs (patched in the fork). |
| [opencv5-resize-segfault-aarch64.md](opencv5-resize-segfault-aarch64.md) | Intermittent SIGSEGV in RapidOCR's `cv2.resize` (OpenCV 5.0.0, aarch64) that kills a whole `amir-batch` run. |
