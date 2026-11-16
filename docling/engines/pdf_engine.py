# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""High-level PDF conversion engine (Phase 1 of the Amir Engine build)."""

from __future__ import annotations

import contextlib
import datetime as _dt
import itertools
import logging
import re
import shutil
import sys
import unicodedata
from collections.abc import Collection, Iterator, Sequence
from pathlib import Path, PurePath, PurePosixPath
from typing import Any, Optional

from docling_core.types.doc import DoclingDocument, ImageRefMode

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    GraniteVisionTableStructureOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.engines.artifacts import IMAGES_SUBDIR, crop_stem, write_artifacts
from docling.engines.chunker import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOKENIZER,
    write_chunks,
)
from docling.engines.export_check import (
    CHECK_FILENAME,
    check_bundle,
    write_bundle_check,
)
from docling.engines.figure_data.evidence import read_figure_rows
from docling.engines.figure_data.pipeline import FIGURE_DATA_DIRNAME, read_document
from docling.engines.figure_data.schema import FigureDataOptions
from docling.engines.figure_typing import (
    BIOMEDCLIP_REPO,
    FigureTyper,
    type_pictures,
)
from docling.engines.html_export import write_document_html
from docling.engines.picture_filter import (
    DEFAULT_NOISE_CLASSES,
    DEFAULT_REPEAT_THRESHOLD,
    IMAGING_FIGURE_TYPES,
    IMAGING_VETO_CONFIDENCE,
    PictureNoiseFlag,
    classify_pictures,
)
from docling.engines.run_snapshot import (
    RUN_JSON_FILENAME,
    build_run_snapshot,
    engine_provenance,
    read_run_record,
    write_run_snapshot,
)
from docling.engines.schemas import (
    PageSummary,
    PdfConversionOutput,
    PdfEngineError,
    RelatedDocument,
    SourceKind,
)
from docling.engines.serializers import export_markdown
from docling.engines.structure import (
    STRUCTURE_FILENAME,
    STRUCTURE_VERSION,
    DocumentRole,
    quality_report,
    structure_document,
    write_structure,
)
from docling.engines.structured_outputs import write_structured_outputs
from docling.engines.text_repair import (
    attach_table_pdf_text,
    pdf_page_words,
    repair_ligature_splits,
    strip_vlm_stop_tokens,
)
from docling.engines.validation import validate_pdf_source
from docling.engines.visualizer import embed_html_images, render_html_preview
from docling.engines.vlm_specs import (
    PictureDescriptionEngine,
    PictureDescriptionPreset,
    build_picture_description_options,
)
from docling.exceptions import ConversionError

_log = logging.getLogger(__name__)

_PLACEHOLDER = "<!-- image -->"


