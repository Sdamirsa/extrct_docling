# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Snap a model-pointed bar end to the pixel edge it points at (v1: bars
and stacked-bar segments in raster figures).

Along the bar's direction, a few pixels either side of the pointed
centreline (an error bar runs down the centre), the colour profile is
searched within a window around the pointed position for the strongest
colour change whose inner side is a uniform run (the bar or segment fill).
The edge's position then goes through the axis map like the pointer did.
"""

from __future__ import annotations

import numpy as np

from docling.engines.figure_data.schema import Orientation

_MIN_STEP = 60
_MIN_RUN = 3


def refine_edge(
    image: np.ndarray,
    x: float,
    y: float,
    orientation: Orientation,
    *,
    window: float,
    inward: int,
) -> float | None:
    """The bar edge nearest the pointed ``(x, y)`` along the value axis
    (y for vertical bars, x for horizontal), or None when no clear edge is
    within *window* pixels. *inward* is +1 when the bar lies at larger
    coordinates than its end (a vertical bar's top: the fill is below),
    -1 otherwise."""
    height, width = image.shape[:2]
    vertical = orientation == "vertical"
    centre = round(x if vertical else y)
    pos = y if vertical else x
    limit = height if vertical else width
    lo = max(0, round(pos - window))
    hi = min(limit - 1, round(pos + window))
    if hi - lo < 2 * _MIN_RUN:
        return None
    offset = max(2, round(0.004 * (width if vertical else height)))
    across = [
        c
        for c in (
            centre - 2 * offset,
            centre - offset,
            centre + offset,
            centre + 2 * offset,
        )
        if 0 <= c < (width if vertical else height)
    ]
    if not across:
        return None
    strip = (
        image[lo : hi + 1, across].astype(int)
        if vertical
        else image[across, lo : hi + 1].astype(int).transpose(1, 0, 2)
    )
    profile = np.median(strip, axis=1)
    steps = np.abs(np.diff(profile, axis=0)).sum(axis=1)
    best: tuple[float, int] | None = None
    for index in np.argsort(-steps):
        if steps[index] < _MIN_STEP:
            break
        inner = (
            profile[index + 1 : index + 1 + _MIN_RUN]
            if inward > 0
            else profile[max(0, index + 1 - _MIN_RUN) : index + 1]
        )
        if len(inner) < _MIN_RUN or np.ptp(inner, axis=0).max() > 25:
            continue
        distance = abs(lo + index + 0.5 - pos)
        score = steps[index] / (1 + distance / max(window, 1.0))
        if best is None or score > best[0]:
            best = (float(score), int(index))
    if best is None:
        return None
    return lo + best[1] + 0.5
