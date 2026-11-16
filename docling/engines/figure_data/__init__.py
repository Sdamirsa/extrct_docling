# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Figure-to-data: read the numbers behind a chart into ``extrct.figure-data/1``.

``off`` · ``simple`` (one VLM call → table) · ``measured`` (panels → evidence
→ grounded VLM read → geometry → verify), local models through Ollama only.
Contract: ``.claude/reference/figure-data/DESIGN.md``. Only the schema is
imported here, so the serializers can use its meta key without a cycle.
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