class PdfEngine:
    """Thin facade over :class:`DocumentConverter` for PDF inputs.

    Returns a :class:`PdfConversionOutput` with normalised status, page
    summaries, error list, and the markdown export. The raw upstream
    :class:`ConversionResult` is preserved on the output for callers that
    need to drop down to lower-level APIs.
    """

    def __init__(
        self,
        converter: Optional[DocumentConverter] = None,
        *,
        with_page_images: bool = False,
        embed_images: bool = True,
        link_images: bool = True,
        images_scale: float = 1.5,
        save_artifacts: bool = True,
        chunk_tokenizer: str = DEFAULT_TOKENIZER,
        chunk_max_tokens: int = DEFAULT_MAX_TOKENS,
        granite_vision_tables: bool = True,
        filter_noise_pictures: bool = True,
        noise_picture_classes: frozenset[str] = DEFAULT_NOISE_CLASSES,
        noise_repeat_threshold: int = DEFAULT_REPEAT_THRESHOLD,
        picture_description: PictureDescriptionPreset | None = "granite_vision_4b",
        picture_description_engine: PictureDescriptionEngine = "default",
        picture_area_threshold: float = 0.03,
        figure_types: bool = True,
        figure_data: FigureDataOptions | None = None,
    ) -> None:
        """Initialise the engine.

        Parameters
        ----------
        converter
            Optional pre-built :class:`DocumentConverter` (advanced use).
            When provided, the other image flags are ignored.
        with_page_images
            When True, retain rendered page images so the HTML viewer
            (``make_html_preview=True``) can be built later. Redundant when
            ``save_artifacts=True`` (which forces this on internally).
        embed_images
            When True (default), additionally writes a second
            ``<stem>.embedded.md`` next to the primary markdown, with image
            placeholders replaced by base64 data URIs — a standalone file you
            can share without the surrounding ``images/`` folder — and
            ``<stem>.html``, the same content as a standalone HTML page with
            per-block provenance and a JSON manifest for agents (see
            :mod:`docling.engines.html_export`).
        link_images
            When True (default), the primary ``<stem>.md`` swaps each image
            placeholder for a relative ``![](images/picture_NNN.png)``
            reference so markdown viewers render the figures inline.
            Requires ``save_artifacts=True`` for the image files to exist.
        images_scale
            Scale factor applied when generating page or picture images.
        save_artifacts
            When True (default) and ``output_dir`` is given to :meth:`convert`,
            writes ``document.json``, ``nodes.jsonl``, ``chunks.jsonl``,
            ``run.json`` and extracted figure/table images under the per-PDF
            output folder. Implicitly enables page + picture image generation.
        chunk_tokenizer
            HuggingFace repo for the HybridChunker tokenizer
            (default: ``sentence-transformers/all-MiniLM-L6-v2``). Override
            when targeting a different downstream model.
        chunk_max_tokens
            Max tokens per chunk (default 512, matches the MiniLM tokenizer's
            ``model_max_length``). Bump alongside ``chunk_tokenizer`` when
            switching to a larger-context embedding/chat model.
        granite_vision_tables
            When True (default), swap the default TableFormer to the
            Granite-Vision VLM-based table-structure model
            (``ibm-granite/granite-vision-4.1-4b``). Higher-quality on
            messy tables; shares weights with the default figure-description
            preset (~13 GB download on first use) and adds a few seconds
            per table. Set False to fall back to TableFormer.
        filter_noise_pictures
            When True (default), runs the picture-noise filter
            (:func:`classify_pictures`) over each conversion. Pictures
            classified as logos/watermarks or repeated across many pages get
            tagged with ``is_noise=True`` in ``figures.jsonl`` and their
            placeholders are replaced by ``<!-- noise picture: reason -->``
            comments in both markdown files (``<stem>.html`` keeps them,
            marked ``data-noise``). A classifier label is overruled when
            figure typing confidently calls the picture a medical image
            (:data:`~docling.engines.picture_filter.IMAGING_FIGURE_TYPES`).
            Auto-enables the picture classifier.
        noise_picture_classes
            Classifier labels considered noise (default:
            :data:`~docling.engines.picture_filter.DEFAULT_NOISE_CLASSES`).
        noise_repeat_threshold
            A picture whose rounded bbox repeats on at least this many pages
            is flagged as noise even without a classifier hit (default 3).
            The same count makes a short line repeated in the top or bottom
            margin a page header / footer
            (:func:`~docling.engines.structure.structure_document`).
        picture_description
            VLM picture-description preset. Default ``"granite_vision_4b"``
            (``ibm-granite/granite-vision-4.1-4b``). Other values:
            ``"granite_vision"`` (3.3-2b — smaller/faster), ``"smolvlm"``,
            ``"pixtral"``, ``"qwen25_vl_3b"``, or ``None`` to skip captions
            entirely. Captions land in ``figures.jsonl[*].vlm_caption``.
            First use downloads the model (4.1-4b ≈ 8 GB).
        picture_description_engine
            Inference runtime for the picture-description VLM. Values:
            ``"default"`` (let Docling pick — falls back to transformers
            when vLLM isn't installed; this is the default), ``"vllm"``
            (force vLLM — requires it installed), ``"transformers"`` (force
            transformers). Ignored when ``picture_description`` is None.
        picture_area_threshold
            Smallest picture, as a fraction of the page area, that gets a VLM
            description (default 0.03; Docling's 0.05 left real charts at
            4-5 % of the page and an ECG at 3.9 % without one).
        figure_types
            When True (default), types every picture with BiomedCLIP into a
            scientific/medical taxonomy (``ct``, ``angiography``, ``ecg``,
            ``kaplan_meier``... see
            :data:`~docling.engines.figure_typing.FIGURE_TYPES`). Lands in
            ``figures.jsonl[*].figure_type`` and on ``PictureItem.meta``
            (``amir__figure_type``) in ``document.json``. Needs picture
            images (``save_artifacts`` or ``embed_images``) and the
            ``models-vlm-inline`` extra (open-clip-torch); ~0.8 GB GPU.
        figure_data
            Read the numbers behind chart figures (``mode`` ``simple`` or
            ``measured``) with a local VLM through Ollama
            (:mod:`docling.engines.figure_data`); None or mode ``off``
            (default) skips it. Records land in ``figures.jsonl``
            (``chart_data``), on ``PictureItem.meta`` and, above the
            confidence threshold, as a marked table in the markdown.
            Needs ``save_artifacts`` (it reads the crops).
        """
        self._image_scale = images_scale
        self._embed_images = embed_images
        self._link_images = link_images
        self._save_artifacts = save_artifacts
        self._chunk_tokenizer = chunk_tokenizer
        self._chunk_max_tokens = chunk_max_tokens
        self._granite_vision_tables = granite_vision_tables
        self._filter_noise_pictures = filter_noise_pictures
        self._noise_picture_classes = noise_picture_classes
        self._noise_repeat_threshold = noise_repeat_threshold
        self._picture_description = picture_description
        self._picture_description_engine = picture_description_engine
        self._figure_data = (
            figure_data
            if figure_data is not None and figure_data.mode != "off"
            else None
        )
        self._engine_config = {
            "with_page_images": with_page_images,
            "embed_images": embed_images,
            "link_images": link_images,
            "images_scale": images_scale,
            "save_artifacts": save_artifacts,
            "chunk_tokenizer": chunk_tokenizer,
            "chunk_max_tokens": chunk_max_tokens,
            "granite_vision_tables": granite_vision_tables,
            "filter_noise_pictures": filter_noise_pictures,
            "noise_picture_classes": sorted(noise_picture_classes),
            "noise_repeat_threshold": noise_repeat_threshold,
            "noise_imaging_veto": {
                "figure_types": sorted(IMAGING_FIGURE_TYPES),
                "min_confidence": IMAGING_VETO_CONFIDENCE,
            }
            if figure_types
            else None,
            "picture_description": picture_description,
            "picture_description_engine": picture_description_engine
            if picture_description
            else None,
            "picture_area_threshold": picture_area_threshold
            if picture_description
            else None,
            "figure_types": BIOMEDCLIP_REPO if figure_types else None,
            "figure_data": self._figure_data.model_dump(mode="json")
            if self._figure_data is not None
            else None,
            "converter_supplied": converter is not None,
        }
        self._figure_typer = FigureTyper() if figure_types else None
        engine_provenance()
        if converter is not None:
            self._converter = converter
            self._pipeline_options: PdfPipelineOptions | None = None
            return

        need_page_images = with_page_images or save_artifacts
        need_picture_images = embed_images or save_artifacts
        if need_page_images or need_picture_images:
            self._pipeline_options = PdfPipelineOptions(
                generate_page_images=need_page_images,
                generate_picture_images=need_picture_images,
                images_scale=images_scale,
            )
        else:
            self._pipeline_options = PdfPipelineOptions()

        if granite_vision_tables:
            self._pipeline_options.table_structure_options = (
                GraniteVisionTableStructureOptions()
            )

        if filter_noise_pictures:
            self._pipeline_options.do_picture_classification = True

        if picture_description is not None:
            description_options = build_picture_description_options(
                picture_description, engine=picture_description_engine
            )
            description_options.picture_area_threshold = picture_area_threshold
            self._pipeline_options.do_picture_description = True
            self._pipeline_options.picture_description_options = description_options

        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self._pipeline_options
                )
            },
        )

    def engine_config(self, *, make_html_preview: bool) -> dict[str, Any]:
        """The ``engine_config`` block of the ``run.json`` this engine writes
        for a conversion with *make_html_preview*."""
        return {**self._engine_config, "make_html_preview": make_html_preview}

    def convert(
        self,
        source: str | Path,
        *,
        output_dir: Path | None = None,
        pdf_dir: Path | None = None,
        max_num_pages: int | None = None,
        make_html_preview: bool = False,
        document_role: DocumentRole = "manuscript",
        related: Sequence[RelatedDocument] = (),
    ) -> PdfConversionOutput:
        """Convert a single PDF from a local path or URL.

        Parameters
        ----------
        source
            Path to a local ``.pdf`` file or an ``http(s)://`` URL.
        output_dir
            If given, writes the bundle to ``<output_dir>/<stem>/`` (see
            :func:`resolve_pdf_dir`): ``<stem>.md`` and, per the engine's
            flags, the other files of the bundle.
        pdf_dir
            Write the bundle to this folder instead of the one resolved under
            ``output_dir`` — for a caller that resolves the folders of a whole
            batch up-front, as the ``amir-batch`` CLI does.
        max_num_pages
            Optional cap on the number of pages to convert.
        document_role
            ``"supplement"`` when the PDF is supplementary material of a
            manuscript; recorded in ``run.json`` and on every element of
            ``<stem>.html``.
        related
            The PDFs this one belongs with (the manuscript of a supplement,
            the supplements of a manuscript), recorded in ``run.json``.

        After the conversion the structure pass settles labels, heading
        levels and caption links (:mod:`docling.engines.structure`), and the
        quality report counts what came out: a blocking warning (the text
        packed into a few blocks, no text at all) is added to ``errors`` as
        component ``quality`` and turns ``status`` into PARTIAL_SUCCESS.

        A failing step after the conversion (an export, the chunker, the
        check...) is recorded in ``errors`` with its component, and the next
        step still runs; ``run.json`` is written last and lists them all.
        """
        if make_html_preview and output_dir is None and pdf_dir is None:
            raise ValueError("make_html_preview=True requires output_dir to be set.")
        kind, normalised = validate_pdf_source(source)
        _log.info("PdfEngine: converting %s (%s)", normalised, kind.value)

        started_at = _dt.datetime.now(_dt.timezone.utc)
        try:
            result: ConversionResult = self._converter.convert(
                normalised,
                raises_on_error=False,
                max_num_pages=max_num_pages
                if max_num_pages is not None
                else sys.maxsize,
            )
        except ConversionError as exc:
            _log.exception("PdfEngine: conversion raised ConversionError")
            return PdfConversionOutput(
                status=ConversionStatus.FAILURE,
                source=normalised,
                source_kind=kind,
                errors=[
                    PdfEngineError(component="DocumentConverter", message=str(exc))
                ],
            )
        finished_at = _dt.datetime.now(_dt.timezone.utc)

        output = self._build_output(result, kind=kind, normalised=normalised)
        if not output.succeeded:
            return output

        local_pdf = Path(normalised) if kind == SourceKind.LOCAL_PATH else None
        doc = result.document
        errors = output.errors
        # Before every export. A URL source has no local file to read.
        with _step(errors, "vlm_stop_tokens"):
            strip_vlm_stop_tokens(doc)
        if local_pdf is not None:
            with _step(errors, "ligature_repair"):
                repair_ligature_splits(doc, pdf_page_words(local_pdf))
            with _step(errors, "table_pdf_text"):
                attach_table_pdf_text(doc, local_pdf)
        with _step(errors, "structure"):
            output.structure = structure_document(
                doc,
                pdf_path=local_pdf,
                document_role=document_role,
                repeat_threshold=self._noise_repeat_threshold,
            )
        with _step(errors, "quality"):
            output.quality = quality_report(doc)
            for warning in output.quality.blocking:
                errors.append(
                    PdfEngineError(
                        component="quality",
                        message=f"{warning.code}: {warning.detail}",
                    )
                )
                output.status = ConversionStatus.PARTIAL_SUCCESS
        with _step(errors, "export_to_markdown"):
            output.markdown = export_markdown(doc, image_mode=ImageRefMode.PLACEHOLDER)

        if self._figure_typer is not None:
            with _step(errors, "figure_typing"):
                typed = type_pictures(result, self._figure_typer)
                _log.info("PdfEngine: typed %d picture(s) with BiomedCLIP", typed)

        if pdf_dir is None and output_dir is not None:
            pdf_dir = resolve_pdf_dir(
                output_dir,
                result.input.file.name,
                file_size=result.input.filesize,
                binary_hash=result.input.document_hash or None,
            )
        if pdf_dir is not None:
            self._write_bundle(
                result,
                output,
                pdf_dir,
                local_pdf=local_pdf,
                started_at=started_at,
                finished_at=finished_at,
                make_html_preview=make_html_preview,
                document_role=document_role,
                related=related,
            )
        return output

    def _write_bundle(
        self,
        result: ConversionResult,
        output: PdfConversionOutput,
        pdf_dir: Path,
        *,
        local_pdf: Path | None,
        started_at: _dt.datetime,
        finished_at: _dt.datetime,
        make_html_preview: bool,
        document_role: DocumentRole,
        related: Sequence[RelatedDocument],
    ) -> None:
        doc = result.document
        errors = output.errors
        pdf_dir.mkdir(parents=True, exist_ok=True)
        _remove_bundle_files(pdf_dir)
        output.output_dir = pdf_dir

        noise_flags: list[PictureNoiseFlag] = []
        if self._filter_noise_pictures:
            with _step(errors, "picture_filter"):
                noise_flags = classify_pictures(
                    result,
                    noise_classes=self._noise_picture_classes,
                    repeat_threshold=self._noise_repeat_threshold,
                )

        if self._save_artifacts:
            with _step(errors, "artifacts"):
                artifacts = write_artifacts(result, pdf_dir)
                output.document_json = artifacts.document_json
                output.nodes_jsonl = artifacts.nodes_jsonl
                output.picture_images = artifacts.picture_images
                output.table_images = artifacts.table_images
            if output.structure is not None:
                with _step(errors, "structure"):
                    output.structure_json = write_structure(pdf_dir, output.structure)
            if self._figure_data is not None and output.document_json is not None:
                # Before the chunker and the exports: they show the tables.
                with _step(errors, "figure_data"):
                    if read_document(
                        doc,
                        pdf_dir,
                        picture_images=output.picture_images,
                        noise_flags=noise_flags,
                        pdf_path=local_pdf,
                        options=self._figure_data,
                    ):
                        doc.save_as_json(output.document_json)
                        output.markdown = export_markdown(
                            doc, image_mode=ImageRefMode.PLACEHOLDER
                        )
            with _step(errors, "chunker"):
                output.chunks_jsonl = write_chunks(
                    result,
                    pdf_dir,
                    tokenizer_repo=self._chunk_tokenizer,
                    max_tokens=self._chunk_max_tokens,
                ).chunks_jsonl
            with _step(errors, "structured_outputs"):
                structured = write_structured_outputs(
                    result,
                    pdf_dir,
                    picture_image_paths=output.picture_images,
                    table_image_paths=output.table_images,
                    picture_noise_flags=noise_flags,
                )
                output.tables_jsonl = structured.tables_jsonl
                output.figures_jsonl = structured.figures_jsonl

        if output.markdown is not None:
            with _step(errors, "markdown"):
                linked = (
                    [p.relative_to(pdf_dir).as_posix() for p in output.picture_images]
                    if self._link_images
                    else []
                )
                markdown = _link_picture_placeholders(
                    output.markdown, linked, noise_flags
                )
                output.markdown = markdown
                target = pdf_dir / f"{pdf_dir.name}.md"
                target.write_text(markdown, encoding="utf-8")
                output.markdown_path = target
                _log.info("PdfEngine: wrote markdown to %s", target)

        if self._embed_images:
            with _step(errors, "export_to_markdown_embedded"):
                output.markdown_embedded_path = _write_embedded_markdown(
                    doc, pdf_dir, noise_flags
                )

        if make_html_preview:
            with _step(errors, "visualizer"):
                preview = render_html_preview(
                    result,
                    pdf_dir,
                    image_scale=self._image_scale,
                    noise_flags=noise_flags,
                    chunks_jsonl=output.chunks_jsonl,
                )
                output.preview_html = preview
                if self._embed_images:
                    output.preview_html_embedded = embed_html_images(preview)

        def snapshot(*, complete: bool) -> dict[str, Any]:
            return build_run_snapshot(
                source=output.source,
                source_kind=output.source_kind.value,
                file_name=result.input.file.name or None,
                file_size=result.input.filesize,
                binary_hash=result.input.document_hash or None,
                status=str(output.status),
                complete=complete,
                started_at=started_at,
                finished_at=finished_at,
                engine_config=self.engine_config(make_html_preview=make_html_preview),
                pipeline_options=(
                    self._pipeline_options.model_dump(
                        mode="json", serialize_as_any=True
                    )
                    if self._pipeline_options is not None
                    else None
                ),
                page_count=output.page_count,
                pictures_extracted=len(output.picture_images),
                tables_extracted=len(output.table_images),
                errors=[e.model_dump() for e in errors],
                document_role=document_role,
                related=[r.model_dump(exclude_none=True) for r in related],
                structure_version=(
                    STRUCTURE_VERSION if output.structure is not None else None
                ),
                quality=(
                    output.quality.model_dump(mode="json")
                    if output.quality is not None
                    else None
                ),
            )

        if self._embed_images:
            with _step(errors, "html_export"):
                output.html_path = write_document_html(
                    doc,
                    pdf_dir,
                    noise_flags=noise_flags,
                    figures_jsonl=output.figures_jsonl,
                    tables_jsonl=output.tables_jsonl,
                    chunks_jsonl=output.chunks_jsonl,
                    run=snapshot(complete=False) if self._save_artifacts else None,
                    structure=output.structure,
                )

        if not self._save_artifacts:
            return
        # The check reads run.json (status, errors): it gets one that says the
        # bundle is not complete, and run.json is rewritten after check.json.
        with _step(errors, "run_snapshot"):
            write_run_snapshot(pdf_dir, snapshot(complete=False))
        if output.document_json is not None:
            with _step(errors, "export_check"):
                output.check = check_bundle(pdf_dir, pdf_path=local_pdf)
                output.check_json = write_bundle_check(pdf_dir, output.check)
        with _step(errors, "run_snapshot"):
            output.run_json = write_run_snapshot(pdf_dir, snapshot(complete=True))

    @staticmethod
    def _build_output(
        result: ConversionResult,
        *,
        kind: SourceKind,
        normalised: str,
    ) -> PdfConversionOutput:
        pages: list[PageSummary] = []
        for page in result.pages:
            size = page.size
            layout = page.predictions.layout if page.predictions else None
            cluster_count = len(layout.clusters) if layout is not None else 0
            pages.append(
                PageSummary(
                    page_no=page.page_no,
                    width=size.width if size is not None else None,
                    height=size.height if size is not None else None,
                    cluster_count=cluster_count,
                )
            )

        errors = [
            PdfEngineError(component=str(err.component_type), message=err.error_message)
            for err in result.errors
        ]

        return PdfConversionOutput(
            status=result.status,
            source=normalised,
            source_kind=kind,
            page_count=result.input.page_count,
            pages=pages,
            errors=errors,
            raw=result,
        )


