# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Figure-to-data: read the numbers behind a chart into ``extrct.figure-data/1``.

A step of its own on a finished bundle (:mod:`.step`): prepare each chart
candidate (:mod:`.prepare`), read it with one of three methods
(:mod:`.methods`: ``ollama``, a local model inside the measured engine;
``cloud``, one call to a cloud model's API; ``agent``, one agent session
per figure), embed the reading at the figure (:mod:`.publish`).
Design: ``.claude/reference/figure-data/STANDALONE-STEP.md``. Only the
schema is imported here, so the serializers can use its meta key without a
cycle.
"""

from docling.engines.figure_data.schema import (
    CHART_DATA_META_KEY,
    SCHEMA_ID,
    ChartData,
    FigureDataOptions,
    FigureDataResult,
)

__all__ = [
    "CHART_DATA_META_KEY",
    "SCHEMA_ID",
    "ChartData",
    "FigureDataOptions",
    "FigureDataResult",
]
