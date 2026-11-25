# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""What a PDF went through, drawn from its bundle's own files.

- ``provenance.html``: every step of the conversion in the order it ran,
  grouped in phases, one card each: what it does, who wrote it (Docling as
  released, Docling as patched in this fork, or the Amir Engine), its model,
  key settings and every recorded one, and what it produced. A step the
  options turned off is drawn as skipped, with the reason. The steps are
  embedded as JSON in ``<script id="extrct-provenance">`` for agents.
- ``methods.md``: a methods paragraph and a software list for a paper.

Both read ``run.json``, ``check.json``, ``structure.json`` and
``figures.jsonl`` only, never the code that ran: a step whose record a
bundle lacks (an earlier release did not write it) says "not recorded".
The fixed prose is package data under ``templates/``: the page
(``provenance.html``), the step catalogue (``provenance_steps.json``) and
the methods paragraph (``methods.md``, ``string.Template``), whose optional
sentences (``$text_layer``, ``$parser_repair``, ``$ocr``, ``$tables``,
``$figures``, ``$descriptions``, ``$structure``, ``$check``,
``$figure_data``) are filled here with a sentence or an empty string.
"""

from __future__ import annotations

import functools
import html
import json
import re
import string
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter

from docling.engines.export_check import CHECK_FILENAME
from docling.engines.figure_data.evidence import FIGURES_FILENAME
from docling.engines.run_snapshot import (
    ENGINE_VERSION,
    RUN_JSON_FILENAME,
    write_text_atomic,
)
from docling.engines.schemas import (
    BundleProvenance,
    ProvenanceOwner,
    ProvenancePhase,
    ProvenanceStep,
)
from docling.engines.structure import STRUCTURE_FILENAME

PROVENANCE_FILENAME = "provenance.html"
METHODS_FILENAME = "methods.md"
PROVENANCE_SCRIPT_ID = "extrct-provenance"

_NOT_IN_RUN = "not recorded in this bundle's run.json"
_OCR_BASE_KEYS = frozenset({"mode", "lang", "scale", "force_full_page_ocr"})
_TABLE_MODELS = {"tableformer": "TableFormer", "granite_vision": "Granite-Vision"}
_GRANITE = "Granite-Vision 4.1-4B"
# The table option block names no model; this is the repo the code loads.
_GRANITE_REPO = "ibm-granite/granite-vision-4.1-4b"
_LIST_LIMIT = 40
_ENGINE_COMPONENTS = {
    "text_repairs": ("vlm_stop_tokens", "ligature_repair", "table_pdf_text"),
    "structure": ("structure",),
    "quality": ("quality",),
    "figure_types": ("figure_typing",),
    "noise_filter": ("picture_filter",),
    "exports": (
        "artifacts",
        "chunker",
        "structured_outputs",
        "export_to_markdown",
        "markdown",
        "export_to_markdown_embedded",
        "visualizer",
        "html_export",
        "run_snapshot",
    ),
    "self_check": ("export_check",),
}
_PHASES: dict[ProvenancePhase, tuple[str, str]] = {
    "read": ("Read the PDF", "Docling's PDF pipeline"),
    "page": ("Understand the page", "Docling's PDF pipeline"),
    "figures": ("Figures", "Docling's enrichment models, on the assembled document"),
    "cleanup": ("Clean-up and structure", "Amir Engine, after Docling's conversion"),
    "write": ("Write and check", "Amir Engine"),
    "figure_data": ("Figure to data", "a step of its own, run on the finished bundle"),
}
_OWNERS: dict[ProvenanceOwner, str] = {
    "docling": "Docling",
    "docling_patched": "Docling, patched in this fork",
    "amir_engine": "Amir Engine",
}


class _About(BaseModel):
    phase: ProvenancePhase
    title: str
    owner: ProvenanceOwner
    code: str
    does: str
    patch: str | None = None


def _template(name: str) -> str:
    return (files("docling.engines") / "templates" / name).read_text(encoding="utf-8")


@functools.cache
def _catalogue() -> dict[str, _About]:
    return TypeAdapter(dict[str, _About]).validate_json(
        _template("provenance_steps.json")
    )


def _at(data: Any, *path: str) -> Any:
    """The value at *path* in nested JSON objects, or None where it stops."""
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _read_rows(path: Path) -> list[dict[str, Any]] | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@dataclass
class _Bundle:
    name: str
    run: dict[str, Any]
    check: dict[str, Any] | None
    structure: dict[str, Any] | None
    figures: list[dict[str, Any]] | None
    tables: list[dict[str, Any]] | None
    files: list[str] = field(default_factory=list)
    images: Counter[str] = field(default_factory=Counter)

    @classmethod
    def read(
        cls, pdf_dir: Path, run: dict[str, Any] | None, check: dict[str, Any] | None
    ) -> _Bundle:
        run = run if run is not None else _read_json(pdf_dir / RUN_JSON_FILENAME)
        check = check if check is not None else _read_json(pdf_dir / CHECK_FILENAME)
        own = {PROVENANCE_FILENAME, METHODS_FILENAME}
        return cls(
            name=pdf_dir.name,
            run=run or {},
            check=check,
            structure=_read_json(pdf_dir / STRUCTURE_FILENAME),
            figures=_read_rows(pdf_dir / FIGURES_FILENAME),
            # Read for the table models only when check.json does not count them.
            tables=_read_rows(pdf_dir / "tables.jsonl") if check is None else None,
            files=sorted(
                p.name if p.is_file() else f"{p.name}/"
                for p in pdf_dir.iterdir()
                if p.name not in own and not p.name.startswith(".")
            ),
            images=Counter(
                p.name.split("_", 1)[0] for p in (pdf_dir / "images").glob("*.png")
            ),
        )

    def at(self, *path: str) -> Any:
        return _at(self.run, *path)

    def checked(self, *path: str) -> Any:
        return _at(self.check, *path)

    @property
    def options(self) -> dict[str, Any]:
        return self.run.get("pipeline_options") or {}

    @property
    def models(self) -> dict[str, Any]:
        return self.run.get("models") or {}

    @property
    def config(self) -> dict[str, Any]:
        return self.run.get("engine_config") or {}

    @property
    def quality(self) -> dict[str, Any] | None:
        return self.run.get("quality")

    @property
    def local(self) -> bool:
        return self.at("source", "source_kind") == "local_path"

    @property
    def fork_r4(self) -> bool:
        # r4 patched the watermark and the cross-page merge, and is the
        # release that added structure_version to run.json.
        return "structure_version" in self.run

    def package(self, name: str) -> str | None:
        return self.at("environment", "packages", name)

    def option(self, block: str) -> dict[str, Any]:
        """A stage's options: ``models.<block>``, or the pipeline's."""
        found = self.models.get(block) or self.options.get(f"{block}_options")
        return found if isinstance(found, dict) else {}

    def flag(self, name: str) -> bool | None:
        value = self.models.get(name, self.options.get(name))
        return value if isinstance(value, bool) else None

    def errors_of(self, key: str) -> list[str]:
        components = _ENGINE_COMPONENTS.get(key, ())
        errors = self.run.get("errors") or []
        return [_error(e) for e in errors if e.get("component") in components]

    def figure_count(self) -> int | None:
        return len(self.figures) if self.figures is not None else None

    def figures_where(self, key: str) -> Counter[str]:
        return Counter(str(row[key]) for row in self.figures or [] if row.get(key))


def _error(error: dict[str, Any]) -> str:
    return f"{error.get('component')}: {error.get('message', '')}"[:240]


def _step(key: str, **fields: Any) -> ProvenanceStep:
    about = _catalogue()[key]
    owner = fields.pop("owner", about.owner)
    patch = fields.pop("patch", about.patch)
    return ProvenanceStep(
        key=key,
        phase=about.phase,
        title=about.title,
        does=about.does,
        owner=owner,
        patch=patch if owner == "docling_patched" else None,
        code=about.code,
        **fields,
    )


def _off(key: str, reason: str = "off", **fields: Any) -> ProvenanceStep:
    return _step(key, state="skipped", reason=reason, **fields)


def _unrecorded(key: str, reason: str = _NOT_IN_RUN, **fields: Any) -> ProvenanceStep:
    return _step(key, state="not_recorded", reason=reason, **fields)


def _shown(*pairs: tuple[str, Any]) -> dict[str, str]:
    return {label: _value(value) for label, value in pairs if value is not None}


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "none"
    return str(value)


def _pick(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: data[key] for key in keys if key in data}


def _count(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def _top(counts: Counter[str], n: int = 3) -> str:
    return ", ".join(f"{k.replace('_', ' ')} {v:,}" for k, v in counts.most_common(n))


def _pages(pages: Iterable[int], limit: int = 6) -> str:
    runs: list[list[int]] = []
    for page in sorted(set(pages)):
        if runs and page == runs[-1][1] + 1:
            runs[-1][1] = page
        else:
            runs.append([page, page])
    text = ", ".join(
        f"p{a}" if a == b else f"p{a}\N{EN DASH}{b}" for a, b in runs[:limit]
    )
    more = len(runs) - limit
    return text + (f" and {more} more" if more > 0 else "")


def _trim(value: Any) -> Any:
    """*value* with long lists cut, so a 300-page record stays readable."""
    if isinstance(value, dict):
        return {k: _trim(v) for k, v in value.items()}
    if isinstance(value, list):
        head = [_trim(v) for v in value[:_LIST_LIMIT]]
        more = len(value) - _LIST_LIMIT
        return [*head, f"... {more} more"] if more > 0 else head
    return value


def _table_method(b: _Bundle) -> tuple[str, str | None]:
    """The table model(s) as the card names them, and the fork's patch."""
    options = b.option("table_structure")
    if not b.config.get("granite_vision_tables"):
        return "TableFormer", None
    if options.get("pdf_text_first"):
        return f"{_GRANITE} + TableFormer, routed per table", (
            "each table routed by where its text is: TableFormer when the PDF "
            "holds it, Granite-Vision for a table of contents, an image-only "
            "table or an OCR page; each the other's fallback; generation capped"
        )
    if options.get("tableformer_fallback"):
        return f"{_GRANITE}, TableFormer as fallback", (
            "TableFormer redoes a looping or degenerate table; generation capped"
        )
    return _GRANITE, None