@contextlib.contextmanager
def _step(errors: list[PdfEngineError], component: str) -> Iterator[None]:
    """Record an exception of the step in the block as an error of
    *component* and go on with the next step; ``KeyboardInterrupt`` passes."""
    try:
        yield
    except Exception as exc:
        _log.exception("PdfEngine: step %s failed", component)
        errors.append(
            PdfEngineError(component=component, message=f"{type(exc).__name__}: {exc}")
        )


def _write_embedded_markdown(
    doc: DoclingDocument,
    pdf_dir: Path,
    noise_flags: list[PictureNoiseFlag],
) -> Path:
    embedded = export_markdown(doc, image_mode=ImageRefMode.EMBEDDED)
    if noise_flags:
        embedded = _strip_noise_embedded(embedded, noise_flags)
    target = pdf_dir / f"{pdf_dir.name}.embedded.md"
    target.write_text(embedded, encoding="utf-8")
    _log.info("PdfEngine: wrote embedded markdown to %s", target)
    return target


def rewrite_bundle_markdown(doc: DoclingDocument, pdf_dir: Path) -> None:
    """Rewrite ``<stem>.md`` and ``<stem>.embedded.md`` of an existing
    bundle (each when present) from *doc*, with the picture links and noise
    comments of the conversion (read back from ``figures.jsonl``)."""
    noise_flags = [
        PictureNoiseFlag(
            self_ref=row.self_ref,
            is_noise=bool(row.is_noise),
            noise_reason=row.noise_reason,
            classifier_label=row.generic_classifier_label,
        )
        for row in read_figure_rows(pdf_dir)
    ]
    target = pdf_dir / f"{pdf_dir.name}.md"
    if target.is_file():
        linked = (
            sorted(
                path.relative_to(pdf_dir).as_posix()
                for path in (pdf_dir / IMAGES_SUBDIR).glob("picture_*.png")
            )
            if f"]({IMAGES_SUBDIR}/" in target.read_text(encoding="utf-8")
            else []
        )
        markdown = export_markdown(doc, image_mode=ImageRefMode.PLACEHOLDER)
        target.write_text(
            _link_picture_placeholders(markdown, linked, noise_flags), encoding="utf-8"
        )
    if (pdf_dir / f"{pdf_dir.name}.embedded.md").is_file():
        _write_embedded_markdown(doc, pdf_dir, noise_flags)


