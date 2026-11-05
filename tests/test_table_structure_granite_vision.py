# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import pytest
import torch
from docling_core.types.doc import BoundingBox, DocItemLabel, TableCell
from huggingface_hub import try_to_load_from_cache

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import (
    Cluster,
    InputFormat,
    Table,
    TableStructurePrediction,
    degenerate_table_reason,
    table_filled_fraction,
)
from docling.datamodel.pipeline_options import (
    GraniteVisionTableStructureOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.models.stages.table_structure import (
    table_structure_model_granite_vision,
)
from docling.models.stages.table_structure.table_structure_model_granite_vision import (
    GraniteVisionTableStructureModel,
    merge_table_predictions,
)
from docling.utils.otsl import parse_otsl_output

pytestmark = pytest.mark.ml_vlm


def test_options_kind():
    opts = GraniteVisionTableStructureOptions()
    assert opts.kind == "granite_vision_table"


def test_parse_simple_table():
    """2x2 table with column headers."""
    text = "<ched>Name</ched><ched>Value</ched><nl><fcel>Foo</fcel><fcel>42</fcel><nl>"
    otsl_seq, cells, num_rows, num_cols = parse_otsl_output(text)

    assert otsl_seq == ["ched", "ched", "nl", "fcel", "fcel", "nl"]
    assert num_rows == 2
    assert num_cols == 2
    assert len(cells) == 4

    header_cells = [c for c in cells if c.column_header]
    assert len(header_cells) == 2
    assert header_cells[0].text == "Name"
    assert header_cells[1].text == "Value"

    data_cells = [c for c in cells if not c.column_header]
    assert data_cells[0].text == "Foo"
    assert data_cells[0].start_row_offset_idx == 1
    assert data_cells[0].start_col_offset_idx == 0
    assert data_cells[1].text == "42"
    assert data_cells[1].start_col_offset_idx == 1


def test_parse_empty_cell():
    """Empty cell produces empty text, still in grid."""
    text = "<ched>A</ched><ched>B</ched><nl><fcel>x</fcel><ecel></ecel><nl>"
    _otsl_seq, cells, num_rows, num_cols = parse_otsl_output(text)

    assert num_rows == 2
    assert num_cols == 2
    assert len(cells) == 4
    empty = [
        c for c in cells if c.start_row_offset_idx == 1 and c.start_col_offset_idx == 1
    ]
    assert len(empty) == 1
    assert empty[0].text == ""


def test_parse_colspan():
    """lcel produces colspan=2 on the preceding fcel."""
    text = "<fcel>Merged</fcel><lcel><nl><fcel>A</fcel><fcel>B</fcel><nl>"
    _otsl_seq, cells, _num_rows, num_cols = parse_otsl_output(text)

    assert num_cols == 2
    merged = [
        c for c in cells if c.start_row_offset_idx == 0 and c.start_col_offset_idx == 0
    ]
    assert len(merged) == 1
    assert merged[0].col_span == 2
    assert merged[0].end_col_offset_idx == 2


def test_parse_rowspan():
    """ucel produces rowspan=2 on the preceding fcel above it."""
    text = "<fcel>Tall</fcel><fcel>A</fcel><nl><ucel><fcel>B</fcel><nl>"
    _otsl_seq, cells, _num_rows, _num_cols = parse_otsl_output(text)

    tall = [
        c for c in cells if c.start_row_offset_idx == 0 and c.start_col_offset_idx == 0
    ]
    assert len(tall) == 1
    assert tall[0].row_span == 2
    assert tall[0].end_row_offset_idx == 2


def test_parse_multiple_rowspan():
    """Multiple ucel produces rowspan=2 on the corresponding fcel above it."""
    text = (
        "<fcel>Regular</fcel><fcel>Merged</fcel><fcel>Merged</fcel><nl>"
        "<fcel>Regular</fcel><ucel><ucel><nl>"
    )
    _otsl_seq, cells, num_rows, num_cols = parse_otsl_output(text)

    assert num_cols == 3
    assert num_rows == 2
    assert len(cells) == 4
    for cell in cells:
        if cell.text == "Merged":
            assert cell.row_span == 2
            assert cell.col_span == 1
            assert cell.start_row_offset_idx == 0
            assert cell.end_row_offset_idx == 2
            assert cell.start_col_offset_idx + 1 == cell.end_col_offset_idx
        else:
            assert cell.text == "Regular"
            assert cell.row_span == 1
            assert cell.col_span == 1
            assert cell.start_row_offset_idx + 1 == cell.end_row_offset_idx
            assert cell.start_col_offset_idx + 1 == cell.end_col_offset_idx


def test_parse_xcel():
    """xcel is merged with adjacent ucel and lcel."""
    text = (
        "<fcel>Regular</fcel><fcel>Regular</fcel><fcel>Regular</fcel><fcel>Regular</fcel><nl>"
        "<fcel>Regular</fcel><fcel>Merged</fcel><lcel><fcel>Regular</fcel><nl>"
        "<fcel>Regular</fcel><ucel><xcel><fcel>Regular</fcel><nl>"
        "<fcel>Regular</fcel><fcel>Regular</fcel><fcel>Regular</fcel><fcel>Regular</fcel><nl>"
    )
    _otsl_seq, cells, num_rows, num_cols = parse_otsl_output(text)

    assert num_cols == 4
    assert num_rows == 4
    assert len(cells) == 13
    for cell in cells:
        if cell.text == "Merged":
            assert cell.row_span == 2
            assert cell.col_span == 2
            assert cell.start_col_offset_idx == 1
            assert cell.end_col_offset_idx == 3
            assert cell.start_row_offset_idx == 1
            assert cell.end_row_offset_idx == 3
        else:
            assert cell.text == "Regular"
            assert cell.row_span == 1
            assert cell.col_span == 1
            assert cell.start_row_offset_idx + 1 == cell.end_row_offset_idx
            assert cell.start_col_offset_idx + 1 == cell.end_col_offset_idx


def test_parse_row_header():
    """rhed token produces row_header=True."""
    text = "<rhed>Section</rhed><fcel>Data</fcel><nl>"
    _, cells, _, _ = parse_otsl_output(text)

    rhed_cells = [c for c in cells if c.row_header]
    assert len(rhed_cells) == 1
    assert rhed_cells[0].text == "Section"


def test_parse_no_bbox():
    """All cells must have bbox=None."""
    text = "<ched>X</ched><nl><fcel>Y</fcel><nl>"
    _, cells, _, _ = parse_otsl_output(text)
    assert all(c.bbox is None for c in cells)


def test_parse_empty_string():
    """Empty or whitespace-only string returns empty table."""
    otsl_seq, cells, num_rows, num_cols = parse_otsl_output("")
    assert otsl_seq == []
    assert cells == []
    assert num_rows == 0
    assert num_cols == 0


def test_get_options_type():
    assert (
        GraniteVisionTableStructureModel.get_options_type()
        is GraniteVisionTableStructureOptions
    )


def test_model_disabled_skips_pages():
    """When enabled=False, predict_tables returns empty prediction without running inference."""
    from unittest.mock import MagicMock

    from docling_core.types.doc import DocItemLabel

    model = GraniteVisionTableStructureModel(
        enabled=False,
        artifacts_path=None,
        options=GraniteVisionTableStructureOptions(),
        accelerator_options=AcceleratorOptions(),
    )

    # Give the page a cluster labelled TABLE so the cluster filter passes —
    # the skip must be triggered by enabled=False, not by an empty cluster list.
    cluster = MagicMock()
    cluster.label = DocItemLabel.TABLE

    page = MagicMock()
    page._backend.is_valid.return_value = True
    page.predictions.layout.clusters = [cluster]
    page.predictions.tablestructure = None
    page.size = MagicMock()

    results = model.predict_tables(MagicMock(), [page])
    assert len(results) == 1
    assert results[0].table_map == {}


def test_model_invalid_backend_returns_empty_prediction():
    """Pages with invalid backends return an empty TableStructurePrediction."""
    from unittest.mock import MagicMock

    model = GraniteVisionTableStructureModel(
        enabled=False,
        artifacts_path=None,
        options=GraniteVisionTableStructureOptions(),
        accelerator_options=AcceleratorOptions(),
    )

    page = MagicMock()
    page._backend.is_valid.return_value = False
    page.predictions.tablestructure = None

    results = model.predict_tables(MagicMock(), [page])
    assert len(results) == 1
    assert results[0].table_map == {}


def test_parse_xcel_2d_merge():
    """xcel produces both rowspan=2 and colspan=2 on the origin cell."""
    text = "<fcel>Big</fcel><lcel><nl><ucel><xcel><nl>"
    _, cells, num_rows, num_cols = parse_otsl_output(text)

    assert num_rows == 2
    assert num_cols == 2
    origin = [
        c for c in cells if c.start_row_offset_idx == 0 and c.start_col_offset_idx == 0
    ]
    assert len(origin) == 1
    assert origin[0].col_span == 2
    assert origin[0].row_span == 2
    assert origin[0].end_col_offset_idx == 2
    assert origin[0].end_row_offset_idx == 2


def test_parse_srow():
    """srow token produces row_section=True."""
    text = "<srow>Category</srow><fcel>Data</fcel><nl>"
    _, cells, _, _ = parse_otsl_output(text)

    srow_cells = [c for c in cells if c.row_section]
    assert len(srow_cells) == 1
    assert srow_cells[0].text == "Category"


def test_parse_ecel_self_closing():
    """<ecel/> self-closing form produces an empty cell."""
    text = "<fcel>A</fcel><ecel/><nl>"
    _, cells, _, _ = parse_otsl_output(text)

    empty = [c for c in cells if c.start_col_offset_idx == 1]
    assert len(empty) == 1
    assert empty[0].text == ""


def test_factory_registration():
    """GraniteVisionTableStructureModel must be discoverable via the table structure factory."""
    from docling.models.factories.table_factory import TableStructureFactory
    from docling.models.stages.table_structure.table_structure_model_granite_vision import (
        GraniteVisionTableStructureModel,
    )

    factory = TableStructureFactory()
    factory.load_from_plugins()
    registered = list(factory.classes.values())
    assert GraniteVisionTableStructureModel in registered


def _table(cid: int, rows: list[list[str]]) -> Table:
    cluster = Cluster(
        id=cid, label=DocItemLabel.TABLE, bbox=BoundingBox(l=0, t=0, r=100, b=100)
    )
    return Table(
        otsl_seq=[],
        table_cells=_cells(rows),
        num_rows=len(rows),
        num_cols=len(rows[0]) if rows else 0,
        id=cid,
        page_no=1,
        cluster=cluster,
        label=DocItemLabel.TABLE,
    )


def _cells(rows: list[list[str]]) -> list[TableCell]:
    return [
        TableCell(
            text=text,
            start_row_offset_idx=r,
            end_row_offset_idx=r + 1,
            start_col_offset_idx=c,
            end_col_offset_idx=c + 1,
        )
        for r, row in enumerate(rows)
        for c, text in enumerate(row)
    ]


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        ([], "empty grid"),
        ([["Mode", "Stage", "Time", "Recall", "F1"]], None),
        ([["The", "agent", "must", "", "", ""]], "one row of 6 columns"),
        ([["✓", "", ""], ["", "", ""], ["", "", ""]], "11% of the grid filled"),
        ([["✓", "", ""], ["", "✓", ""], ["", "", "✓"]], None),
    ],
)
def test_degenerate_table_reason(rows: list[list[str]], reason: str | None) -> None:
    num_cols = len(rows[0]) if rows else 0
    assert degenerate_table_reason(len(rows), num_cols, _cells(rows)) == reason


