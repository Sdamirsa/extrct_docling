# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Markdown serialization shared by ``<stem>.md`` / ``<stem>.embedded.md`` and
``chunks.jsonl``.

On top of Docling's markdown serializer:

- model-guessed picture labels are left out (:data:`TEXT_EXPORT_META_PARAMS`);
- text a model wrote about an item (a VLM figure description) is wrapped in
  ``<!--<annotation kind="description">-->…<!--<annotation/>-->``, so a reader
  can tell it from the paper's text. docling-core's ``mark_annotations`` knob
  only applies to items without ``meta``, and every picture of ours has meta
  (figure type, classification), so the description meta field is marked here,
  and so is the table of a figure's numbers a model read (``tabular_chart``,
  ``<!--<annotation kind="chart_data">-->``, with a sentence above the table
  that names the method and the model; see :mod:`docling.engines.figure_data`);
- a table whose cells miss words printed in its box (``amir__pdf_text``, see
  :func:`~docling.engines.text_repair.attach_table_pdf_text`) is followed by
  a ``Table text from the PDF (cell recall 0.61): …`` paragraph, so the
  markdown and the chunks keep the words the table model dropped.

``DoclingDocument.export_to_markdown`` builds its own serializer and takes no
table serializer, so the markdown exports go through :func:`export_markdown`.
"""

from __future__ import annotations

from typing import Any

from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
    TripletTableSerializer,
)
from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.transforms.serializer.markdown import (
    MarkdownDocSerializer,
    MarkdownMetaSerializer,
    MarkdownParams,
    MarkdownTableSerializer,
)
from docling_core.types.doc import DoclingDocument, ImageRefMode, TableItem
from docling_core.types.doc.document import BaseMeta
from typing_extensions import override

from docling.engines.figure_typing import TEXT_EXPORT_META_PARAMS
from docling.engines.text_repair import get_table_pdf_text

DESCRIPTION_OPEN = '<!--<annotation kind="description">-->'
CHART_DATA_OPEN = '<!--<annotation kind="chart_data">-->'
ANNOTATION_CLOSE = "<!--<annotation/>-->"
TABLE_PDF_TEXT_PREFIX = "Table text from the PDF"

_DESCRIPTION_FIELD = "description"
_CHART_DATA_FIELD = "tabular_chart"
_TEXT_EXPORT_PARAMS: dict[str, Any] = {
    **TEXT_EXPORT_META_PARAMS,
    "mark_annotations": True,
}


def markdown_params(
    image_mode: ImageRefMode = ImageRefMode.PLACEHOLDER,
) -> MarkdownParams:
    """Params of the ``.md`` exports: Docling's defaults plus this module's
    policy."""
    return MarkdownParams(image_mode=image_mode, **_TEXT_EXPORT_PARAMS)


def export_markdown(
    doc: DoclingDocument, *, image_mode: ImageRefMode = ImageRefMode.PLACEHOLDER
) -> str:
    """``doc.export_to_markdown(image_mode=...)`` with this module's policy."""
    serializer = MarkdownDocSerializer(
        doc=doc,
        params=markdown_params(image_mode),
        table_serializer=_MarkdownTableSerializer(),
        meta_serializer=_MarkedMetaSerializer(),
    )
    return serializer.serialize().text


def build_serializer_provider() -> ChunkingSerializerProvider:
    """Serializer provider for ``HybridChunker`` with the same policy."""
    return _ChunkingSerializerProvider()


class _ChunkingSerializerProvider(ChunkingSerializerProvider):
    @override
    def get_serializer(self, doc: DoclingDocument) -> ChunkingDocSerializer:
        defaults: MarkdownParams = ChunkingDocSerializer.model_fields["params"].default
        return ChunkingDocSerializer(
            doc=doc,
            params=defaults.model_copy(update=_TEXT_EXPORT_PARAMS),
            table_serializer=_ChunkingTableSerializer(),
            meta_serializer=_MarkedMetaSerializer(),
        )


class _MarkedMetaSerializer(MarkdownMetaSerializer):
    @override
    def _serialize_meta_field(
        self, meta: BaseMeta, name: str, mark_meta: bool, **kwargs: Any
    ) -> str | None:
        text = super()._serialize_meta_field(meta, name, mark_meta, **kwargs)
        if text and name == _DESCRIPTION_FIELD:
            return f"{DESCRIPTION_OPEN}{text}{ANNOTATION_CLOSE}"
        if name == _CHART_DATA_FIELD:
            # The field's title says who read the table and how far to
            # trust it; it stands alone when the values are held back.
            # Blank lines around the table, or markdown does not render it.
            note = meta.tabular_chart.title if meta.tabular_chart else None
            body = "\n\n".join(part for part in (note, text) if part)
            return (
                f"{CHART_DATA_OPEN}\n\n{body}\n\n{ANNOTATION_CLOSE}" if body else None
            )
        return text


class _MarkdownTableSerializer(MarkdownTableSerializer):
    @override
    def serialize(
        self,
        *,
        item: TableItem,
        doc_serializer: BaseDocSerializer,
        doc: DoclingDocument,
        **kwargs: Any,
    ) -> SerializationResult:
        result = super().serialize(
            item=item, doc_serializer=doc_serializer, doc=doc, **kwargs
        )
        return _with_pdf_text(result, item, doc_serializer, **kwargs)


class _ChunkingTableSerializer(TripletTableSerializer):
    @override
    def serialize(
        self,
        *,
        item: TableItem,
        doc_serializer: BaseDocSerializer,
        doc: DoclingDocument,
        **kwargs: Any,
    ) -> SerializationResult:
        result = super().serialize(
            item=item, doc_serializer=doc_serializer, doc=doc, **kwargs
        )
        return _with_pdf_text(result, item, doc_serializer, **kwargs)


def _with_pdf_text(
    result: SerializationResult,
    item: TableItem,
    doc_serializer: BaseDocSerializer,
    **kwargs: Any,
) -> SerializationResult:
    # A table nested in a table cell renders inline; a paragraph would break
    # the outer table.
    if kwargs.get("_nested_in_table") or item.self_ref in (
        doc_serializer.get_excluded_refs(**kwargs)
    ):
        return result
    pdf_text = get_table_pdf_text(item)
    if pdf_text is None:
        return result
    text = " ".join(pdf_text["text"].split())
    if not text:
        return result
    paragraph = create_ser_result(
        text=(
            f"{TABLE_PDF_TEXT_PREFIX} (cell recall "
            f"{pdf_text['cell_text_recall']:.2f}): "
            f"{doc_serializer.post_process(text=text)}"
        ),
        span_source=item,
    )
    # The paragraph's span keeps a table whose grid came out empty in the
    # chunks: the chunker drops a serialization without spans.
    return create_ser_result(
        text="\n\n".join(part.text for part in (result, paragraph) if part.text),
        span_source=[result, paragraph],
    )