def _bundle_files(pdf_dir: Path) -> tuple[Path, ...]:
    """The files of a bundle that a conversion writes at its top level."""
    stem = pdf_dir.name
    names = (
        "document.json",
        "nodes.jsonl",
        "chunks.jsonl",
        "tables.jsonl",
        "figures.jsonl",
        STRUCTURE_FILENAME,
        RUN_JSON_FILENAME,
        CHECK_FILENAME,
        f"{stem}.md",
        f"{stem}.embedded.md",
        f"{stem}.html",
        "preview.html",
        "preview.embedded.html",
    )
    return tuple(pdf_dir / name for name in names)


def _remove_bundle_files(pdf_dir: Path) -> None:
    """Drop what an earlier conversion wrote into *pdf_dir*: a step that fails
    or writes nothing this time (``tables.jsonl`` of a PDF without tables)
    must not leave the previous run's file in the bundle, nor a picture that
    lost its crop the previous run's crop."""
    for path in _bundle_files(pdf_dir):
        path.unlink(missing_ok=True)
    for subdir in (IMAGES_SUBDIR, FIGURE_DATA_DIRNAME):
        if (pdf_dir / subdir).is_dir():
            shutil.rmtree(pdf_dir / subdir)


_UNSAFE_NAME = re.compile(r"[^\w.-]+")


