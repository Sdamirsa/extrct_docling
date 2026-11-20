# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

import importlib.metadata
import logging
import re
import unicodedata
import warnings
from collections import Counter
from collections.abc import Collection, Sequence
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

import torch
from docling_core.types.doc import DocItemLabel
from transformers import AutoModelForImageTextToText, AutoProcessor

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import (
    Cluster,
    Page,
    Table,
    TableStructurePrediction,
    degenerate_table_reason,
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    GraniteVisionTableStructureOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.models.base_table_model import BaseTableStructureModel
from docling.models.stages.table_structure.table_structure_model import (
    TableStructureModel,
)
from docling.models.utils.hf_model_download import download_hf_model
from docling.utils.accelerator_utils import decide_device
from docling.utils.granite_vision_utils import granite_vision_4_needs_remote_code
from docling.utils.otsl import parse_otsl_output
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


# Granite-Vision keeps a table whose box has PDF text (a table of contents)
# while its cells hold this share of that text's words. Below it the model
# stopped early: two contents fragments held 0.46 and 0.49 of their words,
# TableFormer all of them. The bar is under the check's 0.95 on purpose: a
# lost space at a line break costs a few words, not a fifth.
MIN_PDF_WORDS_HELD = 0.8
_MIN_PDF_WORDS = 8
_WORD_TOKEN = re.compile(r"[a-z0-9]{2,}")


def _word_counts(text: str) -> Counter[str]:
    return Counter(_WORD_TOKEN.findall(unicodedata.normalize("NFKC", text).lower()))


def pdf_words_held(table: Table) -> float | None:
    """The share of the words the PDF prints in *table*'s box that its cells
    hold; None for a box with next to no PDF text (an image, OCR)."""
    printed = _word_counts(
        " ".join(cell.text for cell in table.cluster.cells if not cell.from_ocr)
    )
    total = sum(printed.values())
    if total < _MIN_PDF_WORDS:
        return None
    held = _word_counts(" ".join(cell.text for cell in table.table_cells))
    return 1 - sum((printed - held).values()) / total


def merge_table_predictions(
    primary: TableStructurePrediction,
    fallback: TableStructurePrediction,
    fallback_ids: Collection[int],
) -> TableStructurePrediction:
    """*primary*'s tables, with *fallback*'s in place of those in
    *fallback_ids* (where *fallback* has one)."""
    return TableStructurePrediction(
        table_map={
            cid: fallback.table_map[cid]
            if cid in fallback_ids and cid in fallback.table_map
            else table
            for cid, table in primary.table_map.items()
        }
    )


class GraniteVisionTableStructureModel(BaseTableStructureModel):
    """Table structure model using ibm-granite/granite-vision-4.1-4b with <tables_otsl>."""

    _model_repo_id: ClassVar[str] = "ibm-granite/granite-vision-4.1-4b"
    _model_repo_folder: ClassVar[str] = "ibm-granite--granite-vision-4.1-4b"
    _model_repo_revision: ClassVar[str] = "dd48e97503de471803850df70843cf9eb5da8712"

    def __init__(
        self,
        enabled: bool,
        artifacts_path: Path | None,
        options: GraniteVisionTableStructureOptions,
        accelerator_options: AcceleratorOptions,
        enable_remote_services: Literal[False] = False,
    ):
        self.enabled = enabled
        self.options = options
        self.accelerator_options = accelerator_options
        self._artifacts_path = artifacts_path
        self._tableformer_unavailable = False

        if self.enabled:
            self.device = decide_device(
                accelerator_options.device,
                supported_devices=[AcceleratorDevice.CPU, AcceleratorDevice.CUDA],
            )

            if artifacts_path is None:
                artifacts_path = self.download_models()
            elif (artifacts_path / self._model_repo_folder).exists():
                artifacts_path = artifacts_path / self._model_repo_folder
            else:
                _log.warning(
                    f"Model artifacts not found at {artifacts_path / self._model_repo_folder},"
                    " they will be downloaded."
                )

            self._load_model(artifacts_path)

    @classmethod
    def get_options_type(cls) -> type[GraniteVisionTableStructureOptions]:
        return GraniteVisionTableStructureOptions

    @classmethod
    def download_models(
        cls,
        local_dir: Path | None = None,
        force: bool = False,
        progress: bool = False,
    ) -> Path:
        return download_hf_model(
            repo_id=cls._model_repo_id,
            revision=cls._model_repo_revision,
            local_dir=local_dir,
            force=force,
            progress=progress,
        )

    def _load_model(self, artifacts_path: Path) -> None:
        trust_remote_code = granite_vision_4_needs_remote_code(
            importlib.metadata.version("transformers")
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*torch_dtype.*deprecated.*",
                category=UserWarning,
            )
            warnings.filterwarnings(
                "ignore",
                message=".*incorrect regex pattern.*",
                category=UserWarning,
            )
            self._processor = AutoProcessor.from_pretrained(
                artifacts_path,
                trust_remote_code=trust_remote_code,
            )
            self._model_max_length = self._processor.tokenizer.model_max_length
            self._model = AutoModelForImageTextToText.from_pretrained(
                artifacts_path,
                device_map=self.device,
                dtype=torch.bfloat16,
                # The native granite4_vision Q-Former rejects an explicit sdpa
                # request before transformers 5.13; the transformers default
                # selects sdpa where the model supports it.
                _attn_implementation=(
                    "flash_attention_2"
                    if self.device.startswith("cuda")
                    and self.accelerator_options.cuda_use_flash_attention2
                    else None
                ),
                trust_remote_code=trust_remote_code,
            )
        self._model.eval()

    def _generation_budget(self, clusters: Sequence[Cluster]) -> int:
        """Max new tokens for one page's batch of table crops.

        The tokenizer's ``model_max_length`` is unset (~1e30), so it can't bound
        generation: a crop the model never closes (a boxed prompt laid out
        like a table) generated for over an hour. A table's OTSL output is its
        cell text plus tags; on 88 tables it never exceeded 3x the tokens of
        the PDF text in the crop + 512 (median 1.4x), and the 2048 floor
        covers image-only tables, whose crops have no PDF text. A crop that
        hits the budget is the model looping; its structure is taken from
        TableFormer (``tableformer_fallback``).
        """
        tokenizer = self._processor.tokenizer
        budget = 2048
        for cluster in clusters:
            text = " ".join(cell.text for cell in cluster.cells)
            budget = max(budget, 3 * len(tokenizer(text)["input_ids"]) + 512)
        return min(budget, self._model_max_length)

    def _truncated_cluster_ids(
        self,
        generated_ids: torch.Tensor,
        clusters: Sequence[Cluster],
        budget: int,
    ) -> set[int]:
        """Ids of the crops whose generation was cut off by *budget*: still
        going (last token neither EOS nor padding) when the batch hit it."""
        if generated_ids.shape[1] < budget:
            return set()
        tokenizer = self._processor.tokenizer
        finished = {tokenizer.eos_token_id, tokenizer.pad_token_id}
        return {
            cluster.id
            for row, cluster in zip(generated_ids, clusters)
            if int(row[-1]) not in finished
        }

    @cached_property
    def _tableformer(self) -> TableStructureModel:
        return TableStructureModel(
            enabled=True,
            artifacts_path=self._artifacts_path,
            options=TableStructureOptions(
                mode=TableFormerMode.ACCURATE, do_cell_matching=True
            ),
            accelerator_options=self.accelerator_options,
        )

    def _tableformer_prediction(
        self, conv_res: ConversionResult, page: Page, why: str
    ) -> TableStructurePrediction | None:
        """TableFormer's tables of *page* (it predicts every table of the
        page), or None when it cannot run."""
        if self._tableformer_unavailable:
            return None
        try:
            return self._tableformer.predict_tables(conv_res, [page])[0]
        except Exception:
            # Construction failures (no weights offline) would repeat on every
            # page; remember and stop trying.
            self._tableformer_unavailable = True
            _log.exception(
                "TableFormer failed on page %d; GraniteVision reads its tables (%s)",
                page.page_no,
                why,
            )
            return None

    def _reads_pdf_text(self, cluster: Cluster) -> bool:
        """Whether the table is TableFormer's to make: a table (not a table
        of contents) whose box holds text of the PDF rather than of OCR."""
        if not self.options.pdf_text_first or cluster.label != DocItemLabel.TABLE:
            return False
        printed = [cell for cell in cluster.cells if cell.text.strip()]
        from_pdf = sum(1 for cell in printed if not cell.from_ocr)
        return from_pdf > 0 and 2 * from_pdf >= len(printed)

    def _tables_from_pdf_text(
        self,
        conv_res: ConversionResult,
        page: Page,
        clusters: Sequence[Cluster],
    ) -> tuple[dict[int, Table], TableStructurePrediction | None]:
        """The tables of *clusters* that TableFormer makes, by cluster id, and
        its prediction for the page when it ran."""
        wanted = [cluster.id for cluster in clusters if self._reads_pdf_text(cluster)]
        if not wanted:
            return {}, None
        tableformer = self._tableformer_prediction(
            conv_res, page, f"tables {wanted} hold PDF text"
        )
        if tableformer is None:
            return {}, None
        tables: dict[int, Table] = {}
        for cid in wanted:
            table = tableformer.table_map.get(cid)
            if table is None:
                continue
            degenerate = degenerate_table_reason(
                table.num_rows, table.num_cols, table.table_cells
            )
            if degenerate is not None:
                _log.warning(
                    "TableFormer table [%s] on page %d: %s; read by GraniteVision",
                    cid,
                    page.page_no,
                    degenerate,
                )
                continue
            tables[cid] = table
        return tables, tableformer

    def _tableformer_fallback(
        self,
        conv_res: ConversionResult,
        page: Page,
        granite: TableStructurePrediction,
        reasons: dict[int, str],
        tableformer: TableStructurePrediction | None = None,
    ) -> TableStructurePrediction:
        """*granite* with TableFormer's structure for the tables in *reasons*
        (cluster id -> why Granite's is unusable), stored on *page*.

        TableFormer reads the PDF's text cells (cell matching), so these
        tables are not retyped from the image either. It predicts every table
        of the page (*tableformer*, when it already ran for the page); only
        the ones in *reasons* are kept.
        """
        if tableformer is None:
            tableformer = self._tableformer_prediction(
                conv_res,
                page,
                "; ".join(f"[{cid}] {reason}" for cid, reason in reasons.items()),
            )
        if tableformer is None:
            page.predictions.tablestructure = granite
            return granite
        usable: set[int] = set()
        for cid, reason in reasons.items():
            replacement = tableformer.table_map.get(cid)
            if replacement is None:
                continue
            also_degenerate = degenerate_table_reason(
                replacement.num_rows, replacement.num_cols, replacement.table_cells
            )
            if also_degenerate is not None:
                _log.warning(
                    "GraniteVision table [%s] on page %d: %s; TableFormer's is "
                    "also unusable (%s), keeping GraniteVision's",
                    cid,
                    page.page_no,
                    reason,
                    also_degenerate,
                )
                continue
            usable.add(cid)
            _log.warning(
                "GraniteVision table [%s] on page %d: %s; structure taken "
                "from TableFormer",
                cid,
                page.page_no,
                reason,
            )
        merged = merge_table_predictions(granite, tableformer, usable)
        page.predictions.tablestructure = merged
        return merged

    def predict_tables(
        self,
        conv_res: ConversionResult,
        pages: Sequence[Page],
    ) -> Sequence[TableStructurePrediction]:
        predictions: list[TableStructurePrediction] = []

        for page in pages:
            assert page._backend is not None
            if not page._backend.is_valid():
                existing = page.predictions.tablestructure or TableStructurePrediction()
                page.predictions.tablestructure = existing
                predictions.append(existing)
                continue

            assert page.predictions.layout is not None
            assert page.size is not None
            table_prediction = TableStructurePrediction()
            clusters = [
                c
                for c in page.predictions.layout.clusters
                if c.label in (DocItemLabel.TABLE, DocItemLabel.DOCUMENT_INDEX)
            ]
            if not clusters or not self.enabled:
                page.predictions.tablestructure = table_prediction
                predictions.append(table_prediction)
                continue

            # TableFormer records its own table_structure time.
            from_pdf_text, tableformer = self._tables_from_pdf_text(
                conv_res, page, clusters
            )
            granite_clusters = [c for c in clusters if c.id not in from_pdf_text]
            granite_tables: dict[int, Table] = {}
            truncated: set[int] = set()
            budget = 0
            if granite_clusters:
                with TimeRecorder(conv_res, "table_structure"):
                    granite_tables, truncated, budget = self._granite_tables(
                        page, granite_clusters
                    )
            table_prediction.table_map = {
                cluster.id: table
                for cluster in clusters
                if (
                    table := from_pdf_text.get(cluster.id)
                    or granite_tables.get(cluster.id)
                )
                is not None
            }
            page.predictions.tablestructure = table_prediction

            reasons: dict[int, str] = {}
            for cid, tbl in granite_tables.items():
                if cid in truncated:
                    reasons[cid] = f"hit the {budget}-token generation budget"
                elif (
                    degenerate := degenerate_table_reason(
                        tbl.num_rows, tbl.num_cols, tbl.table_cells
                    )
                ) is not None:
                    reasons[cid] = f"{tbl.num_rows}x{tbl.num_cols} grid, {degenerate}"
                elif (
                    held := pdf_words_held(tbl)
                ) is not None and held < MIN_PDF_WORDS_HELD:
                    reasons[cid] = (
                        f"holds {held:.2f} of the words the PDF prints in its box"
                    )
            if reasons and self.options.tableformer_fallback:
                table_prediction = self._tableformer_fallback(
                    conv_res, page, table_prediction, reasons, tableformer
                )
            else:
                for cid in sorted(truncated):
                    _log.warning(
                        "GraniteVision table [%s] on page %d hit the %d-token "
                        "generation budget; its structure is truncated",
                        cid,
                        page.page_no,
                        budget,
                    )
            predictions.append(table_prediction)

        return predictions

    def _granite_tables(
        self, page: Page, clusters: Sequence[Cluster]
    ) -> tuple[dict[int, Table], set[int], int]:
        """Granite-Vision's tables of *clusters* by cluster id, the ids whose
        generation was cut off, and the token budget of the batch."""
        # Crop one image per table cluster from the page image
        valid_pairs = []
        for cluster in clusters:
            crop = page.get_image(scale=1.0, cropbox=cluster.bbox)
            if crop is not None:
                valid_pairs.append((cluster, crop))
        if not valid_pairs:
            return {}, set(), 0

        valid_clusters, valid_images = zip(*valid_pairs)
        conversations = [
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": "<tables_otsl>"},
                    ],
                }
            ]
            for _ in valid_images
        ]
        texts = [
            self._processor.apply_chat_template(
                conv, tokenize=False, add_generation_prompt=True
            )
            for conv in conversations
        ]
        inputs = self._processor(
            text=texts,
            images=list(valid_images),
            return_tensors="pt",
            padding=True,
            do_pad=True,
        ).to(self.device)

        budget = self._generation_budget(valid_clusters)
        output_ids = cast(Any, self._model).generate(
            **inputs,
            max_new_tokens=budget,
            use_cache=True,
        )
        truncated = self._truncated_cluster_ids(
            output_ids[:, inputs["input_ids"].shape[1] :],
            valid_clusters,
            budget,
        )
        # Decode only generated tokens (strip input prompt tokens)
        output_texts = [
            self._processor.decode(
                output_ids[i, inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )
            for i in range(len(valid_images))
        ]

        tables: dict[int, Table] = {}
        for cluster, raw_text in zip(valid_clusters, output_texts):
            _log.debug(f"GraniteVision table [{cluster.id}] raw output: {raw_text!r}")
            try:
                otsl_seq, table_cells, num_rows, num_cols = parse_otsl_output(raw_text)
            except Exception as exc:
                _log.warning(
                    f"Failed to parse OTSL output for table cluster {cluster.id}: {exc}"
                )
                otsl_seq, table_cells, num_rows, num_cols = [], [], 0, 0
            tables[cluster.id] = Table(
                otsl_seq=otsl_seq,
                table_cells=table_cells,
                num_rows=num_rows,
                num_cols=num_cols,
                id=cluster.id,
                page_no=page.page_no,
                cluster=cluster,
                label=cluster.label,
            )
        return tables, truncated, budget