# --- steps --------------------------------------------------------------------


def _parse_pages(b: _Bundle) -> ProvenanceStep:
    version = b.package("docling-parse")
    pages = b.at("output_summary", "page_count")
    keys = ("images_scale", "force_backend_text", "generate_page_images")
    return _step(
        "parse_pages",
        settings=_shown(
            ("parser", f"docling-parse {version}" if version else None),
            ("image scale", b.options.get("images_scale")),
            ("force_backend_text", b.options.get("force_backend_text")),
        ),
        recorded={"docling-parse": version, **_pick(b.options, *keys)},
        outcome=[_count(pages, "page")] if isinstance(pages, int) else [],
    )


def _text_layer(b: _Bundle) -> ProvenanceStep:
    quality = b.quality or {}
    if "text_layer" not in quality:
        return _unrecorded("text_layer")
    found = quality["text_layer"]
    recorded = {
        "quality.text_layer": found,
        "check.text_layer": b.checked("text_layer"),
    }
    if found is None:
        reason = "no page needed it" if b.local else "not a local file"
        return _off("text_layer", reason, recorded=recorded)
    outcome = []
    if glyph := found.get("glyph_order_pages"):
        outcome.append(
            f"{_count(len(glyph), 'page')} decoded from glyph order ({_pages(glyph)})"
        )
    if unreadable := found.get("unreadable_pages"):
        outcome.append(
            f"{_count(len(unreadable), 'page')} unreadable, read by OCR "
            f"({_pages(unreadable)})"
        )
    if partly := found.get("partly_unreadable_pages"):
        worst = max(p["share"] for p in partly)
        outcome.append(
            f"{_count(len(partly), 'page')} partly unreadable (at most "
            f"{worst:.0%} of a page's characters lost)"
        )
    return _step("text_layer", recorded=recorded, outcome=outcome)


