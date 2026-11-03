# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Amir Engine — high-level wrappers over Docling for PDF → structured pipelines.

This subpackage is project-local (not upstream Docling). Phase 1 ships
:class:`PdfEngine`, a thin facade around :class:`docling.document_converter.DocumentConverter`
that returns a validated :class:`PdfConversionOutput` Pydantic model.
"""

from docling.engines.artifacts import ArtifactPaths, ArtifactsError, write_artifacts
from docling.engines.chunker import ChunkerError, ChunkPaths, write_chunks
from docling.engines.compare_pipelines import ComparisonResult, run_comparison
from docling.engines.html_export import rebuild_document_html, write_document_html
from docling.engines.pdf_engine import PdfEngine
from docling.engines.picture_filter import (
    DEFAULT_NOISE_CLASSES,
    PictureNoiseFlag,
    classify_pictures,
)
from docling.engines.run_snapshot import (
    ENGINE_VERSION,
    engine_provenance,
    write_run_snapshot,
)
from docling.engines.schemas import (
    PageSummary,
    PdfConversionOutput,
    PdfEngineError,
    SourceKind,
)
from docling.engines.structured_outputs import (
    StructuredOutputPaths,
    StructuredOutputsError,
    write_structured_outputs,
)
from docling.engines.visualizer import PreviewError, render_html_preview

__all__ = [
    "DEFAULT_NOISE_CLASSES",
    "ENGINE_VERSION",
    "ArtifactPaths",
    "ArtifactsError",
    "ChunkPaths",
    "ChunkerError",
    "ComparisonResult",
    "PageSummary",
    "PdfConversionOutput",
    "PdfEngine",
    "PdfEngineError",
    "PictureNoiseFlag",
    "PreviewError",
    "SourceKind",
    "StructuredOutputPaths",
    "StructuredOutputsError",
    "classify_pictures",
    "engine_provenance",
    "rebuild_document_html",
    "render_html_preview",
    "run_comparison",
    "write_artifacts",
    "write_chunks",
    "write_document_html",
    "write_run_snapshot",
    "write_structured_outputs",
]
