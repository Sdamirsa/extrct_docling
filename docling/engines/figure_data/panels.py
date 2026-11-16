# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Split a figure into its panels (sub-charts).

1. **Gutters.** The background colour is the median of the image border;
   rows (then columns, recursively) whose ink stays near zero for at least
   :data:`GUTTER_FRACTION` of the image side cut the figure into blocks
   (an XY-cut).
2. **Graphic blocks.** A block is a panel when it holds a long straight
   ink run or a large connected component (axes, a plot background, a pie)
   and is not a solid wordless block (a bar of a chart without axis lines);
   text-only blocks
   (legends, shared axis titles, panel letters on their own line) are not,
   and a text block close to exactly one panel (title, side legend) joins it.
3. **Letters.** Single letters a-h / A-H (``(a)`` too) from the words name
   the panels: a panel takes the alphabetically last letter above-left of
   its centre, several panels under one letter become ``a1, a2, ...``.
4. **Grid fit.** When letters and gutters disagree (fewer panels than
   letters), the letters' own grid splits the figure, or the VLM's panel
   boxes do when a box reader is given.

Everything is in work-image pixels.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import numpy as np
from pydantic import BaseModel
from scipy import ndimage

from docling.engines.figure_data.schema import Box, PanelSplit, Word

GUTTER_FRACTION = 0.01
_GUTTER_MAX_INK = 0.002
_INK_DIFF = 40
_MAX_DEPTH = 4
_GRAPHIC_SPAN = 0.3
_GRAPHIC_MIN_SIDE = 0.06
_MIN_PANEL_AREA = 0.02
_MAX_ASPECT = 10.0
_SOLID = 0.85
_LETTER = re.compile(r"^\(?([a-hA-H])\)?\.?$")

BoxReader = Callable[[], list[tuple[str, Box]]]


class PanelBox(BaseModel):
    id: str
    bbox: Box
    letter: str | None = None


class PanelSplitResult(BaseModel):
    panels: list[PanelBox]
    method: str
    letters: list[str] = []
    notes: list[str] = []


def split_panels(
    image: np.ndarray,
    words: list[Word],
    *,
    mode: PanelSplit = "auto",
    box_reader: BoxReader | None = None,
) -> PanelSplitResult:
    """Panels of *image* (H x W x 3, uint8); a single full-image panel when
    nothing splits it."""
    height, width = image.shape[:2]
    full: Box = (0.0, 0.0, float(width), float(height))
    if mode == "off":
        return PanelSplitResult(panels=[PanelBox(id="1", bbox=full)], method="off")
    if mode == "vlm" and box_reader is not None:
        return _from_reader(box_reader, full, "vlm")

    mask = ink_mask(image)
    blocks = _xy_cut(mask, (0, 0, width, height), depth=0)
    graphic = [b for b in blocks if _is_graphic(mask, b, width, height)]
    graphic = [b for b in graphic if _area(b) >= _MIN_PANEL_AREA * width * height]
    # A solid block without text is a bar of a chart drawn without axis
    # lines (the gutters between bars cut it out), not a panel.
    graphic = [
        b
        for b in graphic
        if any(_centre_in(w, b) for w in words) or _ink_density(mask, b) < _SOLID
    ]
    texts = [b for b in blocks if b not in graphic]
    graphic = _attach_text(graphic, texts, width, height)
    letters = [
        (c, w) for c, w in _letters(words) if _heads_a_block(w, graphic, width, height)
    ]
    notes: list[str] = []
    if not graphic:
        return PanelSplitResult(
            panels=[PanelBox(id="1", bbox=full)],
            method="none",
            letters=[c for c, _ in letters],
        )

    named = _with_letters(_name(graphic, letters), dict(letters), width, height)
    unused = {c for c, _ in letters} - {p.letter for p in named if p.letter}
    if len(letters) >= 2 and (unused or len(graphic) < len(letters)):
        notes.append(
            f"letters {''.join(sorted(c for c, _ in letters))} and "
            f"{len(graphic)} gutter block(s) disagree"
        )
        if box_reader is not None:
            result = _from_reader(box_reader, full, "vlm")
            result.notes = notes + result.notes
            return result
        if len(graphic) < len(letters):
            return PanelSplitResult(
                panels=_letter_grid(letters, width, height),
                method="letters",
                letters=[c for c, _ in letters],
                notes=notes,
            )
    return PanelSplitResult(
        panels=named,
        method="gutters" if len(named) > 1 else "single",
        letters=[c for c, _ in letters],
        notes=notes,
    )


