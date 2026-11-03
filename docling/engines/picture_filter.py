# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Mark non-content pictures (logos, watermarks, repeated banners) as noise.

Two complementary signals:

1. **Classifier label** — when the picture classifier
   (``DocumentPictureClassifier``) ran, any picture whose predicted class
   is in :data:`DEFAULT_NOISE_CLASSES` (configurable) is flagged — but only
   if it covers less than :data:`DEFAULT_MAX_CLASSIFIER_NOISE_AREA` of its
   page, since a large picture is content even when mislabelled, and not
   when BiomedCLIP (:mod:`docling.engines.figure_typing`) confidently calls
   it a medical image (:data:`IMAGING_FIGURE_TYPES`): the generic
   classifier labels small echo frames inside a composite figure ``icon``
   or ``logo``.
2. **Repeated-bbox heuristic** — if the same picture geometry appears on
   ``repeat_threshold`` or more pages, it's almost certainly a journal
   header / logo / running banner. Works even when the classifier didn't
   run, and catches journal headers the classifier may label as
   ``"natural_image"``.

The filter only **annotates** pictures — it never deletes data. Callers
choose how to use the flags (skip in markdown, dim in preview, etc.).
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from docling_core.types.doc import PictureItem

from docling.engines.figure_typing import get_figure_type

if TYPE_CHECKING:
    from docling.datamodel.document import ConversionResult

_log = logging.getLogger(__name__)

# Common "noise" classes a document-figure classifier might emit. The exact
# label set depends on the underlying model — keep this list configurable
# rather than hard-coded. DocumentFigureClassifier-v2.5 emits ``bar_code``
# (not ``barcode``) and ``icon`` for CC-BY / ORCID / "Check for updates"
# badges.
DEFAULT_NOISE_CLASSES: frozenset[str] = frozenset(
    {
        "logo",
        "icon",
        "watermark",
        "signature",
        "stamp",
        "seal",
        "barcode",
        "bar_code",
        "qr_code",
        "page_header",
        "page_footer",
    }
)

DEFAULT_REPEAT_THRESHOLD = 3  # >=3 pages with same bbox → repeated banner.
DEFAULT_MIN_AREA = 0  # off by default; opt-in tiny-picture filter.
# A classifier noise label only counts below this fraction of the page area.
# Logos / badges / QR codes in 25 medical papers covered <= 1.65 %; the
# generic classifier called an 8 % 3-D CT rendering ``icon``.
DEFAULT_MAX_CLASSIFIER_NOISE_AREA = 0.05

# BiomedCLIP types that overrule a classifier noise label at or above
# IMAGING_VETO_CONFIDENCE. Checked on all 68 classifier-hidden pictures in 37
# papers: the 6 real ones (echo frames) scored ultrasound >= 0.95, while a QR
# code scored ultrasound 0.85. ``ecg`` and ``nuclear_medicine`` stay out:
# Springer logos score ecg 1.00 and a "Check for updates" badge
# nuclear_medicine 0.93.
IMAGING_FIGURE_TYPES: frozenset[str] = frozenset(
    {
        "radiograph",
        "ct",
        "mri",
        "ultrasound",
        "angiography",
        "ophthalmic_imaging",
        "histopathology",
        "endoscopy",
    }
)
IMAGING_VETO_CONFIDENCE = 0.9


@dataclass
class PictureNoiseFlag:
    """One row per picture, in ``iterate_items()`` order."""

    self_ref: str | None
    is_noise: bool
    noise_reason: str | None
    classifier_label: str | None


def classify_pictures(
    result: ConversionResult,
    *,
    noise_classes: frozenset[str] = DEFAULT_NOISE_CLASSES,
    repeat_threshold: int = DEFAULT_REPEAT_THRESHOLD,
    min_area: float = DEFAULT_MIN_AREA,
    max_classifier_noise_area: float = DEFAULT_MAX_CLASSIFIER_NOISE_AREA,
) -> list[PictureNoiseFlag]:
    """Walk pictures and emit one :class:`PictureNoiseFlag` per item."""
    if result.document is None:
        return []

    pictures: list[PictureItem] = [
        item
        for item, _level in result.document.iterate_items()
        if isinstance(item, PictureItem)
    ]

    bbox_signatures = _collect_bbox_signatures(pictures)
    flags: list[PictureNoiseFlag] = []
    for pic in pictures:
        label = _classifier_label(pic)
        reason: str | None = None

        if label and label.lower() in {c.lower() for c in noise_classes}:
            page_frac = _page_area_fraction(pic, result.document)
            small = page_frac is None or page_frac < max_classifier_noise_area
            if small and not _is_confident_medical_image(pic):
                reason = f"classifier:{label}"
        if reason is None:
            sig = _picture_bbox_signature(pic)
            if sig is not None and bbox_signatures[sig] >= repeat_threshold:
                reason = f"repeated_bbox:{bbox_signatures[sig]}_pages"
            elif min_area > 0:
                area = _picture_area(pic)
                if area is not None and area < min_area:
                    reason = f"small_area:{area:.0f}"

        flags.append(
            PictureNoiseFlag(
                self_ref=getattr(pic, "self_ref", None),
                is_noise=reason is not None,
                noise_reason=reason,
                classifier_label=label,
            )
        )
    n_noise = sum(1 for f in flags if f.is_noise)
    if pictures:
        _log.info(
            "Picture filter: %d / %d flagged as noise (classes=%d, threshold=%d)",
            n_noise,
            len(pictures),
            len(noise_classes),
            repeat_threshold,
        )
    return flags


def _is_confident_medical_image(item: PictureItem) -> bool:
    prediction = get_figure_type(item)
    return (
        prediction is not None
        and prediction.label in IMAGING_FIGURE_TYPES
        and prediction.confidence >= IMAGING_VETO_CONFIDENCE
    )


def _classifier_label(item: PictureItem) -> str | None:
    """Pull the top-1 predicted class from any classifier annotation."""
    for ann in getattr(item, "annotations", None) or []:
        kind = (getattr(ann, "kind", None) or type(ann).__name__).lower()
        if "classification" in kind or "classifier" in kind:
            preds = getattr(ann, "predicted_classes", None) or getattr(
                ann, "predictions", None
            )
            if preds:
                first = preds[0]
                label = getattr(first, "class_name", None) or getattr(
                    first, "label", None
                )
                if label:
                    return label
    return None


def _picture_bbox_signature(item: PictureItem) -> tuple | None:
    """Round bbox to 2-pt grid so near-identical headers across pages match."""
    prov_list = getattr(item, "prov", None) or []
    if not prov_list:
        return None
    bbox = prov_list[0].bbox
    if bbox is None:
        return None
    return (round(bbox.l / 2), round(bbox.t / 2), round(bbox.r / 2), round(bbox.b / 2))


def _page_area_fraction(item: PictureItem, doc) -> float | None:
    area = _picture_area(item)
    if area is None:
        return None
    page = doc.pages.get(item.prov[0].page_no)
    if page is None or page.size is None:
        return None
    return area / (page.size.width * page.size.height)


def _picture_area(item: PictureItem) -> float | None:
    prov_list = getattr(item, "prov", None) or []
    if not prov_list:
        return None
    bbox = prov_list[0].bbox
    if bbox is None:
        return None
    return abs((bbox.r - bbox.l) * (bbox.b - bbox.t))


def _collect_bbox_signatures(pictures: list[PictureItem]) -> Counter:
    sigs: Counter = Counter()
    for pic in pictures:
        sig = _picture_bbox_signature(pic)
        if sig is not None:
            sigs[sig] += 1
    return sigs