def _parser_repair(b: _Bundle) -> ProvenanceStep | None:
    if "repair_parser_text" not in b.options:
        return None
    on = b.options["repair_parser_text"]
    found = _at(b.quality, "parser_repair")
    common: dict[str, Any] = {
        "settings": _shown(("repair", on)),
        "recorded": {
            "repair_parser_text": on,
            "quality.parser_repair": found,
            "check.text_quality": b.checked("text_quality"),
        },
    }
    if not on:
        return _off("parser_repair", **common)
    if b.quality is None:
        return _unrecorded("parser_repair", **common)
    if found is None:
        return _off("parser_repair", "no page needed it", **common)
    outcome = []
    if respaced := found.get("respaced_pages"):
        outcome.append(
            f"{_count(len(respaced), 'page')} re-spaced where words ran together "
            f"({_pages(respaced)})"
        )
    if letter_pages := found.get("letter_pages"):
        outcome.append(
            f"{_count(found.get('letters', 0), 'look-alike letter')} replaced on "
            f"{_count(len(letter_pages), 'page')} ({_pages(letter_pages)})"
        )
    still = (("fused_pages", "run-together words"), ("lookalike_pages", "look-alikes"))
    for key, what in still:
        if pages := b.checked("text_quality", key):
            outcome.append(f"the check still finds {what} on {_pages(pages)}")
    return _step("parser_repair", outcome=outcome, **common)


def _ocr(b: _Bundle) -> ProvenanceStep:
    options = b.option("ocr")
    auto = set(options) <= _OCR_BASE_KEYS
    patched = "text_layer" in (b.quality or {})
    common: dict[str, Any] = {
        "owner": "docling_patched" if patched else "docling",
        "settings": _shown(
            ("engine", "chosen at run time (auto)" if auto else "set by the caller"),
            ("mode", options.get("mode")),
            ("scale", options.get("scale")),
            ("languages", options.get("lang") or None),
        ),
        "recorded": {"do_ocr": b.flag("do_ocr"), "ocr_options": options},
    }
    if (do_ocr := b.flag("do_ocr")) is None:
        return _unrecorded("ocr", **common)
    if not do_ocr:
        return _off("ocr", **common)
    unreadable = _at(b.quality, "text_layer", "unreadable_pages") or []
    if options.get("mode") == "full_page" or options.get("force_full_page_ocr"):
        outcome = ["every page read by OCR in full"]
    elif unreadable:
        outcome = [
            f"{_count(len(unreadable), 'whole page')} read by OCR, text layer "
            f"unreadable ({_pages(unreadable)})",
            "elsewhere bitmap regions only",
        ]
    elif patched:
        outcome = ["bitmap regions only"]
    else:
        outcome = ["bitmap regions; whole-page OCR not recorded"]
    return _step("ocr", outcome=outcome, **common)


def _layout(b: _Bundle) -> ProvenanceStep:
    layout = b.option("layout")
    if not layout:
        return _unrecorded("layout")
    spec = layout.get("model_spec") or {}
    labels = Counter(_at(b.quality, "label_counts") or {})
    total = sum(labels.values())
    return _step(
        "layout",
        model=spec.get("repo_id"),
        settings=_shown(
            ("revision", spec.get("revision")),
            ("runtime", _at(layout, "engine_options", "engine_type")),
            ("score threshold", _at(layout, "engine_options", "score_threshold")),
        ),
        recorded={"layout_options": layout},
        outcome=[f"{_count(total, 'item')} in the final document: {_top(labels, 4)}"]
        if total
        else [],
    )


def _layout_cleanup(b: _Bundle) -> ProvenanceStep:
    layout = b.option("layout")
    keys = ("keep_empty_clusters", "skip_cell_assignment", "create_orphan_clusters")
    owner = "docling_patched" if b.fork_r4 else "docling"
    if not layout:
        return _unrecorded("layout_cleanup", owner=owner)
    background = _at(b.quality, "layer_counts", "background")
    return _step(
        "layout_cleanup",
        owner=owner,
        settings=_shown(*((key, layout.get(key)) for key in keys)),
        recorded=_pick(layout, *keys),
        outcome=[f"{_count(background, 'item')} on the background layer"]
        if background
        else [],
    )


def _table_structure(b: _Bundle) -> ProvenanceStep:
    options = b.option("table_structure")
    model, patch = _table_method(b)
    tables = b.checked("tables")
    scalars = ((k, v) for k, v in options.items() if not isinstance(v, (dict, list)))
    common: dict[str, Any] = {
        "owner": "docling_patched" if patch else "docling",
        "patch": patch,
        "model": model,
        "settings": _shown(*scalars),
        "recorded": {
            "do_table_structure": b.flag("do_table_structure"),
            "granite_vision_tables": b.config.get("granite_vision_tables"),
            "table_structure_options": options,
            "check.tables": tables,
        },
    }
    if b.flag("do_table_structure") is False:
        return _off("table_structure", **common)
    if tables is not None:
        count = tables.get("count", 0)
        by_model = Counter(tables.get("by_structure_model") or {})
    elif b.tables is not None:
        count = len(b.tables)
        by_model = Counter(
            str(t["structure_model"]) for t in b.tables if t.get("structure_model")
        )
    else:
        return _step("table_structure", **common)
    made_by = ", ".join(
        f"{_TABLE_MODELS.get(k, k)} {n}" for k, n in by_model.most_common()
    )
    outcome = [_count(count, "table") + (f": {made_by}" if made_by else "")]
    if low := _at(tables, "low_recall"):
        outcome.append(f"{_count(len(low), 'table')} whose cells miss printed words")
    if degenerate := _at(tables, "degenerate"):
        outcome.append(f"{_count(len(degenerate), 'degenerate grid')} (e.g. one row)")
    return _step("table_structure", outcome=outcome, **common)


def _assemble(b: _Bundle) -> ProvenanceStep:
    hierarchy = b.options.get("heading_hierarchy_options")
    return _step(
        "assemble",
        owner="docling_patched" if b.fork_r4 else "docling",
        settings=_shown(("Docling heading hierarchy", _at(hierarchy, "enabled"))),
        recorded={"heading_hierarchy_options": hierarchy},
    )


def _picture_classifier(b: _Bundle) -> ProvenanceStep:
    options = b.option("picture_classification")
    on = b.flag("do_picture_classification")
    recorded = {
        "do_picture_classification": on,
        "picture_classification_options": options,
    }
    if on is None:
        return _unrecorded("picture_classifier")
    if not on:
        return _off("picture_classifier", recorded=recorded)
    spec = options.get("model_spec") or {}
    labels = b.figures_where("generic_classifier_label")
    used_by = "the noise filter" if b.config.get("filter_noise_pictures") else None
    classified = _count(sum(labels.values()), "picture")
    return _step(
        "picture_classifier",
        model=spec.get("repo_id"),
        settings=_shown(
            ("revision", spec.get("revision")),
            ("runtime", _at(options, "engine_options", "engine_type")),
            ("used by", used_by),
        ),
        recorded=recorded,
        outcome=[f"{classified} classified; top: {_top(labels)}"] if labels else [],
    )


