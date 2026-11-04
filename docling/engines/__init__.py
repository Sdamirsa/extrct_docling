# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Amir Engine — high-level wrappers over Docling for PDF → structured pipelines.

This subpackage is project-local (not upstream Docling). Phase 1 ships
:class:`PdfEngine`, a thin facade around :class:`docling.document_converter.DocumentConverter`
that returns a validated :class:`PdfConversionOutput` Pydantic model.
"""

from docling.engines.artifacts import ArtifactPaths, ArtifactsError, write_artifacts
from docling.engines.chunker import ChunkerError, ChunkPaths, write_chunks
from docling.engines.compare_pipelines import (
    ComparisonResult,
    build_full_page_vlm_engine,
    run_comparison,
)
from docling.engines.export_check import (
    BundleCheck,
    check_bundle,
    write_bundle_check,
)
from docling.engines.html_export import rebuild_document_html, write_document_html
from docling.engines.pdf_engine import PdfEngine, resolve_pdf_dir
from docling.engines.picture_filter import (
    DEFAULT_NOISE_CLASSES,
    PictureNoiseFlag,
    classify_pictures,
)
from docling.engines.run_snapshot import (
    ENGINE_VERSION,
    build_run_snapshot,
    engine_provenance,
    write_run_snapshot,
)
from docling.engines.schemas import (
    PageSummary,
    PdfConversionOutput,
    PdfEngineError,
    SourceKind,
)
from docling.engines.serializers import (
    build_serializer_provider,
    export_markdown,
    markdown_params,
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
    "BundleCheck",
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
    "build_full_page_vlm_engine",
    "build_run_snapshot",
    "build_serializer_provider",
    "check_bundle",
    "classify_pictures",
    "engine_provenance",
    "export_markdown",
    "markdown_params",
    "rebuild_document_html",
    "render_html_preview",
    "resolve_pdf_dir",
    "run_comparison",
    "write_artifacts",
    "write_bundle_check",
    "write_chunks",
    "write_document_html",
    "write_run_snapshot",
    "write_structured_outputs",
]