def ink_mask(image: np.ndarray) -> np.ndarray:
    """Pixels that differ from the background (the median border colour)."""
    border = np.concatenate(
        [image[0], image[-1], image[:, 0], image[:, -1]], axis=0
    ).astype(int)
    background = np.median(border, axis=0)
    return np.abs(image.astype(int) - background).max(axis=2) > _INK_DIFF


def _xy_cut(mask: np.ndarray, box: tuple[int, int, int, int], depth: int) -> list[Box]:
    x0, y0, x1, y1 = box
    sub = mask[y0:y1, x0:x1]
    if not sub.any():
        return []
    rows = np.flatnonzero(sub.any(axis=1))
    cols = np.flatnonzero(sub.any(axis=0))
    x0, x1 = x0 + int(cols[0]), x0 + int(cols[-1]) + 1
    y0, y1 = y0 + int(rows[0]), y0 + int(rows[-1]) + 1
    if depth >= _MAX_DEPTH:
        return [(float(x0), float(y0), float(x1), float(y1))]
    height, width = mask.shape
    for axis in (1, 0) if depth % 2 == 0 else (0, 1):
        profile = mask[y0:y1, x0:x1].sum(axis=axis)
        side = height if axis == 1 else width
        length = (x1 - x0) if axis == 1 else (y1 - y0)
        runs = _content_runs(
            profile > max(1, _GUTTER_MAX_INK * length),
            max(3, round(GUTTER_FRACTION * side)),
        )
        if len(runs) > 1:
            out: list[Box] = []
            for start, end in runs:
                child = (
                    (x0, y0 + start, x1, y0 + end)
                    if axis == 1
                    else (x0 + start, y0, x0 + end, y1)
                )
                out.extend(_xy_cut(mask, child, depth + 1))
            return out
    return [(float(x0), float(y0), float(x1), float(y1))]


def _content_runs(filled_rows: np.ndarray, min_gap: int) -> list[tuple[int, int]]:
    """Spans of *filled_rows* separated by at least *min_gap* empty entries."""
    filled = np.flatnonzero(filled_rows)
    if filled.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = prev = int(filled[0])
    for index in filled[1:]:
        if index - prev - 1 >= min_gap:
            runs.append((start, prev + 1))
            start = int(index)
        prev = int(index)
    runs.append((start, prev + 1))
    return runs


def _is_graphic(mask: np.ndarray, box: Box, width: int, height: int) -> bool:
    """A chart block holds a long straight ink run (an axis, a frame, a
    filled area) or one large connected component (a pie, a plot
    background); text and legends hold neither. Very elongated blocks
    (a framed legend row) are not panels."""
    x0, y0, x1, y1 = (round(v) for v in box)
    bw, bh = x1 - x0, y1 - y0
    if bw <= 0 or bh <= 0 or max(bw / bh, bh / bw) > _MAX_ASPECT:
        return False
    sub = mask[y0:y1, x0:x1]
    min_w = max(_GRAPHIC_SPAN * bw, _GRAPHIC_MIN_SIDE * width)
    min_h = max(_GRAPHIC_SPAN * bh, _GRAPHIC_MIN_SIDE * height)
    if _longest_run(sub) >= min_h or _longest_run(sub.T) >= min_w:
        return True
    labels, count = ndimage.label(sub)
    for sl in ndimage.find_objects(labels) if count else []:
        if sl is None:
            continue
        if sl[1].stop - sl[1].start >= min_w or sl[0].stop - sl[0].start >= min_h:
            return True
    return False


