import re
from typing import Any


def _normalize_key(inner: str) -> str:
    s = inner.strip().replace("-", "_")
    s = re.sub(r"[,;]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = [p for p in s.split(" ") if p]
    return "_".join(p.lower().strip(".,'") for p in parts)


def _label_from_inner(inner: str, key: str) -> str:
    """Form label: prefer text as written inside the braces."""
    s = inner.strip()
    if s:
        return s
    return key.replace("_", " ").title()


def detect_dynamic_fields(text: str) -> list[dict[str, Any]]:
    """Detect only ``{{ field_name }}`` placeholders (double curly braces).

    Each **distinct** ``{{...}}`` string becomes its own form field so spelling and
    casing differences (e.g. ``{{Client Name}}`` vs ``{{Client name}}``) are separate.
    The exact ``{{...}}`` substring is what merge replaces.

    If the same ``{{...}}`` text appears multiple times, one field still fills every
    occurrence (same replacement string).
    """
    rx = re.compile(r"\{\{\s*([a-zA-Z0-9_,\s-]+?)\s*\}\}")
    rows: list[dict[str, Any]] = []
    raw_assigned: set[str] = set()
    base_seq: dict[str, int] = {}

    for m in rx.finditer(text):
        raw_full = m.group(0)
        inner = m.group(1)
        base = _normalize_key(inner)
        if not base:
            continue
        if raw_full in raw_assigned:
            continue

        base_seq[base] = base_seq.get(base, 0) + 1
        n = base_seq[base]
        key = base if n == 1 else f"{base}_{n}"
        label = _label_from_inner(inner, key)
        raw_assigned.add(raw_full)
        rows.append({"key": key, "label": label, "placeholders": [raw_full]})

    return rows