def _picture_description(b: _Bundle) -> ProvenanceStep:
    options = b.option("picture_description")
    on = b.options.get("do_picture_description")
    keys = (
        "picture_description",
        "picture_description_engine",
        "picture_area_threshold",
    )
    recorded = {
        "do_picture_description": on,
        "picture_description_options": options,
        **_pick(b.config, *keys),
    }
    if on is None:
        return _unrecorded("picture_description")
    if not on:
        return _off("picture_description", recorded=recorded)
    spec = options.get("model_spec") or {}
    revision = spec.get("revision")
    threshold = options.get("picture_area_threshold")
    smallest = f"{threshold:.0%} of the page" if isinstance(threshold, float) else None
    runtime = b.config.get("picture_description_engine") or _at(
        options, "engine_options", "engine_type"
    )
    total = b.figure_count()
    described = sum(b.figures_where("vlm_caption").values())
    return _step(
        "picture_description",
        model=spec.get("default_repo_id") or spec.get("repo_id"),
        settings=_shown(
            ("revision", revision[:10] if isinstance(revision, str) else None),
            ("smallest picture", smallest),
            ("runtime", runtime),
            ("max new tokens", spec.get("max_new_tokens")),
        ),
        recorded=recorded,
        outcome=[f"{described} of {_count(total, 'picture')} described"]
        if total is not None
        else [],
    )


def _enrichment(b: _Bundle) -> ProvenanceStep:
    flags = {
        "code": b.flag("do_code_enrichment"),
        "formulas": b.flag("do_formula_enrichment"),
        "charts": b.flag("do_chart_extraction"),
    }
    if all(value is None for value in flags.values()):
        return _unrecorded("enrichment")
    recorded = {
        **flags,
        "code_formula_options": b.option("code_formula"),
        "chart_extraction_options": b.option("chart_extraction"),
    }
    if not any(flags.values()):
        return _off("enrichment", settings=_shown(*flags.items()), recorded=recorded)
    blocks = (
        ("code_formula", flags["code"] or flags["formulas"]),
        ("chart_extraction", flags["charts"]),
    )
    repos = [
        _at(b.option(k), "model_spec", "default_repo_id") for k, on in blocks if on
    ]
    return _step(
        "enrichment",
        model=", ".join(r for r in repos if r) or None,
        settings=_shown(*flags.items()),
        recorded=recorded,
    )


def _docling_unrecorded(b: _Bundle) -> ProvenanceStep:
    if b.config.get("converter_supplied"):
        return _unrecorded(
            "docling_unrecorded",
            "a converter supplied by the caller: its steps and settings are not "
            "recorded",
        )
    return _unrecorded("docling_unrecorded")


def _text_repairs(b: _Bundle) -> ProvenanceStep:
    ligatures = b.checked("ligature_splits")
    kept = b.checked("tables", "low_recall")
    outcome = []
    if ligatures is not None and ligatures.get("skipped") is None:
        left = sum((ligatures.get("per_export") or {}).values())
        outcome.append(f"{_count(left, 'ligature split')} left in the exports")
    if not b.local:
        outcome.append("ligature rejoin and table PDF text skipped: not a local file")
    elif kept is not None:
        outcome.append(f"{_count(len(kept), 'table')} keep the PDF text of their box")
    checks = "on" if b.local else "off, not a local file"
    return _step(
        "text_repairs",
        settings=_shown(("PDF text checks", checks)),
        recorded={
            "source_kind": b.at("source", "source_kind"),
            "check.ligature_splits": ligatures,
            "check.tables.low_recall": kept,
        },
        outcome=outcome,
        errors=b.errors_of("text_repairs"),
    )


def _structure(b: _Bundle) -> ProvenanceStep:
    if not b.fork_r4:
        return _unrecorded("structure")
    structure = b.structure or {}
    rules = (str(r.get("rule", "")) for r in structure.get("relabels") or [])
    relabels = Counter(rule.removeprefix("rule:") for rule in rules)
    outline = len(structure.get("outline") or [])
    outcome = []
    if b.structure is not None:
        outcome.append(f"{_count(outline, 'section heading')} in the outline")
        outcome.append(
            "title found" if structure.get("title_ref") else "no title found"
        )
    if relabels:
        changed = _count(sum(relabels.values()), "label")
        outcome.append(f"{changed} changed by rule: {_top(relabels, 4)}")
    repeat = b.config.get("noise_repeat_threshold")
    return _step(
        "structure",
        settings=_shown(
            ("rules version", b.run.get("structure_version")),
            ("document role", b.run.get("document_role")),
            ("margin line repeated on", f"{repeat}+ pages" if repeat else None),
        ),
        recorded={
            "structure_version": b.run.get("structure_version"),
            "document_role": b.run.get("document_role"),
            "structure.json": {"outline": outline, "relabels": dict(relabels)}
            if b.structure is not None
            else None,
        },
        outcome=outcome,
        errors=b.errors_of("structure"),
    )


def _quality(b: _Bundle) -> ProvenanceStep:
    quality = b.quality
    if quality is None:
        return _unrecorded("quality", errors=b.errors_of("quality"))
    warnings = quality.get("warnings") or []
    codes = list(dict.fromkeys(w.get("code", "?") for w in warnings))
    blocking = list(dict.fromkeys(w.get("code") for w in warnings if w.get("blocking")))
    body = _count(quality.get("body_text_items", 0), "body text block")
    headings = _count(quality.get("section_headers", 0), "section heading")
    outcome = [
        f"{body}, {headings}",
        f"warnings: {', '.join(codes)}" if codes else "no warnings",
    ]
    if blocking:
        outcome.append(f"blocking: {', '.join(blocking)}")
    if empty := quality.get("pages_without_text"):
        outcome.append(f"{_count(len(empty), 'page')} without text ({_pages(empty)})")
    left_out = ("page_label_counts", "text_layer", "parser_repair")
    return _step(
        "quality",
        recorded={k: v for k, v in quality.items() if k not in left_out},
        outcome=outcome,
        errors=b.errors_of("quality"),
    )


def _figure_types(b: _Bundle) -> ProvenanceStep:
    if "figure_types" not in b.config:
        return _unrecorded("figure_types")
    if (repo := b.config["figure_types"]) is None:
        return _off("figure_types")
    types = b.figures_where("figure_type")
    typed = _count(sum(types.values()), "figure")
    return _step(
        "figure_types",
        model=repo,
        recorded={"figure_types": repo},
        outcome=[f"{typed} typed; top: {_top(types)}"] if types else [],
        errors=b.errors_of("figure_types"),
    )