def _longest_run(mask: np.ndarray) -> int:
    """Longest run of ink down any column of *mask*."""
    padded = np.zeros((mask.shape[0] + 2, mask.shape[1]), dtype=np.int8)
    padded[1:-1] = mask
    edges = np.diff(padded, axis=0)
    starts = np.argwhere(edges == 1)
    ends = np.argwhere(edges == -1)
    if starts.size == 0:
        return 0
    order_s = np.lexsort((starts[:, 0], starts[:, 1]))
    order_e = np.lexsort((ends[:, 0], ends[:, 1]))
    return int((ends[order_e, 0] - starts[order_s, 0]).max())


def _attach_text(
    graphic: list[Box], texts: list[Box], width: int, height: int
) -> list[Box]:
    """Grow a panel by a text block next to it (its title, axis title or
    side legend): the block lies within a small gap above, below or beside
    exactly one panel, or much closer to one than to any other."""
    out = list(graphic)
    for text in texts:
        gaps: list[tuple[float, int]] = []
        reach = 3 * GUTTER_FRACTION * max(width, height)
        for index, g in enumerate(out):
            x_overlap = _overlap(text, g, 0) / max(text[2] - text[0], 1.0)
            y_overlap = _overlap(text, g, 1) / max(text[3] - text[1], 1.0)
            vertical_gap = max(g[1] - text[3], text[1] - g[3])
            side_gap = max(g[0] - text[2], text[0] - g[2])
            if x_overlap >= 0.5 and y_overlap >= 0.5:
                gaps.append((0.0, index))
            elif x_overlap >= 0.6 and 0 <= vertical_gap <= reach:
                gaps.append((vertical_gap, index))
            elif y_overlap >= 0.5 and 0 <= side_gap <= reach:
                gaps.append((side_gap, index))
        gaps.sort()
        if not gaps or (len(gaps) > 1 and gaps[1][0] < 2 * gaps[0][0] + 2):
            continue
        g = out[gaps[0][1]]
        out[gaps[0][1]] = (
            min(g[0], text[0]),
            min(g[1], text[1]),
            max(g[2], text[2]),
            max(g[3], text[3]),
        )
    return out


def _letters(words: list[Word]) -> list[tuple[str, Word]]:
    found: dict[str, Word] = {}
    for word in words:
        match = _LETTER.match(word.text.strip())
        if match is None:
            continue
        letter = match.group(1).lower()
        if letter not in found or (word.cy, word.cx) < (
            found[letter].cy,
            found[letter].cx,
        ):
            found[letter] = word
    return sorted(found.items())


def _heads_a_block(word: Word, blocks: list[Box], width: int, height: int) -> bool:
    """A panel letter sits at the top-left of a panel (inside or just
    outside it); a single-letter category label under an axis does not."""
    reach = 6 * GUTTER_FRACTION * max(width, height)
    return any(
        b[0] - reach <= word.cx <= b[0] + 0.5 * (b[2] - b[0])
        and b[1] - reach <= word.cy <= b[1] + 0.2 * (b[3] - b[1])
        for b in blocks
    )


def _name(blocks: list[Box], letters: list[tuple[str, Word]]) -> list[PanelBox]:
    ordered = _reading_order(blocks)
    owners: list[str | None] = []
    for block in ordered:
        cx, cy = (block[0] + block[2]) / 2, (block[1] + block[3]) / 2
        above_left = [c for c, w in letters if w.cx <= cx and w.cy <= cy]
        owners.append(max(above_left) if above_left else None)
    if len(ordered) == 1 and not letters:
        return [PanelBox(id="1", bbox=ordered[0])]
    # OCR often loses the "a" in the very corner: panels before the first
    # letter found belong to the letter before it.
    if letters and letters[0][0] not in "aA":
        first = chr(ord(letters[0][0]) - 1)
        owners = [first if o is None else o for o in owners]
    panels: list[PanelBox] = []
    for index, (block, owner) in enumerate(zip(ordered, owners)):
        if owner is None:
            panels.append(PanelBox(id=str(index + 1), bbox=block))
            continue
        siblings = [i for i, o in enumerate(owners) if o == owner]
        panel_id = (
            owner if len(siblings) == 1 else f"{owner}{siblings.index(index) + 1}"
        )
        panels.append(PanelBox(id=panel_id, bbox=block, letter=owner))
    return panels


