import re
from typing import Any


def _normalize_key(inner: str) -> str:
    inner = inner.strip().replace("-", "_")
    parts = re.split(r"\s+", inner)
    return "_".join(p.lower() for p in parts if p)


def _label_from_key(key: str, inner: str) -> str:
    inner = inner.strip()
    if inner and not inner.replace(" ", "_").lower() == key:
        return inner.title() if inner.isupper() or "_" in inner else inner
    return key.replace("_", " ").title()


def detect_dynamic_fields(text: str) -> list[dict[str, Any]]:
    """Find placeholders: {{ field_name }}, [[ FIELD_NAME ]], {single_token}."""
    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"\{\{\s*([a-zA-Z0-9_\s-]+?)\s*\}\}"), "mustache"),
        (re.compile(r"\[\[\s*([A-Z0-9_\s-]+?)\s*\]\]"), "brackets"),
        (re.compile(r"(?<!\{)\{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*\}(?!\})"), "brace"),
    ]

    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for rx, _kind in patterns:
        for m in rx.finditer(text):
            raw_full = m.group(0)
            inner = m.group(1)
            key = _normalize_key(inner)
            if not key:
                continue
            label = _label_from_key(key, inner)
            if key not in merged:
                merged[key] = {"key": key, "label": label, "placeholders": []}
                order.append(key)
            if raw_full not in merged[key]["placeholders"]:
                merged[key]["placeholders"].append(raw_full)

    return [merged[k] for k in order]
