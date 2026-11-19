"""Split the figures with FigEx2 (Song et al., EMNLP 2026).

    <figex2 python> .../scripts/run_figex2.py --code <FigEx2 checkout> \\
        --weights <FigEx2-8B folder> --base <Qwen3-VL-8B-Instruct folder>

FigEx2 is two models that work as one. A captioning model (Qwen3-VL-8B
with the authors' adapters) lists the panels of a compound figure by their
printed letters and writes a caption for each; a detector (DAB-DETR, 26
classes, the letters A to Z) draws at most one box per letter, guided by
the captioning model's hidden states. This script runs both the authors'
way (their ``inference.py`` functions, their prompt, greedy decoding) and
the detector once more without the captioning model's features.

It needs the authors' pinned ``transformers`` and ``peft``, which the
project environment does not have: run it with a separate environment (see
the README). Images are scaled down to a long side of 1,024 px, the size
of the figures FigEx2 was trained on.

Writes ``candidates/figex2-raw.json`` (captions, every detection) and three
candidates read from it:

- ``figex2``: as designed, the box of each letter the captioning model
  lists;
- ``figex2-scored``: the guided detector by itself, its boxes with a score
  of at least 0.5, whatever the captions list;
- ``figex2-detector``: the detector without the captioning model, score at
  least 0.5.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import torch
from common import figures, image_path, to_grid, write_candidate
from PIL import Image

MAX_SIDE = 1024
SCORE = 0.5
KEEP_FROM = 0.02  # detections under this score are not recorded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()

    for folder in (args.code, args.weights, args.base):
        if not folder.is_dir():
            raise SystemExit(f"not a folder: {folder}")
    # Everything is read from the three folders. Offline mode makes any
    # other lookup fail instead of reaching the hub: the authors' loaders
    # pass trust_remote_code=True, which has nothing to run in the reviewed
    # folders and must not be given a repository to fetch from.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    sys.path.insert(0, str(args.code))
    from inference import build_detector, build_lm, parse_subcaptions, run_detector
    from model.FigEx2_dab_detr import PROMPT_COMPOUND

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    started = time.perf_counter()
    tokenizer, processor, lm = build_lm(
        str(args.base), args.weights / "vlm", device=device, dtype=dtype
    )
    # The second argument is the authors' fallback when the detector folder
    # has no image processor: the same local folder here, never a hub id.
    det_processor, det_model = build_detector(
        args.weights / "detector", str(args.weights / "detector"), device=device
    )
    print(f"models loaded in {time.perf_counter() - started:.0f} s", flush=True)

    raw: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as work:
        for figure in figures():
            if args.only and figure["id"] not in args.only:
                continue
            image = Image.open(image_path(figure)).convert("RGB")
            image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
            scaled = Path(work) / f"{figure['id']}.png"
            image.save(scaled)

            started = time.perf_counter()
            text, det_feats, text_feats, _ = lm.evaluate(
                qwen_processor=processor,
                tokenizer=tokenizer,
                image_path=str(scaled),
                device=device,
                max_new_tokens=1024,
                prompt=PROMPT_COMPOUND,
                return_generation_details=True,
            )
            caption_s = time.perf_counter() - started
            captions = parse_subcaptions(text)

            def detect(
                det: torch.Tensor | None, txt: torch.Tensor | None
            ) -> list[dict]:
                boxes, scores, labels, _ = run_detector(
                    det_processor=det_processor,
                    det_model=det_model,
                    image=image,
                    det_feats=det,
                    text_feats=txt,
                    device=device,
                    score_threshold=KEEP_FROM,
                    max_det=300,
                )
                return [
                    {
                        "letter": chr(ord("A") + int(label)),
                        "score": round(float(score), 4),
                        "box": to_grid(
                            [float(v) for v in box], image.width, image.height
                        ),
                    }
                    for box, score, label in zip(boxes, scores, labels)
                ]

            started = time.perf_counter()
            guided = detect(det_feats, text_feats)
            detector_s = time.perf_counter() - started
            alone = detect(None, None)
            raw[figure["id"]] = {
                "captions": captions,
                "reply": text,
                "guided": guided,
                "alone": alone,
                "caption_seconds": round(caption_s, 2),
                "detector_seconds": round(detector_s, 3),
            }
            print(
                figure["id"],
                f"letters {''.join(sorted(captions)) or '-'}",
                f"guided>={SCORE}: {sum(d['score'] >= SCORE for d in guided)}",
                f"alone>={SCORE}: {sum(d['score'] >= SCORE for d in alone)}",
                f"{caption_s:.1f} s",
                flush=True,
            )

    def reading_order(found: list[dict]) -> list[dict]:
        return sorted(found, key=lambda d: (round(d["box"][1] / 100), d["box"][0]))

    as_designed: dict[str, dict] = {}
    scored: dict[str, dict] = {}
    detector: dict[str, dict] = {}
    for figure_id, row in raw.items():
        by_letter = {d["letter"]: d for d in row["guided"]}
        listed = reading_order(
            [
                by_letter[letter]
                for letter in sorted(row["captions"])
                if letter in by_letter
            ]
        )
        as_designed[figure_id] = {
            "boxes": [d["box"] for d in listed],
            "labels": [d["letter"] for d in listed],
            "listed": sorted(row["captions"]),
            "seconds": round(row["caption_seconds"] + row["detector_seconds"], 2),
        }
        for target, key in ((scored, "guided"), (detector, "alone")):
            kept = reading_order([d for d in row[key] if d["score"] >= SCORE])
            target[figure_id] = {
                "boxes": [d["box"] for d in kept],
                "labels": [d["letter"] for d in kept],
                "seconds": row["detector_seconds"],
            }
    if args.only:
        return
    write_candidate(
        "figex2-raw",
        "FigEx2-8B: the captions of its captioning model and every box of its "
        "detector (at most one per letter, score from 0.02), with the "
        "captioning model's features (guided) and without (alone). Not a "
        "candidate by itself.",
        raw,
    )
    write_candidate(
        "figex2",
        "FigEx2-8B as designed: the detector's box for each panel letter its "
        "captioning model lists.",
        as_designed,
    )
    write_candidate(
        "figex2-scored",
        f"FigEx2-8B's detector guided by its captioning model: boxes with a score "
        f"of at least {SCORE}, whatever the captions list.",
        scored,
    )
    write_candidate(
        "figex2-detector",
        f"FigEx2-8B's detector alone (93 MB, no captioning model): boxes with a "
        f"score of at least {SCORE}.",
        detector,
    )


if __name__ == "__main__":
    main()