def test_a_spanning_cell_fills_every_slot_it_spans() -> None:
    """A filled header across a 3x3 grid of otherwise empty cells fills 3 of
    its 9 slots: not degenerate, though it is 1 of 7 cells."""
    header = TableCell(
        text="Checklist item",
        start_row_offset_idx=0,
        end_row_offset_idx=1,
        start_col_offset_idx=0,
        end_col_offset_idx=3,
    )
    body = _cells([["", "", ""], ["", "", ""]])
    for cell in body:
        cell.start_row_offset_idx += 1
        cell.end_row_offset_idx += 1

    assert table_filled_fraction(3, 3, [header, *body]) == 0.333
    assert degenerate_table_reason(3, 3, [header, *body]) is None


def test_merge_takes_the_fallback_table_only_for_flagged_clusters() -> None:
    granite = TableStructurePrediction(
        table_map={cid: _table(cid, [["granite"]]) for cid in (3, 7, 9)}
    )
    tableformer = TableStructurePrediction(
        table_map={cid: _table(cid, [["tableformer"]]) for cid in (3, 7)}
    )

    merged = merge_table_predictions(granite, tableformer, {7, 9})

    assert list(merged.table_map) == [3, 7, 9]
    assert {cid: t.table_cells[0].text for cid, t in merged.table_map.items()} == {
        3: "granite",
        7: "tableformer",
        9: "granite",
    }