def _noise_filter(b: _Bundle) -> ProvenanceStep:
    on = b.config.get("filter_noise_pictures")
    if on is None:
        return _unrecorded("noise_filter")
    classes = b.config.get("noise_picture_classes") or []
    veto = b.config.get("noise_imaging_veto")
    vetoed = f"type confidence ≥ {veto['min_confidence']:g}" if veto else "off"
    keys = ("filter_noise_pictures", "noise_picture_classes", "noise_repeat_threshold")
    common: dict[str, Any] = {
        "settings": _shown(
            ("noise labels", _count(len(classes), "classifier label")),
            ("repeated on", f"{b.config.get('noise_repeat_threshold')}+ pages"),
            ("medical-image veto", vetoed),
        ),
        "recorded": _pick(b.config, *keys, "noise_imaging_veto"),
    }
    if not on:
        return _off("noise_filter", **common)
    noise = Counter(
        row.get("noise_reason") or "unknown"
        for row in b.figures or []
        if row.get("is_noise")
    )
    total = b.figure_count()
    marked = f"{sum(noise.values())} of {_count(total or 0, 'picture')} marked as noise"
    return _step(
        "noise_filter",
        outcome=[marked + (f"; {_top(noise)}" if noise else "")]
        if total is not None
        else [],
        errors=b.errors_of("noise_filter"),
        **common,
    )


def _exports(b: _Bundle) -> ProvenanceStep:
    keys = ("chunk_tokenizer", "chunk_max_tokens", "embed_images", "make_html_preview")
    outcome = []
    if (chunks := b.checked("chunks", "count")) is not None:
        outcome.append(_count(chunks, "chunk"))
    outcome.append(f"{_count(len(b.files), 'file')}: {', '.join(b.files)}")
    kinds = {"page": "page render", "picture": "figure crop", "table": "table crop"}
    if crops := [_count(b.images[k], word) for k, word in kinds.items() if b.images[k]]:
        outcome.append("images/: " + ", ".join(crops))
    size = b.config.get("chunk_max_tokens")
    return _step(
        "exports",
        settings=_shown(
            ("chunk tokenizer", b.config.get("chunk_tokenizer")),
            ("chunk size", f"≤ {size} tokens" if size else None),
            ("standalone files", b.config.get("embed_images")),
            ("page viewer", b.config.get("make_html_preview")),
        ),
        recorded=_pick(b.config, *keys, "link_images", "save_artifacts"),
        outcome=outcome,
        errors=b.errors_of("exports"),
    )


def _self_check(b: _Bundle) -> ProvenanceStep:
    check = b.check
    if check is None:
        errors = b.errors_of("self_check")
        return _unrecorded("self_check", "no check.json", errors=errors)
    issues = check.get("issues") or []
    codes = Counter(issue.split(":", 1)[0] for issue in issues)
    listed = ", ".join(f"{code} {n}" for code, n in codes.most_common())
    outcome = [f"{_count(len(issues), 'issue')}: {listed}" if issues else "no issues"]
    recall = check.get("page_recall") or {}
    if recall.get("skipped"):
        outcome.append(f"page recall skipped: {recall['skipped']}")
    elif recall.get("document_recall") is not None:
        low = recall.get("min_page_recall")
        page = recall.get("min_page")
        lowest = f", lowest page {low:.2f} (p{page})" if low is not None else ""
        words = f"{recall.get('pdf_words', 0):,}"
        outcome.append(
            f"word recall vs the PDF {recall['document_recall']:.3f} of {words} "
            f"words{lowest}"
        )
    fidelity = check.get("export_fidelity") or {}
    shown = [
        f"{k} {fidelity[k]:.3f}" for k in ("html", "md", "chunks") if fidelity.get(k)
    ]
    if shown:
        outcome.append(f"export fidelity {', '.join(shown)}")
    coverage = check.get("html_coverage") or {}
    if items := coverage.get("items"):
        once = coverage.get("tagged_once", 0)
        outcome.append(f"{once:,} of {items:,} items once in the HTML")
    keys = ("ok", "issues", "page_recall", "export_fidelity", "html_coverage")
    return _step(
        "self_check",
        settings=_shown(
            ("checked by", check.get("checked_by")),
            ("source PDF", check.get("pdf") or "not found"),
        ),
        recorded=_pick(check, *keys, "uncovered_text"),
        outcome=outcome,
        errors=b.errors_of("self_check"),
    )


def _figure_to_data(b: _Bundle) -> ProvenanceStep | None:
    block = b.run.get("figure_to_data")
    if block is None:
        return None
    checked = b.checked("figure_data") or {}
    figures = block.get("figures") or {}
    outcome = []
    if figures:
        outcome.append(
            f"{_count(figures.get('read', 0), 'figure')} read, "
            f"{figures.get('no_data', 0)} without data, "
            f"{figures.get('not_read', 0)} not read"
        )
    if block.get("values") is not None:
        outcome.append(_count(block["values"], "value"))
    if checked.get("skipped") is None and checked.get("extracted") is not None:
        outcome.append(
            f"{checked.get('verified', 0)} of {checked['extracted']} at the markdown "
            f"confidence threshold; {checked.get('eligible', 0)} chart figures eligible"
        )
    if (seconds := block.get("seconds")) is not None:
        cost = block.get("cost_usd")
        spent = f", {cost:.2f} USD" if cost is not None else ""
        outcome.append(f"{seconds:.0f} s{spent}")
    return _step(
        "figure_to_data",
        model=block.get("model"),
        settings=_shown(
            ("method", block.get("method")),
            ("backend", block.get("backend")),
            ("step version", block.get("step_version")),
            ("ran at", block.get("ran_at")),
        ),
        recorded={"run.figure_to_data": block, "check.figure_data": checked or None},
        outcome=outcome,
    )


_Builder = Callable[[_Bundle], "ProvenanceStep | None"]
_DOCLING_STEPS: tuple[_Builder, ...] = (
    _parse_pages,
    _text_layer,
    _parser_repair,
    _ocr,
    _layout,
    _layout_cleanup,
    _table_structure,
    _assemble,
    _picture_classifier,
    _picture_description,
    _enrichment,
)
_ENGINE_STEPS: tuple[_Builder, ...] = (
    _text_repairs,
    _structure,
    _quality,
    _figure_types,
    _noise_filter,
    _exports,
    _self_check,
    _figure_to_data,
)


