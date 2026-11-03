# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Domain-aware figure types for scientific and medical PDFs.

Docling's bundled ``DocumentFigureClassifier`` predicts generic document
classes (``bar_chart``, ``logo``, ``photograph``, ``engineering_drawing``...)
and has no medical-imaging classes: it labels an ECG ``line_chart`` and a
coronary angiogram ``photograph``. It stays in use for the noise filter
(logos, QR codes, icons) — that is what it is good at — while this module
supplies the *content* type.

`BiomedCLIP <https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224>`_
(trained on 15M PubMed Central figure-caption pairs) scores every picture
zero-shot against :data:`FIGURE_TYPES`. On a 97-figure hand-labelled sample
(cardiology case reports + medical-AI papers) it was right for 83.5 % of
figures (87.6 % also accepting a valid alternate, e.g. ``angiography`` for a
CT angiogram), against 16.5 % for the generic classifier, at ~15 ms and
~0.8 GB GPU per figure. Asking Granite-Vision-4.1-4B for the type alongside
its description scored 79.4 % / 84.5 % at ~1.1 s per figure, so BiomedCLIP
runs in every config whether or not a description VLM is on.

Predictions are stored on ``PictureItem.meta`` under the custom field
``amir__figure_type`` so they round-trip through ``document.json``.
"""

from __future__ import annotations

import functools
import importlib.util
import logging
from typing import TYPE_CHECKING, Any

from docling_core.types.doc import PictureItem
from docling_core.types.doc.document import MetaUtils, PictureMeta
from pydantic import BaseModel

from docling.datamodel.accelerator_options import AcceleratorDevice
from docling.engines.text_repair import TABLE_PDF_TEXT_META_KEY
from docling.utils.accelerator_utils import decide_device

if TYPE_CHECKING:
    from PIL.Image import Image

    from docling.datamodel.document import ConversionResult

_log = logging.getLogger(__name__)

BIOMEDCLIP_REPO = "microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"

# Label -> phrase the text encoder sees. The phrases were fixed before the
# evaluation above; re-measure if you edit them.
FIGURE_TYPES: dict[str, str] = {
    "ecg": "an electrocardiogram (ECG) tracing",
    "radiograph": "a plain X-ray radiograph",
    "ct": "a computed tomography (CT) scan",
    "mri": "a magnetic resonance imaging (MRI) scan",
    "ultrasound": "an ultrasound or echocardiography image",
    "angiography": "a catheter angiography fluoroscopy image of blood vessels",
    "nuclear_medicine": "a nuclear medicine scan such as scintigraphy, SPECT or PET",
    "ophthalmic_imaging": "a retinal fundus photograph or OCT scan of the eye",
    "histopathology": "a histopathology microscopy image of stained tissue",
    "endoscopy": "an endoscopy image",
    "clinical_photo": "a clinical photograph of a patient or lesion",
    "medical_illustration": "a medical illustration or anatomical drawing",
    "flow_diagram": "a flowchart or diagram with boxes and arrows",
    "bar_chart": "a bar chart",
    "line_chart": "a line chart",
    "scatter_plot": "a scatter plot",
    "box_plot": "a box plot",
    "kaplan_meier": "a Kaplan-Meier survival curve",
    "forest_plot": "a forest plot",
    "roc_curve": "a ROC curve",
    "heatmap": "a heatmap or confusion matrix",
    "table_image": "a table of text and numbers",
    "other": "a logo, icon, or photograph of a person",
}
_PROMPT_TEMPLATES = ("this is {}", "a figure showing {}", "{}")
_CONTEXT_LENGTH = 256
_BATCH_SIZE = 32

_META_NAMESPACE = "amir"
_META_NAME = "figure_type"
META_KEY = MetaUtils.create_meta_field_name(namespace=_META_NAMESPACE, name=_META_NAME)

# Serializer params for text exports (markdown, chunks): leave model-guessed
# picture labels out of the text. docling-core would otherwise append the
# generic classifier label ("Line chart" under an ECG) and the repr of
# META_KEY's dict to every picture; both stay available as structured data in
# figures.jsonl / document.json.
TEXT_EXPORT_META_PARAMS: dict[str, Any] = {
    "include_picture_classification": False,
    # TABLE_PDF_TEXT_META_KEY: a table box's PDF text, kept for the HTML only.
    "blocked_meta_names": {META_KEY, TABLE_PDF_TEXT_META_KEY},
}


class FigureTypePrediction(BaseModel):
    """Top-1 figure type for one picture."""

    label: str
    confidence: float
    model: str = BIOMEDCLIP_REPO


class FigureTyper:
    """Zero-shot BiomedCLIP figure typer; weights load on first use."""

    def __init__(self, device: str = AcceleratorDevice.AUTO.value) -> None:
        if importlib.util.find_spec("open_clip") is None:
            raise ImportError(
                "Figure typing needs open-clip-torch. Install it with "
                "`uv sync --extra models-vlm-inline` (see README), or pass "
                "figure_types=False / --no-figure-types."
            )
        self._device = decide_device(device)

    def classify(self, images: list[Image]) -> list[FigureTypePrediction]:
        import torch

        model, preprocess, text_features = _load_biomedclip(self._device)
        labels = list(FIGURE_TYPES)
        predictions: list[FigureTypePrediction] = []
        with torch.inference_mode():
            for start in range(0, len(images), _BATCH_SIZE):
                batch = torch.stack(
                    [
                        preprocess(img.convert("RGB"))
                        for img in images[start : start + _BATCH_SIZE]
                    ]
                ).to(self._device)
                feats = model.encode_image(batch)
                feats = feats / feats.norm(dim=-1, keepdim=True)
                probs = (model.logit_scale.exp() * feats @ text_features.T).softmax(-1)
                conf, idx = probs.max(dim=-1)
                predictions.extend(
                    FigureTypePrediction(label=labels[i], confidence=round(c, 4))
                    for i, c in zip(idx.tolist(), conf.tolist(), strict=True)
                )
        return predictions


@functools.cache
def _load_biomedclip(device: str) -> tuple[Any, Any, Any]:
    """Load model + preprocess once per process and pre-encode the label prompts.

    Prompt-ensembled: each label's text embedding is the normalised mean over
    :data:`_PROMPT_TEMPLATES`.
    """
    import open_clip
    import torch

    name = f"hf-hub:{BIOMEDCLIP_REPO}"
    model, preprocess = open_clip.create_model_from_pretrained(name)
    tokenizer = open_clip.get_tokenizer(name)
    model = model.to(device).eval()
    with torch.inference_mode():
        per_label = []
        for phrase in FIGURE_TYPES.values():
            tokens = tokenizer(
                [tpl.format(phrase) for tpl in _PROMPT_TEMPLATES],
                context_length=_CONTEXT_LENGTH,
            ).to(device)
            emb = model.encode_text(tokens)
            emb = emb / emb.norm(dim=-1, keepdim=True)
            mean = emb.mean(dim=0)
            per_label.append(mean / mean.norm())
        text_features = torch.stack(per_label)
    _log.info("Loaded BiomedCLIP figure typer on %s", device)
    return model, preprocess, text_features


def type_pictures(result: ConversionResult, typer: FigureTyper) -> int:
    """Store a :class:`FigureTypePrediction` on every picture that has an image.

    Pictures only carry images when the pipeline ran with
    ``generate_picture_images=True``; others are left untouched. Returns the
    number of pictures typed.
    """
    doc = result.document
    typed: list[tuple[PictureItem, Image]] = []
    for item, _level in doc.iterate_items():
        if isinstance(item, PictureItem):
            image = item.get_image(doc)
            if image is not None:
                typed.append((item, image))
    if not typed:
        return 0

    predictions = typer.classify([image for _, image in typed])
    for (item, _image), pred in zip(typed, predictions, strict=True):
        if item.meta is None:
            item.meta = PictureMeta()
        item.meta.set_custom_field(_META_NAMESPACE, _META_NAME, pred.model_dump())
    return len(typed)


def get_figure_type(item: PictureItem) -> FigureTypePrediction | None:
    """Read back the prediction (works on live and JSON-reloaded documents)."""
    if item.meta is None:
        return None
    raw = item.meta.get_custom_part().get(META_KEY)
    return FigureTypePrediction.model_validate(raw) if raw is not None else None
