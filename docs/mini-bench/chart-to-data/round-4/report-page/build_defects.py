"""Build the round-4 defects page: the capture defect that was fixed and
the defects of the figure-to-data step that are open, each with its
evidence.

    uv run --no-sync python docs/mini-bench/chart-to-data/round-4/report-page/build_defects.py <out.html>

Run from the repository root. Reads defects.json (the page's prose) and
defects_template.html beside this script, ../metrics/pipeline.json, the
truth, and the prepared figures under ../runs/ and ../after-fix/. The
figure images are embedded with the charts the step found drawn on them,
so the output holds the paper's artwork: keep it out of the repository and
share it only privately.
"""

import base64
import io
import json
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
BUNDLE = "Public-test-manuscript"
OUT = Path(sys.argv[1])
TEXT = json.loads((HERE / "defects.json").read_text(encoding="utf-8"))
PIPELINE = json.loads((ROUND / "metrics" / "pipeline.json").read_text(encoding="utf-8"))
FIRST = ROUND / "runs" / "cloud-sonnet-5-5" / BUNDLE / "figure-to-data"
AGAIN = ROUND / "after-fix" / "runs" / "cloud-sonnet-5-5" / BUNDLE / "figure-to-data"
NAMES = {
    "ollama-gemma4-26b-qat": "ollama, Gemma 4 26B",
    "cloud-sonnet-5-5": "cloud, Sonnet 5.5",
    "cloud-gemini-3-8-flash": "cloud, Gemini 3.8 Flash",
    "agent-sonnet-5-5": "agent, Sonnet 5.5",
}
# Charts each figure holds: the truth files and truth-sample/STRUCTURE.md.
CHARTS = {
    "S02": ("Figure 3", 4),
    "S03": ("Figure 4", 1),
    "S04": ("Figure 5", 1),
    "S05": ("Figure 6", 2),
    "S06": ("Figure 7", 4),
    "S08": ("Supplementary Figure S2", 1),
    "S10": ("Supplementary Figure S4", 3),
    "S11": ("Supplementary Figure S5", 11),
    "S12": ("Supplementary Figure S6", 5),
    "S13": ("Supplementary Figure S7", 4),
    "S14": ("Supplementary Figure S8", 3),
}
STEP_COLOUR = "#eb6834"  # what the step did
TRUE_COLOUR = "#2a78d6"  # what the figure has
_BOX = re.compile(r"^- chart (\S+), box \[(\d+), (\d+), (\d+), (\d+)\]", re.M)


