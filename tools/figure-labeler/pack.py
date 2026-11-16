"""Pack chart-like figures from Amir bundles into a self-contained labelling folder.

Usage::

    uv run --no-sync python tools/figure-labeler/pack.py <bundle_dir>... --out <folder>
        [--refs "#/pictures/4,HeartAgent#/pictures/1"] [--types bar_chart,line_chart]
        [--pdf-dir <dir>] [--hires-scale 3]

Without ``--refs`` every non-noise figure whose ``figure_type`` is in
``--types`` is packed. A ref written ``<bundle>#/pictures/N`` applies to that
bundle only; a bare ``#/pictures/N`` applies to every bundle.

The folder gets ``figures/<bundle>__picturesN.png`` (the bundle crop, the
pixel space of ``bbox_px``), ``figures/<bundle>__picturesN@hi.png`` (the same
box rendered from the PDF, display only), ``manifest.js`` (helper evidence,
``window.LABELER_MANIFEST = {...}``), the web app, ``schema.json``, the
README and an empty ``labels/``. Existing files in ``labels/`` are kept.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

# Sibling module: the script's folder is first on sys.path when run as a script.
from validate import SCHEMA_ID, json_schema  # isort: skip

KIT_DIR = Path(__file__).resolve().parent
KIT_FILES = ("index.html", "labeler-core.js", "labeler.js", "labeler.css", "README.md")
CHART_TYPES = (
    "bar_chart",
    "line_chart",
    "scatter_plot",
    "box_plot",
    "forest_plot",
    "kaplan_meier",
    "roc_curve",
    "heatmap",
    "pie_chart",
)


@dataclass(frozen=True)
class Word:
    text: str
    bbox_px: tuple[float, float, float, float]


@dataclass(frozen=True)
class CropFrame:
    """Maps top-left page points into pixels of the bundle crop."""

    left: float
    top: float
    sx: float
    sy: float
    width: int
    height: int

    def to_px(
        self, x_l: float, y_t: float, x_r: float, y_b: float
    ) -> tuple[float, float, float, float] | None:
        """Top-left page box ``[l, t, r, b]`` in points -> crop pixels, or None when its centre is outside."""
        x0, x1 = (x_l - self.left) * self.sx, (x_r - self.left) * self.sx
        y0, y1 = (y_t - self.top) * self.sy, (y_b - self.top) * self.sy
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if not (0 <= cx <= self.width and 0 <= cy <= self.height):
            return None
        return (
            round(max(0.0, x0), 1),
            round(max(0.0, y0), 1),
            round(min(float(self.width), x1), 1),
            round(min(float(self.height), y1), 1),
        )


@dataclass(frozen=True)
class ManifestFigure:
    id: str
    image: str
    image_hires: str | None
    width: int
    height: int
    bundle: str
    bundle_dir: str
    self_ref: str
    image_path: str
    page: int
    bbox: tuple[float, float, float, float]
    bbox_origin: str
    page_size: tuple[float, float]
    px_per_pt: float
    caption_text: str | None
    figure_type: str | None
    figure_type_confidence: float | None
    classifier_label: str | None
    vlm_caption: str | None
    pdf: str | None
    words_docling: list[Word]
    words_pdf: list[Word]


def _top_left(bbox: dict, page_height: float) -> tuple[float, float, float, float]:
    if bbox["coord_origin"] == "BOTTOMLEFT":
        return bbox["l"], page_height - bbox["t"], bbox["r"], page_height - bbox["b"]
    return bbox["l"], bbox["t"], bbox["r"], bbox["b"]


def _resolve_ref(doc: dict, ref: str) -> dict:
    _, collection, index = ref.split("/")
    return doc[collection][int(index)]


def docling_words(
    doc: dict, picture: dict, page_no: int, frame: CropFrame
) -> list[Word]:
    """Text items Docling placed inside the picture (text layer or OCR), in crop pixels."""
    page_height = doc["pages"][str(page_no)]["size"]["height"]
    words: list[Word] = []
    stack = [c["$ref"] for c in reversed(picture["children"])]
    while stack:
        item = _resolve_ref(doc, stack.pop())
        stack.extend(c["$ref"] for c in reversed(item.get("children", [])))
        text = (item.get("text") or "").strip()
        if not text:
            continue
        for prov in item.get("prov", []):
            if prov["page_no"] != page_no:
                continue
            box = frame.to_px(*_top_left(prov["bbox"], page_height))
            if box is not None:
                words.append(Word(text, box))
    return words


def _adjacent(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    """Character boxes close enough to belong to one word (any reading direction)."""
    size = max(a[2] - a[0], a[3] - a[1], b[2] - b[0], b[3] - b[1], 1.0)
    pad = 0.35 * size
    return not (
        b[0] > a[2] + pad or b[2] < a[0] - pad or b[1] > a[3] + pad or b[3] < a[1] - pad
    )


def pdf_words(page: pdfium.PdfPage, frame: CropFrame) -> list[Word]:
    """Words of the PDF text layer whose centre lies inside the picture box, in crop pixels."""
    left, bottom, _, top = page.get_cropbox()
    height = top - bottom
    textpage = page.get_textpage()
    words: list[Word] = []
    chars: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []

    def flush() -> None:
        if chars:
            words.append(
                Word(
                    "".join(chars),
                    (
                        min(b[0] for b in boxes),
                        min(b[1] for b in boxes),
                        max(b[2] for b in boxes),
                        max(b[3] for b in boxes),
                    ),
                )
            )
        chars.clear()
        boxes.clear()

    for i in range(textpage.count_chars()):
        ch = textpage.get_text_range(i, 1)
        if not ch or ch.isspace():
            flush()
            continue
        c_l, c_b, c_r, c_t = textpage.get_charbox(i)
        box = frame.to_px(
            c_l - left, height - (c_t - bottom), c_r - left, height - (c_b - bottom)
        )
        if box is None or (boxes and not _adjacent(boxes[-1], box)):
            flush()
        if box is not None:
            chars.append(ch)
            boxes.append(box)
    flush()
    textpage.close()
    return words


def _parse_refs(spec: str | None) -> dict[str, list[str]] | None:
    """``"#/pictures/4,HeartAgent#/pictures/1"`` -> ``{"": [...], "HeartAgent": [...]}``."""
    if not spec:
        return None
    refs: dict[str, list[str]] = {}
    for raw in spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        bundle, _, rest = raw.partition("#")
        refs.setdefault(bundle, []).append("#" + rest)
    return refs


def select(
    records: list[dict], bundle: str, refs: dict[str, list[str]] | None, types: set[str]
) -> Iterator[dict]:
    if refs is None:
        yield from (
            r for r in records if not r["is_noise"] and r["figure_type"] in types
        )
        return
    wanted = refs.get("", []) + refs.get(bundle, [])
    by_ref = {r["self_ref"]: r for r in records}
    for ref in wanted:
        if ref in by_ref:
            yield by_ref[ref]
        elif ref in refs.get(bundle, []):
            print(f"  ! {bundle}: {ref} not in figures.jsonl", file=sys.stderr)


def _find_pdf(bundle_dir: Path, pdf_dir: Path | None) -> Path | None:
    if pdf_dir is not None:
        candidate = pdf_dir / f"{bundle_dir.name}.pdf"
        if candidate.is_file():
            return candidate
    run_json = bundle_dir / "run.json"
    if not run_json.is_file():
        return None
    source = Path(json.loads(run_json.read_text(encoding="utf-8"))["source"]["input"])
    # run.json stores the input as given to the CLI, usually relative to the repo root.
    for base in (Path.cwd(), *bundle_dir.resolve().parents):
        if (base / source).is_file():
            return base / source
    return None


def pack_bundle(
    bundle_dir: Path,
    out: Path,
    refs: dict[str, list[str]] | None,
    types: set[str],
    pdf_dir: Path | None,
    hires_scale: float,
) -> list[ManifestFigure]:
    bundle = bundle_dir.name
    records = [
        json.loads(line)
        for line in (bundle_dir / "figures.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    chosen = list(select(records, bundle, refs, types))
    if not chosen:
        return []
    doc = json.loads((bundle_dir / "document.json").read_text(encoding="utf-8"))
    pdf_path = _find_pdf(bundle_dir, pdf_dir)
    pdf = pdfium.PdfDocument(pdf_path) if pdf_path else None
    if pdf is None:
        print(
            f"  ! {bundle}: source PDF not found, no PDF words or hi-res images",
            file=sys.stderr,
        )
    figures: list[ManifestFigure] = []
    for rec in chosen:
        index = int(rec["self_ref"].rsplit("/", 1)[-1])
        image_path = rec["image_path"] or f"images/picture_{index + 1:03d}.png"
        crop = bundle_dir / image_path
        if not crop.is_file():
            print(
                f"  ! {bundle} {rec['self_ref']}: crop {image_path} missing, skipped",
                file=sys.stderr,
            )
            continue
        prov = rec["prov"][0]
        page_no = prov["page_no"]
        page_w = doc["pages"][str(page_no)]["size"]["width"]
        page_h = doc["pages"][str(page_no)]["size"]["height"]
        x_l, y_t, x_r, y_b = _top_left(prov["bbox"], page_h)
        with Image.open(crop) as im:
            width, height = im.size
        frame = CropFrame(
            x_l, y_t, width / (x_r - x_l), height / (y_b - y_t), width, height
        )
        fig_id = f"{bundle}__pictures{index}"
        dest = out / "figures" / f"{fig_id}.png"
        shutil.copyfile(crop, dest)

        words_pdf: list[Word] = []
        hires: str | None = None
        if pdf is not None:
            page = pdf[page_no - 1]
            if page.get_rotation():
                print(
                    f"  ! {fig_id}: rotated page, PDF words may be misplaced",
                    file=sys.stderr,
                )
            words_pdf = pdf_words(page, frame)
            if hires_scale > 0:
                image = page.render(scale=hires_scale).to_pil()
                box = tuple(round(v * hires_scale) for v in (x_l, y_t, x_r, y_b))
                image.crop(box).save(
                    out / "figures" / f"{fig_id}@hi.png", optimize=True
                )
                hires = f"figures/{fig_id}@hi.png"
            page.close()

        figures.append(
            ManifestFigure(
                id=fig_id,
                image=f"figures/{fig_id}.png",
                image_hires=hires,
                width=width,
                height=height,
                bundle=bundle,
                bundle_dir=bundle_dir.as_posix(),
                self_ref=rec["self_ref"],
                image_path=image_path,
                page=page_no,
                bbox=(round(x_l, 2), round(y_t, 2), round(x_r, 2), round(y_b, 2)),
                bbox_origin="TOPLEFT",
                page_size=(page_w, page_h),
                px_per_pt=round(frame.sx, 4),
                caption_text=rec.get("caption_text"),
                figure_type=rec.get("figure_type"),
                figure_type_confidence=rec.get("figure_type_confidence"),
                classifier_label=rec.get("generic_classifier_label"),
                vlm_caption=rec.get("vlm_caption"),
                pdf=pdf_path.name if pdf_path else None,
                words_docling=docling_words(
                    doc, _resolve_ref(doc, rec["self_ref"]), page_no, frame
                ),
                words_pdf=words_pdf,
            )
        )
        print(
            f"  {fig_id}: {rec.get('figure_type')} {width}x{height}px, "
            f"words docling {len(figures[-1].words_docling)} / pdf {len(words_pdf)}"
        )
    if pdf is not None:
        pdf.close()
    return figures


def write_kit(out: Path, figures: list[ManifestFigure], argv: list[str]) -> None:
    for name in KIT_FILES:
        shutil.copyfile(KIT_DIR / name, out / name)
    (out / "schema.json").write_text(
        json.dumps(json_schema(), indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema": "extrct.figure-labeler-manifest/1",
        "label_schema": SCHEMA_ID,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(argv),
        "figures": [asdict(f) for f in figures],
    }
    (out / "manifest.js").write_text(
        "window.LABELER_MANIFEST = " + json.dumps(manifest, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "bundles", nargs="+", type=Path, help="bundle folders (with figures.jsonl)"
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="pack folder to create or update"
    )
    parser.add_argument(
        "--refs", help="comma-separated self_refs, optionally prefixed by bundle name"
    )
    parser.add_argument(
        "--types", default=",".join(CHART_TYPES), help="figure_type values to pack"
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        help="folder with <bundle>.pdf (default: run.json source)",
    )
    parser.add_argument(
        "--hires-scale",
        type=float,
        default=3.0,
        help="PDF render scale for display images; 0 = off",
    )
    args = parser.parse_args(argv)

    out: Path = args.out
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(exist_ok=True)
    refs = _parse_refs(args.refs)
    types = {t.strip() for t in args.types.split(",") if t.strip()}
    figures: list[ManifestFigure] = []
    for bundle_dir in args.bundles:
        if not (bundle_dir / "figures.jsonl").is_file():
            print(f"  ! {bundle_dir}: no figures.jsonl, skipped", file=sys.stderr)
            continue
        figures.extend(
            pack_bundle(bundle_dir, out, refs, types, args.pdf_dir, args.hires_scale)
        )
    write_kit(out, figures, sys.argv if argv is None else ["pack.py", *argv])
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"packed {len(figures)} figures into {out} ({size / 1e6:.1f} MB)")
    return 0 if figures else 1


if __name__ == "__main__":
    raise SystemExit(main())
