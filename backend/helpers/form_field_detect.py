import re
from typing import Any

# Stored on each field in fields_schema; admin assigns in "Generated fields" UI.
ALLOWED_INPUT_TYPES = frozenset(
    {"text", "textarea", "number", "email", "tel", "date", "checkbox", "signature"}
)


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
        rows.append(
            {
                "key": key,
                "label": label,
                "placeholders": [raw_full],
                "input_type": "text",
            }
        )

    return rows


def normalize_field_schema(schema: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Ensure each row has a valid input_type."""
    out: list[dict[str, Any]] = []
    for row in list(schema or []):
        if not isinstance(row, dict) or not row.get("key"):
            continue
        d = {k: v for k, v in row.items() if k != "input_type"}
        it = str(row.get("input_type") or "text").strip().lower()
        if it not in ALLOWED_INPUT_TYPES:
            it = "text"
        d["input_type"] = it
        out.append(d)
    return out


def merge_detected_with_saved_input_types(
    previous: list[dict[str, Any]] | None,
    detected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """After re-detecting {{}} from document text, keep input_type from previous schema when keys match."""
    prev_map = {
        str(r["key"]): r
        for r in (previous or [])
        if isinstance(r, dict) and r.get("key")
    }
    merged: list[dict[str, Any]] = []
    for row in detected:
        if not isinstance(row, dict) or not row.get("key"):
            continue
        key = str(row["key"])
        prev = prev_map.get(key, {})
        it = str(prev.get("input_type") or row.get("input_type") or "text").strip().lower()
        if it not in ALLOWED_INPUT_TYPES:
            it = "text"
        merged.append({**row, "input_type": it})
    return merged