def _with_letters(
    panels: list[PanelBox], letters: dict[str, Word], width: int, height: int
) -> list[PanelBox]:
    """Grow a panel named by a letter of its own to take in that letter when
    it sits just outside its top-left corner."""
    reach = 6 * GUTTER_FRACTION * max(width, height)
    for panel in panels:
        word = letters.get(panel.id)
        if word is None:
            continue
        x0, y0, x1, y1 = panel.bbox
        if x0 - reach <= word.bbox[0] <= x1 and y0 - reach <= word.bbox[1] <= y0:
            panel.bbox = (min(x0, word.bbox[0]), word.bbox[1], x1, y1)
    return panels


def _reading_order(blocks: list[Box]) -> list[Box]:
    """Rows of blocks top to bottom (a block joins a row when it overlaps
    the row's vertical span by half its height), each row left to right."""
    rows: list[list[Box]] = []
    for block in sorted(blocks, key=lambda b: b[1]):
        for row in rows:
            top = min(b[1] for b in row)
            bottom = max(b[3] for b in row)
            overlap = min(bottom, block[3]) - max(top, block[1])
            if overlap >= 0.5 * (block[3] - block[1]):
                row.append(block)
                break
        else:
            rows.append([block])
    return [b for row in rows for b in sorted(row, key=lambda b: b[0])]


def _letter_grid(
    letters: list[tuple[str, Word]], width: int, height: int
) -> list[PanelBox]:
    """Cells spanned by the panel letters: rows of letters at the same
    height, each letter's cell reaching to the next letter on the right and
    to the next row."""
    tol = 0.05 * height
    rows: list[list[tuple[str, Word]]] = []
    for letter in sorted(letters, key=lambda lw: lw[1].cy):
        if rows and abs(rows[-1][0][1].cy - letter[1].cy) <= tol:
            rows[-1].append(letter)
        else:
            rows.append([letter])
    panels: list[PanelBox] = []
    for r, row in enumerate(rows):
        top = min(w.bbox[1] for _, w in row)
        bottom = min(w.bbox[1] for _, w in rows[r + 1]) if r + 1 < len(rows) else height
        row.sort(key=lambda lw: lw[1].cx)
        for i, (char, word) in enumerate(row):
            right = row[i + 1][1].bbox[0] if i + 1 < len(row) else width
            panels.append(
                PanelBox(
                    id=char,
                    bbox=(
                        max(0.0, word.bbox[0]),
                        max(0.0, top),
                        float(right),
                        float(bottom),
                    ),
                    letter=char,
                )
            )
    return panels


def _from_reader(reader: BoxReader, full: Box, method: str) -> PanelSplitResult:
    boxes = reader()
    width, height = full[2], full[3]
    panels = [
        PanelBox(
            id=panel_id,
            bbox=(
                max(0.0, min(b[0], b[2])),
                max(0.0, min(b[1], b[3])),
                min(width, max(b[0], b[2])),
                min(height, max(b[1], b[3])),
            ),
            letter=panel_id if _LETTER.match(panel_id) else None,
        )
        for panel_id, b in boxes
        if abs(b[2] - b[0]) > 0.05 * width and abs(b[3] - b[1]) > 0.05 * height
    ]
    if not panels:
        return PanelSplitResult(
            panels=[PanelBox(id="1", bbox=full)],
            method=method,
            notes=["VLM returned no usable panel box"],
        )
    return PanelSplitResult(panels=panels, method=method)


def _ink_density(mask: np.ndarray, box: Box) -> float:
    x0, y0, x1, y1 = (round(v) for v in box)
    sub = mask[y0:y1, x0:x1]
    return float(sub.mean()) if sub.size else 0.0


def _centre_in(word: Word, box: Box) -> bool:
    return box[0] <= word.cx <= box[2] and box[1] <= word.cy <= box[3]


def _overlap(a: Box, b: Box, axis: int) -> float:
    """Overlap of *a* and *b* along x (*axis* 0) or y (1)."""
    return max(0.0, min(a[2 + axis], b[2 + axis]) - max(a[axis], b[axis]))


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