def bundle_dir_name(file_name: str) -> str:
    """The sanitised stem of *file_name* that names its bundle folder; letters
    of every script are kept."""
    stem = unicodedata.normalize("NFC", PurePath(file_name).stem)
    return _UNSAFE_NAME.sub("_", stem).strip("._-") or "document"


def resolve_pdf_dir(
    output_dir: Path,
    file_name: str,
    *,
    file_size: int | None = None,
    binary_hash: str | None = None,
    taken: Collection[Path] = (),
    bundle_subdir: str | None = None,
) -> Path:
    """The bundle folder of the PDF *file_name*: ``<output_dir>/<base>``, or
    ``<base>_2``, ``<base>_3``... with ``base = bundle_dir_name(file_name)``.

    A folder of that sequence whose ``run.json`` records this PDF (its name,
    and its size and binary hash where known) is reused wherever it is, so a
    PDF keeps its folder when the PDFs before it come and go. Otherwise the
    PDF gets the first folder not in *taken* (an earlier PDF of the batch has
    it) that does not hold another PDF's bundle; a folder without
    ``run.json`` — an interrupted conversion of this PDF leaves one — is
    reused. *bundle_subdir* is where each folder keeps the ``run.json`` that
    identifies it (``standard`` in a comparison folder)."""
    base = bundle_dir_name(file_name)

    def record_dir(folder: Path) -> Path:
        return folder / bundle_subdir if bundle_subdir is not None else folder

    for folder in _numbered_dirs(output_dir, base):
        record = read_run_record(record_dir(folder))
        if (
            folder not in taken
            and record is not None
            and record.source.file_name is not None
            and record.is_source(file_name, file_size, binary_hash)
        ):
            return folder

    candidate = output_dir / base
    suffix = 1
    while candidate in taken or _holds_other_pdf(
        record_dir(candidate), file_name, file_size, binary_hash
    ):
        suffix += 1
        candidate = output_dir / f"{base}_{suffix}"
    if suffix > 1:
        _log.warning(
            "PdfEngine: %s is taken by another PDF; writing %s to %s",
            output_dir / base,
            file_name,
            candidate,
        )
    return candidate