def _provenance(b: _Bundle) -> BundleProvenance:
    docling = _DOCLING_STEPS if b.options else (_docling_unrecorded,)
    status = b.run.get("status")
    duration = b.at("timing", "duration_seconds")
    timed = f" ({_duration(duration)})" if duration is not None else ""
    return BundleProvenance(
        bundle=b.name,
        file_name=b.at("source", "file_name"),
        pages=b.at("output_summary", "page_count"),
        sha256=b.at("source", "binary_hash"),
        document_role=b.run.get("document_role"),
        converted_from=b.at("source", "converted_from", "file_name"),
        engine=b.run.get("engine") or {},
        started_at=b.at("timing", "started_at"),
        duration_seconds=duration,
        status=status.rsplit(".", 1)[-1] if isinstance(status, str) else None,
        check_ok=b.checked("ok"),
        issue_codes=Counter(i.split(":", 1)[0] for i in b.checked("issues") or []),
        errors=[_error(e) for e in b.run.get("errors") or []],
        steps=[
            s for build in (*docling, *_ENGINE_STEPS) if (s := build(b)) is not None
        ],
        not_recorded=[
            "How long each step took: run.json times the Docling conversion as a "
            f"whole{timed}, model loading included for the first PDF of a process; "
            "the steps after it are not timed.",
            "Which OCR engine ran: the options let Docling choose one at run time.",
            "The PDF backend and the table models' repo ids: the options do not "
            "name them. The engine uses Docling's default backend (docling-parse) "
            f"and loads {_GRANITE_REPO} for Granite-Vision tables.",
        ],
    )


def build_provenance(
    pdf_dir: Path,
    *,
    run: dict[str, Any] | None = None,
    check: dict[str, Any] | None = None,
) -> BundleProvenance:
    """The steps the bundle in *pdf_dir* records, in execution order; *run*
    and *check* stand for ``run.json`` and ``check.json`` when given."""
    return _provenance(_Bundle.read(pdf_dir, run, check))


def write_provenance(
    pdf_dir: Path,
    *,
    run: dict[str, Any] | None = None,
    check: dict[str, Any] | None = None,
) -> list[Path]:
    """Write ``provenance.html`` and ``methods.md`` into the bundle *pdf_dir*
    and return their paths. *run* and *check* stand for ``run.json`` and
    ``check.json`` when given (a conversion passes what it is about to
    write); the other files are read from the bundle. A missing file or
    field makes its steps "not recorded"."""
    bundle = _Bundle.read(pdf_dir, run, check)
    page = pdf_dir / PROVENANCE_FILENAME
    write_text_atomic(page, _render_page(_provenance(bundle)))
    methods = pdf_dir / METHODS_FILENAME
    write_text_atomic(methods, _render_methods(bundle))
    return [page, methods]


# --- provenance.html ----------------------------------------------------------

_NUMBER = re.compile(r"(?<![\w.\N{EN DASH}-])\d+(?:[.,]\d+)*%?")
_Group = tuple[ProvenancePhase, list[tuple[int, ProvenanceStep]]]


def _fact(text: str) -> str:
    return _NUMBER.sub(lambda m: f"<b>{m.group()}</b>", html.escape(text))


def _duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.1f} s"
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes} min {rest} s"


def _release(engine: dict[str, Any]) -> str:
    version = engine.get("version") or "(version not recorded)"
    release = engine.get("release")
    commit = engine.get("git_commit")
    parts = [
        f"{engine.get('name') or 'extrct_docling'} {version}",
        f"release {release}" if release else "",
        "not a tagged release" if "release" in engine and not release else "",
        f"commit {commit[:10]}" if commit else "",
        "with uncommitted changes" if engine.get("git_dirty") else "",
    ]
    return " · ".join(p for p in parts if p)


def _header(p: BundleProvenance) -> str:
    if p.check_ok is None:
        check = '<dd class="muted">no check.json</dd>'
    elif p.check_ok:
        check = '<dd class="good">OK, no issues</dd>'
    else:
        issues = ", ".join(f"{code} {n}" for code, n in p.issue_codes.items())
        found = _count(sum(p.issue_codes.values()), "issue")
        check = f'<dd class="bad">{html.escape(f"{found}: {issues}")}</dd>'
    when = (p.started_at or "")[:16].replace("T", " ")
    took = _duration(p.duration_seconds) if p.duration_seconds is not None else ""
    status = p.status or "not recorded"
    facts = [
        ("Pages", str(p.pages) if p.pages is not None else "not recorded"),
        ("SHA-256", f"{p.sha256[:12]}…" if p.sha256 else "not recorded"),
        ("Release", _release(p.engine)),
        (
            "Converted",
            " · ".join(t for t in (f"{when} UTC" if when else "", took) if t),
        ),
    ]
    if p.document_role and p.document_role != "manuscript":
        facts.append(("Role", p.document_role))
    if p.converted_from:
        facts.append(("Made from", p.converted_from))
    wide = ' class="wide"'
    rows = "".join(
        f"<div{wide if k == 'Release' else ''}><dt>{k}</dt>"
        f"<dd>{html.escape(v or 'not recorded')}</dd></div>"
        for k, v in facts
    )
    good = "good" if status == "SUCCESS" else "bad"
    rows += f'<div><dt>Status</dt><dd class="{good}">{html.escape(status)}</dd></div>'
    rows += f"<div><dt>Self-check</dt>{check}</div>"
    if p.errors:
        errors = html.escape("; ".join(p.errors))
        rows += f'<div><dt>Errors</dt><dd class="bad">{errors}</dd></div>'
    legend = "".join(
        f'<li class="o-{owner}"><span class="sw"></span>{label}</li>'
        for owner, label in _OWNERS.items()
    )
    title = html.escape(p.file_name or p.bundle)
    return (
        '<header class="top"><p class="eyebrow">How this bundle was made</p>'
        f'<h1>{title}</h1><dl class="facts">{rows}</dl>'
        f'<ul class="legend" aria-label="Legend">{legend}<li class="st-skipped">'
        '<span class="sw"></span>skipped, with the reason</li></ul></header>'
    )


def _grouped(steps: list[ProvenanceStep]) -> list[_Group]:
    groups: list[_Group] = []
    for number, step in enumerate(steps, start=1):
        if not groups or groups[-1][0] != step.phase:
            groups.append((step.phase, []))
        groups[-1][1].append((number, step))
    return groups


