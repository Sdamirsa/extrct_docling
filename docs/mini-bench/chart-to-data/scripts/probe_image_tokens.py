# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""How many prompt tokens one image costs an Ollama vision model, by size.

    uv run --no-sync python docs/mini-bench/chart-to-data/scripts/probe_image_tokens.py \
        <image.png> <ollama model> [<ollama model> ...]

The same image is resized to a ladder of sizes and sent with a three-word
prompt; the image's cost is the prompt-token count minus that of the prompt
alone. A model whose count stops growing has a fixed budget per image, and
sending it a larger image buys no detail: cut the figure up instead.
"""

from __future__ import annotations

import base64
import io
import sys

import httpx
from PIL import Image

SIZES = [
    (224, 224),
    (448, 448),
    (672, 672),
    (896, 896),
    (1344, 1344),
    (2048, 2048),
    (4096, 4096),
    (1600, 280),
    (3200, 2472),
]


def prompt_tokens(http: httpx.Client, model: str, image: Image.Image | None) -> int:
    message: dict[str, object] = {"role": "user", "content": "Say ok."}
    if image is not None:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        message["images"] = [base64.b64encode(buffer.getvalue()).decode("ascii")]
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "keep_alive": "5m",
        "options": {"num_ctx": 32768, "num_predict": 8, "temperature": 0},
        "messages": [message],
    }
    return int(http.post("/api/chat", json=body).json()["prompt_eval_count"])


def main() -> None:
    image = Image.open(sys.argv[1]).convert("RGB")
    http = httpx.Client(base_url="http://127.0.0.1:11434", timeout=600)
    for model in sys.argv[2:]:
        text_only = prompt_tokens(http, model, None)
        costs = [
            f"{w}x{h}={prompt_tokens(http, model, image.resize((w, h))) - text_only}"
            for w, h in SIZES
        ]
        print(model, " ".join(costs), flush=True)
        http.post("/api/generate", json={"model": model, "keep_alive": 0, "prompt": ""})


if __name__ == "__main__":
    main()
