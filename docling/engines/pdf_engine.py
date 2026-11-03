# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""High-level PDF conversion engine (Phase 1 of the Amir Engine build)."""

from __future__ import annotations

import datetime as _dt
import logging
import re
from pathlib import Path
from typing import Optional

from docling_core.types.doc import ImageRefMode

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    GraniteVisionTableStructureOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.engines.artifacts import ArtifactsError, write_artifacts
from docling.engines.chunker import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOKENIZER,
    ChunkerError,
    write_chunks,
)
from docling.engines.figure_typing import (
    BIOMEDCLIP_REPO,
    TEXT_EXPORT_META_PARAMS,
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
from docling.engines.run_snapshot import write_run_snapshot
from docling.engines.schemas import (
    PageSummary,
    PdfConversionOutput,
    PdfEngineError,
    SourceKind,
)
from docling.engines.structured_outputs import (
    StructuredOutputsError,
    write_structured_outputs,
)
from docling.engines.text_repair import (
    attach_table_pdf_text,
    pdf_page_words,
    repair_ligature_splits,
)
from docling.engines.validation import validate_pdf_source
from docling.engines.visualizer import (
    PreviewError,
    embed_html_images,
    render_html_preview,
)
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
        figure_types: bool = True,
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
        figure_types
            When True (default), types every picture with BiomedCLIP into a
            scientific/medical taxonomy (``ct``, ``angiography``, ``ecg``,
            ``kaplan_meier``... see
            :data:`~docling.engines.figure_typing.FIGURE_TYPES`). Lands in
            ``figures.jsonl[*].figure_type`` and on ``PictureItem.meta``
            (``amir__figure_type``) in ``document.json``. Needs picture
            images (``save_artifacts`` or ``embed_images``) and the
            ``models-vlm-inline`` extra (open-clip-torch); ~0.8 GB GPU.
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
            "figure_types": BIOMEDCLIP_REPO if figure_types else None,
            "converter_supplied": converter is not None,
        }
        self._figure_typer = FigureTyper() if figure_types else None
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
            self._pipeline_options.do_picture_description = True
            self._pipeline_options.picture_description_options = (
                build_picture_description_options(
                    picture_description, engine=picture_description_engine
                )
            )

        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self._pipeline_options
                )
            },
        )

    def convert(
        self,
        source: str | Path,
        *,
        output_dir: Path | None = None,
        max_num_pages: int | None = None,
        make_html_preview: bool = False,
    ) -> PdfConversionOutput:
        """Convert a single PDF from a local path or URL.

        Parameters
        ----------
        source
            Path to a local ``.pdf`` file or an ``http(s)://`` URL.
        output_dir
            If given, writes the markdown export(s) to
            ``<output_dir>/<stem>/<stem>.md`` (and ``<stem>.embedded.md`` when
            ``embed_images=True``).
        max_num_pages
            Optional cap on the number of pages to convert.
        """
        kind, normalised = validate_pdf_source(source)
        _log.info("PdfEngine: converting %s (%s)", normalised, kind.value)

        convert_kwargs: dict[str, object] = {"raises_on_error": False}
        if max_num_pages is not None:
            convert_kwargs["max_num_pages"] = max_num_pages

        started_at = _dt.datetime.now(_dt.timezone.utc)
        try:
            result: ConversionResult = self._converter.convert(
                normalised,
                **convert_kwargs,  # type: ignore[arg-type]
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

        if (
            result.status
            in {ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS}
            and kind == SourceKind.LOCAL_PATH
        ):
            # Before _build_output (which exports the markdown) and every
            # other export. A URL source has no local file to read.
            repair_ligature_splits(result.document, pdf_page_words(Path(normalised)))
            attach_table_pdf_text(result.document, Path(normalised))

        output = self._build_output(result, kind=kind, normalised=normalised)

        if output.succeeded and self._figure_typer is not None:
            typed = type_pictures(result, self._figure_typer)
            _log.info("PdfEngine: typed %d picture(s) with BiomedCLIP", typed)

        if output.succeeded and output_dir is not None:
            pdf_dir = _resolve_pdf_dir(output_dir, normalised, result)
            pdf_dir.mkdir(parents=True, exist_ok=True)
            output.output_dir = pdf_dir

            noise_flags: list[PictureNoiseFlag] = []
            if self._filter_noise_pictures:
                noise_flags = classify_pictures(
                    result,
                    noise_classes=self._noise_picture_classes,
                    repeat_threshold=self._noise_repeat_threshold,
                )

            if self._save_artifacts:
                try:
                    artifacts = write_artifacts(result, pdf_dir)
                    output.document_json = artifacts.document_json
                    output.nodes_jsonl = artifacts.nodes_jsonl
                    output.picture_images = artifacts.picture_images
                    output.table_images = artifacts.table_images
                except ArtifactsError as exc:
                    _log.warning("PdfEngine: artifacts not written: %s", exc)
                    output.errors.append(
                        PdfEngineError(component="artifacts", message=str(exc))
                    )

                try:
                    chunks = write_chunks(
                        result,
                        pdf_dir,
                        tokenizer_repo=self._chunk_tokenizer,
                        max_tokens=self._chunk_max_tokens,
                    )
                    output.chunks_jsonl = chunks.chunks_jsonl
                except ChunkerError as exc:
                    _log.warning("PdfEngine: chunks not written: %s", exc)
                    output.errors.append(
                        PdfEngineError(component="chunker", message=str(exc))
                    )

                try:
                    structured = write_structured_outputs(
                        result,
                        pdf_dir,
                        picture_image_paths=output.picture_images,
                        table_image_paths=output.table_images,
                        picture_noise_flags=noise_flags,
                    )
                    output.tables_jsonl = structured.tables_jsonl
                    output.figures_jsonl = structured.figures_jsonl
                except StructuredOutputsError as exc:
                    _log.warning("PdfEngine: structured outputs not written: %s", exc)
                    output.errors.append(
                        PdfEngineError(component="structured_outputs", message=str(exc))
                    )

            if self._link_images and output.markdown and output.picture_images:
                rel_paths = [
                    p.relative_to(pdf_dir).as_posix() for p in output.picture_images
                ]
                output.markdown = _link_picture_placeholders(
                    output.markdown, rel_paths, noise_flags
                )

            self._write_primary_markdown(output, pdf_dir)

            if self._embed_images:
                output.markdown_embedded_path = self._write_embedded_markdown(
                    result, pdf_dir, output.errors, noise_flags
                )

            if self._save_artifacts:
                output.run_json = write_run_snapshot(
                    pdf_dir,
                    source=normalised,
                    source_kind=kind.value,
                    status=str(output.status),
                    started_at=started_at,
                    finished_at=finished_at,
                    engine_config=self._engine_config,
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
                    errors=[e.model_dump() for e in output.errors],
                )

            # After run.json and the jsonl sidecars: the HTML manifest embeds them.
            if self._embed_images:
                output.html_path = self._write_document_html(
                    result, pdf_dir, output.errors, noise_flags
                )

            if make_html_preview:
                try:
                    output.preview_html = render_html_preview(
                        result,
                        pdf_dir,
                        image_scale=self._image_scale,
                        noise_flags=noise_flags,
                        chunks_jsonl=output.chunks_jsonl,
                    )
                    if self._embed_images:
                        output.preview_html_embedded = embed_html_images(
                            output.preview_html
                        )
                except PreviewError as exc:
                    _log.warning("PdfEngine: HTML preview skipped: %s", exc)
                    output.errors.append(
                        PdfEngineError(component="visualizer", message=str(exc))
                    )
        elif make_html_preview and output_dir is None:
            raise ValueError("make_html_preview=True requires output_dir to be set.")

        return output

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

        markdown: str | None = None
        if result.status in {
            ConversionStatus.SUCCESS,
            ConversionStatus.PARTIAL_SUCCESS,
        }:
            try:
                markdown = result.document.export_to_markdown(
                    image_mode=ImageRefMode.PLACEHOLDER, **TEXT_EXPORT_META_PARAMS
                )
            except Exception as exc:  # pragma: no cover - defensive
                _log.warning("PdfEngine: markdown export failed: %s", exc)
                errors.append(
                    PdfEngineError(component="export_to_markdown", message=str(exc))
                )

        return PdfConversionOutput(
            status=result.status,
            source=normalised,
            source_kind=kind,
            page_count=result.input.page_count
            if result.input is not None
            else len(pages),
            pages=pages,
            errors=errors,
            markdown=markdown,
            raw=result,
        )

    @staticmethod
    def _write_primary_markdown(output: PdfConversionOutput, pdf_dir: Path) -> None:
        if output.markdown is None:
            return
        target = pdf_dir / f"{pdf_dir.name}.md"
        target.write_text(output.markdown, encoding="utf-8")
        _log.info("PdfEngine: wrote markdown to %s", target)

    @staticmethod
    def _write_embedded_markdown(
        result: ConversionResult,
        pdf_dir: Path,
        errors: list[PdfEngineError],
        noise_flags: list[PictureNoiseFlag] | None = None,
    ) -> Path | None:
        try:
            embedded = result.document.export_to_markdown(
                image_mode=ImageRefMode.EMBEDDED, **TEXT_EXPORT_META_PARAMS
            )
        except Exception as exc:
            _log.warning("PdfEngine: embedded markdown export failed: %s", exc)
            errors.append(
                PdfEngineError(
                    component="export_to_markdown_embedded", message=str(exc)
                )
            )
            return None
        if noise_flags:
            embedded = _strip_noise_embedded(embedded, noise_flags)
        target = pdf_dir / f"{pdf_dir.name}.embedded.md"
        target.write_text(embedded, encoding="utf-8")
        _log.info("PdfEngine: wrote embedded markdown to %s", target)
        return target

    @staticmethod
    def _write_document_html(
        result: ConversionResult,
        pdf_dir: Path,
        errors: list[PdfEngineError],
        noise_flags: list[PictureNoiseFlag],
    ) -> Path | None:
        try:
            return write_document_html(
                result.document, pdf_dir, noise_flags=noise_flags
            )
        except Exception as exc:
            _log.warning("PdfEngine: standalone HTML export failed: %s", exc)
            errors.append(PdfEngineError(component="html_export", message=str(exc)))
            return None


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _link_picture_placeholders(
    markdown: str,
    picture_paths: list[str],
    noise_flags: list[PictureNoiseFlag] | None = None,
) -> str:
    """Replace ``<!-- image -->`` placeholders with ``![](path)`` refs in order.

    When ``noise_flags`` is given and the Nth placeholder corresponds to a
    noise-flagged picture, emit ``<!-- noise picture: <reason> -->`` instead.
    """
    iterator = iter(
        zip(picture_paths, noise_flags or [None] * len(picture_paths), strict=False)
    )

    def _swap(_match: re.Match[str]) -> str:
        try:
            path, flag = next(iterator)
        except StopIteration:
            return _PLACEHOLDER
        if flag is not None and flag.is_noise:
            return f"<!-- noise picture: {flag.noise_reason or 'unknown'} -->"
        return f"![]({path})"

    return re.sub(re.escape(_PLACEHOLDER), _swap, markdown)


_EMBEDDED_IMG_RE = re.compile(r"!\[[^\]]*\]\(data:image/[^)]+\)")


def _strip_noise_embedded(markdown: str, noise_flags: list[PictureNoiseFlag]) -> str:
    """Replace base64 image refs whose iteration index is noise with a comment."""
    iterator = iter(noise_flags)

    def _swap(match: re.Match[str]) -> str:
        try:
            flag = next(iterator)
        except StopIteration:
            return match.group(0)
        if flag.is_noise:
            return f"<!-- noise picture: {flag.noise_reason or 'unknown'} -->"
        return match.group(0)

    return _EMBEDDED_IMG_RE.sub(_swap, markdown)


def _resolve_pdf_dir(
    output_dir: Path, normalised: str, result: ConversionResult
) -> Path:
    """Return ``output_dir / <safe-stem>`` for this PDF.

    Prefers the upstream-reported input filename (which works for URL inputs
    too) and falls back to the source's stem; sanitised for filesystem
    safety.
    """
    raw_name: str | None = None
    if result.input is not None:
        try:
            raw_name = result.input.file.name
        except Exception:  # pragma: no cover - defensive
            raw_name = None
    candidate = Path(raw_name or normalised).stem or "document"
    safe = _SAFE_NAME.sub("_", candidate).strip("._-") or "document"
    return output_dir / safe