def _overview(groups: list[_Group]) -> str:
    phases = []
    for phase, steps in groups:
        pills = "".join(
            f'<a class="pill o-{s.owner} st-{s.state}" href="#step-{s.key}">'
            f"<span>{n}</span>{html.escape(s.title)}</a>"
            for n, s in steps
        )
        title = html.escape(_PHASES[phase][0])
        phases.append(f'<li><p>{title}</p><div class="pills">{pills}</div></li>')
    return f'<nav class="map" aria-label="All steps"><ol>{"".join(phases)}</ol></nav>'


def _card(number: int, s: ProvenanceStep) -> str:
    owner = _OWNERS[s.owner] + (" · skipped" if s.state == "skipped" else "")
    about = [f'<p class="does">{html.escape(s.does)}</p>']
    if s.patch:
        patch = html.escape(s.patch)
        about.append(f'<p class="patch"><span>Fork patch:</span> {patch}</p>')
    if s.state != "ran":
        label = "Skipped" if s.state == "skipped" else "Not recorded"
        why = html.escape(s.reason or "")
        about.append(f'<p class="why"><span>{label}:</span> {why}</p>')
    rows = [("model", f"<code>{html.escape(s.model)}</code>")] if s.model else []
    rows += [(k, html.escape(v)) for k, v in s.settings.items()]
    if rows:
        cells = "".join(
            f"<div><dt>{html.escape(k)}</dt><dd>{v}</dd></div>" for k, v in rows
        )
        about.append(f'<dl class="settings">{cells}</dl>')
    facts = "".join(f"<li>{_fact(f)}</li>" for f in s.outcome)
    facts += "".join(f'<li class="error">{html.escape(e)}</li>' for e in s.errors)
    if facts:
        result = f'<ul class="outcome">{facts}</ul>'
    elif s.state == "ran":
        result = '<p class="none">No outcome recorded for this step.</p>'
    else:
        result = ""
    details = ""
    if any(value is not None for value in s.recorded.values()):
        dumped = html.escape(
            json.dumps(_trim(s.recorded), indent=2, ensure_ascii=False)
        )
        details = (
            "<details><summary>All recorded settings and data</summary>"
            f"<pre>{dumped}</pre></details>"
        )
    code = f'<p class="code"><code>{html.escape(s.code)}</code></p>' if s.code else ""
    title = html.escape(s.title)
    return (
        f'<li class="card o-{s.owner} st-{s.state}" id="step-{s.key}">'
        f'<div class="head"><span class="no">{number}</span><h3>{title}</h3>'
        f'<span class="tag">{html.escape(owner)}</span></div>'
        f'<div class="body"><div>{"".join(about)}</div><div>{result}</div></div>'
        f"{details}{code}</li>"
    )


def _section(index: int, group: _Group) -> str:
    phase, steps = group
    title, subtitle = (html.escape(text) for text in _PHASES[phase])
    cards = "".join(_card(n, s) for n, s in steps)
    return (
        f'<section class="phase" id="phase-{phase}"><h2><span class="badge">{index}'
        f'</span>{title} <small>{subtitle}</small></h2><ol class="steps">{cards}</ol>'
        "</section>"
    )


def _render_page(p: BundleProvenance) -> str:
    groups = _grouped(p.steps)
    data = json.dumps(p.model_dump(mode="json"), ensure_ascii=False)
    return string.Template(_template("provenance.html")).substitute(
        title=html.escape(f"How {p.file_name or p.bundle} was made"),
        script_id=PROVENANCE_SCRIPT_ID,
        # "</" would end the <script> element early; "<\/" is the same JSON.
        data=data.replace("</", "<\\/"),
        header=_header(p),
        overview=_overview(groups),
        sections="".join(_section(i, g) for i, g in enumerate(groups, start=1)),
        notes="".join(f"<li>{html.escape(n)}</li>" for n in p.not_recorded),
        written_by=html.escape(f"extrct_docling {ENGINE_VERSION}"),
    )


# --- methods.md ---------------------------------------------------------------


def _sentence(text: str | None) -> str:
    return f"{text} " if text else ""