def uri(image: Image.Image, side: int = 900) -> str:
    image = image.convert("RGB")
    image.thumbnail((side, side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def outline(
    image: Image.Image, boxes: list[tuple[str, list[float]]], colour: str, *, dashed: bool = False
) -> None:
    """Draw *boxes* (label, [x0, y0, x1, y1] in image pixels) on *image*."""
    draw = ImageDraw.Draw(image)
    width = max(4, image.width // 220)
    font = ImageFont.load_default(size=max(18, image.width // 42))
    for label, (x0, y0, x1, y1) in boxes:
        if dashed:
            step = 4 * width
            for x in range(int(x0), int(x1), 2 * step):
                draw.line([(x, y0), (min(x + step, x1), y0)], fill=colour, width=width)
                draw.line([(x, y1), (min(x + step, x1), y1)], fill=colour, width=width)
            for y in range(int(y0), int(y1), 2 * step):
                draw.line([(x0, y), (x0, min(y + step, y1))], fill=colour, width=width)
                draw.line([(x1, y), (x1, min(y + step, y1))], fill=colour, width=width)
        else:
            draw.rectangle([x0, y0, x1, y1], outline=colour, width=width)
        tag = draw.textbbox((0, 0), label, font=font)
        pad = width
        corner = (x1 - (tag[2] - tag[0]) - 3 * pad, y0 + pad) if dashed else (x0 + pad, y0 + pad)
        draw.rectangle(
            [corner[0], corner[1], corner[0] + tag[2] - tag[0] + 2 * pad, corner[1] + tag[3] + 2 * pad],
            fill=colour,
        )
        draw.text((corner[0] + pad, corner[1] + pad // 2), label, fill="#ffffff", font=font)


def split_shot(folder: str) -> Image.Image:
    """A prepared figure with the charts the splitter found drawn on it."""
    image = Image.open(FIRST / folder / "figure.png").convert("RGB")
    text = (FIRST / folder / "figure.txt").read_text(encoding="utf-8")
    boxes = [
        (
            f"chart {m.group(1)}",
            [
                int(m.group(2)) * image.width / 1000,
                int(m.group(3)) * image.height / 1000,
                int(m.group(4)) * image.width / 1000,
                int(m.group(5)) * image.height / 1000,
            ],
        )
        for m in _BOX.finditer(text)
    ]
    outline(image, boxes, STEP_COLOUR)
    return image


def box_shot() -> Image.Image:
    """Figure 7 with the truth's four panels and the boxes the record of a
    reading gives its charts 3 and 4."""
    image = Image.open(FIRST / "pictures_6" / "figure.png").convert("RGB")
    truth = json.loads(
        (ROUND / "truth" / f"{BUNDLE}__pictures_6.json").read_text(encoding="utf-8")
    )
    reading = json.loads(
        (
            ROUND / "runs" / "agent-sonnet-5-5" / BUNDLE / "figure-to-data" / "pictures_6"
            / "figure-to-data.json"
        ).read_text(encoding="utf-8")
    )
    crop_width = max(p["bbox_px"][2] for p in truth["panels"])
    scale = image.width / crop_width
    outline(
        image,
        [(f"panel {p['id']}", [v * scale for v in p["bbox_px"]]) for p in truth["panels"]],
        TRUE_COLOUR,
        dashed=True,
    )
    outline(
        image,
        [
            (f"chart {p['id']} in the record", [v * scale for v in p["bbox_px"]])
            for p in reading["panels"]
            if p["id"] in ("3", "4")
        ],
        STEP_COLOUR,
    )
    return image


def frame_shot() -> Image.Image:
    """The synthetic chart of the end-to-end test with a bar that reaches
    the top tick."""
    import pypdfium2 as pdfium

    sys.path.insert(0, str(Path.cwd()))
    from tests.test_engines.test_figure_data import _BLUE, _bar_chart_pdf

    with tempfile.TemporaryDirectory() as work:
        pdf_path = _bar_chart_pdf(
            Path(work) / "chart.pdf",
            [("A", [(0.3, _BLUE)]), ("B", [(0.55, _BLUE)]), ("C", [(1.0, _BLUE)])],
            printed={"B": "0.55"},
        )
        pdf = pdfium.PdfDocument(pdf_path)
        image = pdf[0].render(scale=3).to_pil().convert("RGB")
        pdf.close()
    # Bar C: x 180 to 210 pt, y 60 to 260 pt from the page's bottom, at 3 px per pt.
    left, top = 90, 80
    image = image.crop((left, top, 690, 790))
    outline(image, [("not read", [540 - left, 120 - top, 630 - left, 720 - top])], STEP_COLOUR)
    return image


def main() -> None:
    by_id = {f["id"]: f for f in PIPELINE["figures"]}
    manifest = json.loads((FIRST / "prepare.json").read_text(encoding="utf-8"))
    found = {f["folder"]: f["charts"] for f in manifest["figures"] if f.get("folder")}
    s05 = by_id["S05"]
    data = {
        "text": TEXT,
        "capture": [
            {
                "name": NAMES[label],
                "before": s05["runs"][label]["score"]["within_5_by_name"],
                "after": s05["runs"][label]["after_fix"]["within_5_by_name"],
            }
            for label in NAMES
        ],
        "split": [
            {
                "id": figure_id,
                "figure": name,
                "has": has,
                "found": found[by_id[figure_id]["folder"]],
            }
            for figure_id, (name, has) in CHARTS.items()
        ],
        "figure7": [
            {
                "name": NAMES[label],
                "scored": by_id["S06"]["runs"][label]["score"]["within_5"],
                "byName": by_id["S06"]["runs"][label]["score"]["within_5_by_name"],
            }
            for label in NAMES
        ],
        "segments": [
            {
                "name": NAMES[label],
                "s03": by_id["S03"]["runs"][label]["values"],
                "s04": by_id["S04"]["runs"][label]["values"],
                "right": by_id["S03"]["runs"][label]["score"]["within_5_by_name"]
                + by_id["S04"]["runs"][label]["score"]["within_5_by_name"],
            }
            for label in NAMES
        ],
        "scorer": [
            {
                "name": NAMES[label],
                "scored": PIPELINE["runs"][label]["against_truth"]["within_5"],
                "byName": PIPELINE["runs"][label]["against_truth"]["within_5_by_name"],
            }
            for label in NAMES
        ],
        "shots": {
            "capture": [
                [
                    uri(Image.open(FIRST / "pictures_5" / "figure.png")),
                    "Figure 6 as the readers got it: two charts on a black background, the axis labels invisible",
                    "As every reader got it.",
                    "Black where the page is white. The axis titles and tick labels, printed in black, are gone.",
                ],
                [
                    uri(Image.open(AGAIN / "pictures_5" / "figure.png")),
                    "Figure 6 after the fix: the same charts on white, with years and cut-off dates on the x axes",
                    "After the fix.",
                    "The image's transparency mask is applied. Years and cut-off dates can be read.",
                ],
            ],
            "splitter": [
                [
                    uri(split_shot("pictures_3"), 700),
                    "Figure 4, one chart of 37 stacked bars, with two boxes drawn on it",
                    "Figure 4: one chart, found as two.",
                    "37 bars share one axis; the cut runs between two of the six blocks.",
                ],
                [
                    uri(split_shot("pictures_6")),
                    "Figure 7, four line panels, with six boxes drawn on it",
                    "Figure 7: four panels, found as six.",
                    "The bottom-left panel is cut across the middle, and a sliver of the last panel is a chart of its own.",
                ],
                [
                    uri(split_shot("pictures_14"), 700),
                    "Supplementary Figure S8, three panels of stacked bars, with eight boxes drawn on it",
                    "Supplementary Figure S8: three panels, found as eight.",
                    "Each panel of 37 bars is cut along its groups of bars.",
                ],
            ],
            "box": [
                [
                    uri(box_shot()),
                    "Figure 7 with the four panels a to d outlined, and two boxes of a reading's record both lying in the bottom-left panel",
                    "Figure 7: where the record puts charts 3 and 4.",
                    "Dashed blue: the figure's four panels. Orange: the boxes the record gives the reading's third and fourth chart. Both lie in panel c; panel d is on the right.",
                ],
            ],
            "frame": [
                [
                    uri(frame_shot(), 520),
                    "A synthetic bar chart with three bars; the tallest reaches the top tick and is outlined",
                    "The synthetic chart of the test.",
                    "The bar that reaches the top tick fills more than 0.9 of the chart's box and is dropped as a frame.",
                ],
            ],
        },
    }
    page = (HERE / "defects_template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page.replace("/*__DATA__*/", payload), encoding="utf-8")
    print(f"{OUT}: {OUT.stat().st_size / 1e6:.1f} MB, {len(TEXT['defects'])} defects")


if __name__ == "__main__":
    main()
