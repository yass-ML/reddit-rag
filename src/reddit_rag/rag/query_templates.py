"""Load editable query templates from Markdown files with YAML front matter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Categories allowed in front matter (extensible; default seeds use the five analysis types).
ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {
        "pain_points",
        "emotional_drivers",
        "objections",
        "vocabulary",
        "faqs",
        "themes",
    }
)

# Ticket 5.4: these template ids must exist under ``config/query_templates/`` in the repo default.
REQUIRED_TEMPLATE_IDS: frozenset[str] = frozenset(
    {
        "pain-points",
        "emotional-drivers",
        "objections",
        "vocabulary",
        "faqs",
    }
)

_FRONT_MATTER_RE = re.compile(
    r"^---\s*\n(?P<yaml>.+?)\n---\s*\n(?P<body>.*)$",
    re.DOTALL | re.MULTILINE,
)


class QueryTemplateError(ValueError):
    """Invalid template file or index."""


@dataclass(frozen=True)
class QueryTemplate:
    """One reusable analysis prompt loaded from disk."""

    id: str
    title: str
    category: str
    prompt: str
    path: Path


def _require_str(data: dict[str, Any], key: str, *, path: Path) -> str:
    v = data.get(key)
    if not isinstance(v, str) or not v.strip():
        raise QueryTemplateError(f"{path}: front matter '{key}' must be a non-empty string")
    return v.strip()


def _parse_front_matter(text: str, *, path: Path) -> tuple[dict[str, Any], str]:
    m = _FRONT_MATTER_RE.match(text.strip())
    if not m:
        raise QueryTemplateError(
            f"{path}: expected YAML front matter starting with --- and closing --- before prompt body"
        )
    raw_yaml = m.group("yaml")
    body = m.group("body").strip()
    try:
        loaded = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as e:
        raise QueryTemplateError(f"{path}: invalid YAML in front matter: {e}") from e
    if not isinstance(loaded, dict):
        raise QueryTemplateError(f"{path}: front matter YAML must be a mapping at the root")
    return loaded, body


def load_query_template_file(path: Path) -> QueryTemplate:
    """Load a single ``*.md`` template file."""
    if not path.is_file():
        raise QueryTemplateError(f"Template file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    data, body = _parse_front_matter(raw, path=path)
    tid = _require_str(data, "id", path=path)
    title = _require_str(data, "title", path=path)
    cat = _require_str(data, "category", path=path)
    if cat not in ALLOWED_CATEGORIES:
        raise QueryTemplateError(
            f"{path}: unknown category {cat!r}; allowed: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )
    if not body:
        raise QueryTemplateError(f"{path}: prompt body after front matter must be non-empty")
    return QueryTemplate(id=tid, title=title, category=cat, prompt=body, path=path.resolve())


def load_query_templates(templates_dir: Path) -> list[QueryTemplate]:
    """Load every ``*.md`` file in ``templates_dir`` (non-recursive)."""
    root = Path(templates_dir).expanduser().resolve()
    if not root.is_dir():
        raise QueryTemplateError(f"Query templates directory not found: {root}")
    paths = sorted(root.glob("*.md"))
    if not paths:
        raise QueryTemplateError(f"No *.md templates in {root}")
    templates = [load_query_template_file(p) for p in paths]
    seen: set[str] = set()
    for t in templates:
        if t.id in seen:
            raise QueryTemplateError(f"Duplicate template id {t.id!r} under {root}")
        seen.add(t.id)
    return templates


def validate_required_templates(templates: list[QueryTemplate]) -> None:
    """Ensure all ticket-required template ids are present."""
    have = {t.id for t in templates}
    missing = sorted(REQUIRED_TEMPLATE_IDS - have)
    if missing:
        raise QueryTemplateError(
            "Missing required query template id(s): "
            + ", ".join(missing)
            + ". Add matching *.md files under the query templates directory."
        )


def get_template_by_id(templates_dir: Path, template_id: str) -> QueryTemplate:
    """Return the template with the given ``id``."""
    want = (template_id or "").strip()
    if not want:
        raise QueryTemplateError("template id must be non-empty")
    for t in load_query_templates(templates_dir):
        if t.id == want:
            return t
    raise QueryTemplateError(f"Unknown template id: {want!r}")


def list_templates_lines(templates: list[QueryTemplate]) -> list[str]:
    """Human-readable lines for ``--list-templates``."""
    lines: list[str] = []
    for t in sorted(templates, key=lambda x: (x.category, x.title.lower())):
        lines.append(f"{t.id}\t{t.category}\t{t.title}")
    return lines
