# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""VLM presets for the Amir Engine.

Docling ships picture-description presets for ``smolvlm``, ``granite_vision``
and ``pixtral``. We add ``qwen25_vl_3b`` here so a future swap to Qwen3-VL is
a one-line edit (change the ``default_repo_id``).

Use :func:`build_picture_description_options` from
:class:`docling.engines.PdfEngine` via the ``picture_description=`` flag.
"""

from __future__ import annotations

from typing import Literal

from docling.datamodel.pipeline_options import (
    PictureDescriptionVlmEngineOptions,
    PictureDescriptionVlmOptions,
)
from docling.datamodel.pipeline_options_vlm_model import (
    ResponseFormat,
    TransformersModelType,
)
from docling.datamodel.stage_model_specs import EngineModelConfig, VlmModelSpec
from docling.datamodel.vlm_engine_options import (
    AutoInlineVlmEngineOptions,
    BaseVlmEngineOptions,
    TransformersVlmEngineOptions,
    VllmVlmEngineOptions,
    VlmEngineType,
)

PictureDescriptionPreset = Literal[
    "smolvlm",
    "granite_vision",
    "granite_vision_4b",
    "pixtral",
    "qwen25_vl_3b",
]
PictureDescriptionEngine = Literal["vllm", "transformers", "default"]

# Custom Qwen2.5-VL-3B model spec — Docling's bundled Qwen preset is for the
# full-page VlmConvert stage, not picture description, so we declare our own.
QWEN25_VL_3B_PICTURE_DESC_SPEC = VlmModelSpec(
    name="Qwen2.5-VL-3B-Instruct",
    default_repo_id="Qwen/Qwen2.5-VL-3B-Instruct",
    prompt="Describe this image in one or two concise sentences. Be specific and factual.",
    response_format=ResponseFormat.MARKDOWN,
    max_new_tokens=200,
    extra_generation_config={"skip_special_tokens": True},
)

# Granite-Vision 4.1 4B — newest IBM document-vision model. Docling ships a
# bundled spec for it (`GRANITE_VISION_4_1_TRANSFORMERS`) but only registers
# the 3.3-2B variant as a picture-description preset, so we declare our own.
# Model settings mirror upstream's CHART_EXTRACTION_GRANITE_VISION_V4 spec
# (pinned revision, bfloat16, remote code). It needs
# AutoModelForImageTextToText (not the bare AutoModel default), since only the
# *ForConditionalGeneration class exposes .generate().
GRANITE_VISION_4B_PICTURE_DESC_SPEC = VlmModelSpec(
    name="Granite-Vision-4.1-4B",
    default_repo_id="ibm-granite/granite-vision-4.1-4b",
    revision="dd48e97503de471803850df70843cf9eb5da8712",
    prompt="What is shown in this image? Describe it in 1-2 concise factual sentences.",
    response_format=ResponseFormat.PLAINTEXT,
    max_new_tokens=200,
    trust_remote_code=True,
    # Docling's engines decode with special tokens kept unless asked; the
    # model's EOS token <|end_of_text|> then ended every caption.
    extra_generation_config={"skip_special_tokens": True},
    engine_overrides={
        VlmEngineType.TRANSFORMERS: EngineModelConfig(
            torch_dtype="bfloat16",
            extra_config={
                "transformers_model_type": TransformersModelType.AUTOMODEL_IMAGETEXTTOTEXT,
            },
        ),
    },
)


def build_picture_description_options(
    preset: PictureDescriptionPreset,
    *,
    engine: PictureDescriptionEngine = "vllm",
) -> PictureDescriptionVlmEngineOptions | PictureDescriptionVlmOptions:
    """Construct picture-description options for the chosen preset.

    For ``qwen25_vl_3b`` we build a fresh :class:`PictureDescriptionVlmEngineOptions`
    with the Qwen model spec; for everything else we use Docling's registered
    preset via ``from_preset``. The ``engine`` argument selects the runtime
    (``vllm`` for high-throughput serving, ``transformers`` for direct HF
    inference, ``default`` to let Docling decide).
    """
    engine_opts = _engine_options(engine)

    if preset == "qwen25_vl_3b":
        return PictureDescriptionVlmEngineOptions(
            model_spec=QWEN25_VL_3B_PICTURE_DESC_SPEC,
            engine_options=engine_opts,
        )

    if preset == "granite_vision_4b":
        return PictureDescriptionVlmEngineOptions(
            model_spec=GRANITE_VISION_4B_PICTURE_DESC_SPEC,
            engine_options=engine_opts,
        )

    return PictureDescriptionVlmEngineOptions.from_preset(
        preset, engine_options=engine_opts
    )


def _engine_options(engine: PictureDescriptionEngine) -> BaseVlmEngineOptions:
    """Translate engine name → engine options.

    ``"default"`` returns :class:`AutoInlineVlmEngineOptions` so Docling's
    auto-selector picks the best available runtime (vLLM if installed, then
    transformers). ``"vllm"`` and ``"transformers"`` force the choice.
    """
    if engine == "vllm":
        return VllmVlmEngineOptions(engine_type=VlmEngineType.VLLM)
    if engine == "transformers":
        return TransformersVlmEngineOptions(engine_type=VlmEngineType.TRANSFORMERS)
    return AutoInlineVlmEngineOptions(engine_type=VlmEngineType.AUTO_INLINE)