def _upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def _render_methods(b: _Bundle) -> str:
    engine = b.run.get("engine") or {}
    commit = engine.get("git_commit")
    noted = [
        f"commit {commit[:10]}" if commit else "",
        "with uncommitted changes" if engine.get("git_dirty") else "",
    ]
    shown = ", ".join(n for n in noted if n)
    unknown = "(version not recorded)"
    rules = b.run.get("structure_version")
    structure = (
        "Headings, captions and running headers and footers were then assigned "
        f"by rule (structure rules version {rules})."
    )
    layout = _at(b.option("layout"), "model_spec", "repo_id")
    text = string.Template(_template("methods.md")).substitute(
        generator=ENGINE_VERSION,
        bundle=b.name,
        file_name=b.at("source", "file_name") or b.name,
        pages=b.at("output_summary", "page_count") or "an unrecorded number of",
        engine_version=engine.get("version") or unknown,
        release=f" ({shown})" if shown else "",
        docling_version=b.package("docling-slim") or b.package("docling") or "",
        docling_parse_version=b.package("docling-parse") or unknown,
        text_layer=_sentence(_methods_text_layer(b)),
        parser_repair=_sentence(_methods_parser_repair(b)),
        ocr=_sentence(_methods_ocr(b)),
        layout_model=layout or "(not recorded)",
        tables=_sentence(_methods_tables(b)),
        figures=_sentence(_methods_figures(b)),
        descriptions=_sentence(_methods_descriptions(b)),
        structure=_sentence(structure if rules is not None else None),
        chunk_max_tokens=b.config.get("chunk_max_tokens", "(not recorded)"),
        chunk_tokenizer=b.config.get("chunk_tokenizer", "(not recorded)"),
        check=_sentence(_methods_check(b)),
        figure_data=_sentence(_methods_figure_data(b)),
        software=_methods_software(b),
    )
    lines = [re.sub(r" {2,}", " ", line).rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip() + "\n"


def _methods_text_layer(b: _Bundle) -> str | None:
    found = _at(b.quality, "text_layer") or {}
    parts = []
    if glyph := found.get("glyph_order_pages"):
        parts.append(
            f"on {_count(len(glyph), 'page')}, text in fonts without a Unicode map "
            "was decoded from glyph order"
        )
    if partly := found.get("partly_unreadable_pages"):
        worst = max(p["share"] for p in partly)
        parts.append(
            f"on {_count(len(partly), 'page')}, up to {worst:.0%} of a page's "
            "characters could not be read"
        )
    return _upper_first("; ".join(parts) + ".") if parts else None


def _methods_parser_repair(b: _Bundle) -> str | None:
    found = _at(b.quality, "parser_repair") or {}
    parts = []
    if letter_pages := found.get("letter_pages"):
        letters = f"{found.get('letters', 0):,}"
        parts.append(
            f"characters that docling-parse read as look-alikes ({letters} on "
            f"{_count(len(letter_pages), 'page')}) were replaced by pdfium's reading"
        )
    if respaced := found.get("respaced_pages"):
        pages = _count(len(respaced), "page")
        parts.append(f"words it ran together were separated on {pages}")
    return _upper_first(", and ".join(parts) + ".") if parts else None


def _methods_ocr(b: _Bundle) -> str | None:
    if b.flag("do_ocr") is False:
        return "OCR was not used."
    options = b.option("ocr")
    if options.get("mode") == "full_page" or options.get("force_full_page_ocr"):
        return "Every page was read in full by OCR (engine chosen at run time)."
    if unreadable := _at(b.quality, "text_layer", "unreadable_pages"):
        return (
            f"The {_count(len(unreadable), 'page')} whose text layer could not be "
            "read were read in full by OCR (engine chosen at run time)."
        )
    return None


def _methods_tables(b: _Bundle) -> str | None:
    if b.flag("do_table_structure") is False:
        return "Table structure recognition was off."
    options = b.option("table_structure")
    granite = f"{_GRANITE} ({_GRANITE_REPO})"
    if not b.config.get("granite_vision_tables"):
        method = "TableFormer"
    elif options.get("pdf_text_first"):
        method = (
            "TableFormer where the PDF's text layer held their text and with "
            f"{granite} otherwise, each the other's fallback"
        )
    elif options.get("tableformer_fallback"):
        method = f"{granite}, with TableFormer for tables it could not parse"
    else:
        method = granite
    counts = ""
    if (count := b.checked("tables", "count")) is not None:
        by_model = Counter(b.checked("tables", "by_structure_model") or {})
        made_by = ", ".join(
            f"{_TABLE_MODELS.get(k, k)} {n}" for k, n in by_model.most_common()
        )
        counts = f" ({_count(count, 'table')}{': ' + made_by if made_by else ''})"
    return f"Tables were structured with {method}{counts}."


def _methods_figures(b: _Bundle) -> str | None:
    classifier = _at(b.option("picture_classification"), "model_spec", "repo_id")
    parts = []
    if b.flag("do_picture_classification") and classifier:
        parts.append(f"classified with {classifier}")
    if repo := b.config.get("figure_types"):
        parts.append(f"typed zero-shot with BiomedCLIP ({repo})")
    sentences = [f"Pictures were {' and '.join(parts)}."] if parts else []
    if b.config.get("filter_noise_pictures"):
        classes = set(b.config.get("noise_picture_classes") or [])
        examples = [c for c in ("logo", "signature", "watermark") if c in classes]
        veto = b.config.get("noise_imaging_veto")
        total = b.figure_count()
        noise = sum(1 for row in b.figures or [] if row.get("is_noise"))
        repeat = b.config.get("noise_repeat_threshold")
        sentences.append(
            "Pictures with a non-content label"
            + (f" (e.g. {', '.join(examples)})" if examples else "")
            + f" or repeated on {repeat} or more pages were marked as noise and "
            "left out of the markdown"
            + (f" ({noise} of {total})" if total is not None else "")
            + (
                ", unless typed as a medical image with confidence "
                f"≥ {veto['min_confidence']:g}"
                if veto
                else ""
            )
            + "."
        )
    return " ".join(sentences) or None


def _methods_descriptions(b: _Bundle) -> str | None:
    on = b.options.get("do_picture_description")
    if on is None:
        return None
    if not on:
        return "Pictures were not described by a vision-language model."
    options = b.option("picture_description")
    spec = options.get("model_spec") or {}
    repo = (
        spec.get("default_repo_id") or spec.get("repo_id") or "a vision-language model"
    )
    threshold = options.get("picture_area_threshold")
    covering = (
        f" covering at least {threshold:.0%} of the page"
        if isinstance(threshold, float)
        else ""
    )
    total = b.figure_count()
    described = sum(b.figures_where("vlm_caption").values())
    counted = f" ({described} of {total})" if total is not None else ""
    return (
        f"Pictures{covering} were described by {repo}{counted}; these "
        "descriptions are model output."
    )


def _methods_check(b: _Bundle) -> str | None:
    recall = b.checked("page_recall") or {}
    if recall.get("skipped") or recall.get("document_recall") is None:
        return None
    low = recall.get("min_page_recall")
    page = recall.get("min_page")
    lowest = f" (lowest page: {low:.1%}, page {page})" if low is not None else ""
    words = f"{recall.get('pdf_words', 0):,}"
    return (
        f"The output holds {recall['document_recall']:.1%} of the {words} words "
        f"of the PDF's text layer{lowest}."
    )


def _methods_figure_data(b: _Bundle) -> str | None:
    block = b.run.get("figure_to_data")
    if block is None:
        return None
    checked = b.checked("figure_data") or {}
    model = block.get("model") or "a model"
    method = block.get("method") or "method not recorded"
    if not checked.get("eligible") or checked.get("extracted") is None:
        return f"In a separate step, {model} ({method}) read chart figures' values."
    values = _count(block.get("values") or 0, "value")
    return (
        f"In a separate step, {model} ({method}) read the plotted values of "
        f"{checked['extracted']} of {_count(checked['eligible'], 'chart figure')} "
        f"({values}); {checked.get('verified', 0)} reached the confidence "
        "threshold for the markdown."
    )


def _methods_software(b: _Bundle) -> str:
    lines = [f"- {_release(b.run.get('engine') or {})}"]
    cuda = b.at("environment", "torch_cuda")
    for name, version in (b.at("environment", "packages") or {}).items():
        if version is not None:
            on_cuda = f" (CUDA {cuda})" if name == "torch" and cuda else ""
            lines.append(f"- {name} {version}{on_cuda}")
    if python := b.at("environment", "python"):
        lines.append(f"- Python {python}")
    return "\n".join(lines)