_GRANITE_ON_GPU = torch.cuda.is_available() and isinstance(
    try_to_load_from_cache(
        GraniteVisionTableStructureModel._model_repo_id,
        "config.json",
        revision=GraniteVisionTableStructureModel._model_repo_revision,
    ),
    str,
)


@pytest.mark.skipif(
    not _GRANITE_ON_GPU, reason="needs CUDA and the Granite-Vision weights cached"
)
def test_a_truncated_granite_table_takes_its_structure_from_tableformer(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """With a budget no table fits in, every Granite generation is cut off;
    each table must reach the document with TableFormer's grid, whose cells
    are matched to PDF text cells and so are located (OTSL cells never are)."""
    monkeypatch.setattr(
        GraniteVisionTableStructureModel, "_generation_budget", lambda self, c: 8
    )
    options = PdfPipelineOptions(
        do_ocr=False, table_structure_options=GraniteVisionTableStructureOptions()
    )
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )

    with caplog.at_level(
        logging.WARNING, logger=table_structure_model_granite_vision.__name__
    ):
        doc = converter.convert(
            Path("tests/data/pdf/sources/2305.03393v1-pg9.pdf")
        ).document

    fallbacks = [
        r.getMessage()
        for r in caplog.records
        if r.getMessage().endswith("structure taken from TableFormer")
    ]
    assert doc.tables
    assert len(fallbacks) == len(doc.tables)
    assert all("hit the 8-token generation budget" in m for m in fallbacks)
    for table in doc.tables:
        assert table.data.num_rows > 1
        assert table.data.num_cols > 1
        assert all(cell.bbox is not None for cell in table.data.table_cells)