def _numbered_dirs(output_dir: Path, base: str) -> list[Path]:
    """The folders ``<base>``, ``<base>_2``, ``<base>_3``... of *output_dir*
    that exist, in that order."""
    if not output_dir.is_dir():
        return []
    numbered = re.compile(rf"{re.escape(base)}(?:_(\d+))?")
    found: list[tuple[int, Path]] = []
    for entry in output_dir.iterdir():
        match = numbered.fullmatch(entry.name)
        if match is not None and entry.is_dir():
            found.append((int(match.group(1) or 1), entry))
    return [entry for _n, entry in sorted(found)]


def _holds_other_pdf(
    pdf_dir: Path, file_name: str, file_size: int | None, binary_hash: str | None
) -> bool:
    record = read_run_record(pdf_dir)
    return record is not None and not record.is_source(
        file_name, file_size, binary_hash
    )


def _link_picture_placeholders(
    markdown: str,
    picture_paths: list[str],
    noise_flags: list[PictureNoiseFlag] | None = None,
) -> str:
    """Replace ``<!-- image -->`` placeholders with ``![](path)`` refs.

    The Nth placeholder is the Nth picture of ``iterate_items()``, as are the
    crop named ``crop_stem("picture", N)`` and ``noise_flags[N]``. A picture
    without a crop keeps its placeholder; a noise-flagged picture becomes
    ``<!-- noise picture: <reason> -->``.
    """
    crops = {PurePosixPath(path).stem: path for path in picture_paths}
    flags = noise_flags or []
    positions = itertools.count()

    def _swap(_match: re.Match[str]) -> str:
        position = next(positions)
        flag = flags[position] if position < len(flags) else None
        if flag is not None and flag.is_noise:
            return _noise_comment(flag)
        path = crops.get(crop_stem("picture", position))
        return f"![]({path})" if path is not None else _PLACEHOLDER

    return re.sub(re.escape(_PLACEHOLDER), _swap, markdown)


# One per picture: its base64 image, or docling-core's comment for a picture
# without one ("<!-- 🖼️❌ Image not available. ... -->").
_EMBEDDED_PICTURE_RE = re.compile(
    r"!\[[^\]]*\]\(data:image/[^)]+\)|<!-- \S+ Image not available\.[^\n]*?-->"
)


def _strip_noise_embedded(markdown: str, noise_flags: list[PictureNoiseFlag]) -> str:
    """Replace the Nth picture of the embedded markdown with a comment when
    ``noise_flags[N]`` is noise."""
    positions = itertools.count()

    def _swap(match: re.Match[str]) -> str:
        position = next(positions)
        if position < len(noise_flags) and noise_flags[position].is_noise:
            return _noise_comment(noise_flags[position])
        return match.group(0)

    return _EMBEDDED_PICTURE_RE.sub(_swap, markdown)


def _noise_comment(flag: PictureNoiseFlag) -> str:
    return f"<!-- noise picture: {flag.noise_reason or 'unknown'} -->"
