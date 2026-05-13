import re
from typing import Any

# Stored on each field in fields_schema; admin assigns in "Generated fields" UI.
ALLOWED_INPUT_TYPES = frozenset(
    {"text", "textarea", "number", "email", "tel", "date", "checkbox", "radio", "signature"}
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
    """Detect ``{{ field_name }}`` placeholders (double curly braces).

    Each **regex match** becomes its own form field, so the same literal ``{{a}}``
    repeated N times yields N rows (keys ``a``, ``a_2``, …) and independent answers.

    ``placeholder_match_index`` is 0-based among occurrences of that **exact**
    placeholder string (same spacing/casing) in ``text`` order — used at merge time
    so each occurrence can get a different value.

    ``group_label`` (optional) is text before the first ``{{`` on the same line, or
    the previous **heading-only** line: ends with ``:``, ends with ``?`` (intake
    questions), ``1.`` / ``1)`` numbered lead-ins, ends with ``)`` while containing
    ``(``, or looks like ``V. Title`` (Roman numeral). Shown on the fill form as a
    section heading; consecutive fields with the same ``group_label`` can render in
    one row in the UI.
    """
    rx = re.compile(r"\{\{\s*([a-zA-Z0-9_,\s-]+?)\s*\}\}")
    rows: list[dict[str, Any]] = []
    base_seq: dict[str, int] = {}
    # 0-based occurrence count per exact placeholder token (e.g. second "{{a}}" → 1)
    ph_occurrence: dict[str, int] = {}
    # Last section title (heading-only line or inline text before {{ on a line); applies to
    # following placeholder lines until a new heading-only line replaces it.
    active_section: str | None = None
    _section_roman = re.compile(r"^\s*[IVXLCDM]{1,5}\.\s+\S", re.I)
    _section_numbered = re.compile(r"^\s*\d{1,2}[\).\s]\s*\S")

    def _is_section_heading_line(s: str) -> bool:
        if not s or "{{" in s:
            return False
        if s.endswith(":"):
            return True
        if "(" in s and s.endswith(")"):
            return True
        if s.endswith("?"):
            # Skip tiny fragments ("OK?"); real intake prompts are longer.
            return len(s.strip()) >= 10
        if _section_numbered.match(s):
            return True
        return bool(_section_roman.match(s))

    for line in text.split("\n"):
        stripped = line.strip()
        matches = list(rx.finditer(line))
        if not matches:
            if _is_section_heading_line(stripped):
                active_section = stripped[:200]
            continue

        prefix = line[: matches[0].start()].strip()
        group_label = (prefix or active_section or "").strip() or None
        if group_label and len(group_label) > 200:
            group_label = group_label[:200].rstrip()
        if prefix:
            active_section = prefix[:200]

        for m in matches:
            raw_full = m.group(0)
            inner = m.group(1)
            base = _normalize_key(inner)
            if not base:
                continue

            match_idx = ph_occurrence.get(raw_full, 0)
            ph_occurrence[raw_full] = match_idx + 1

            base_seq[base] = base_seq.get(base, 0) + 1
            seq = base_seq[base]
            key = base if seq == 1 else f"{base}_{seq}"

            label = _label_from_inner(inner, key)
            if match_idx > 0:
                label = f"{label} ({match_idx + 1})"

            row: dict[str, Any] = {
                "key": key,
                "label": label,
                "placeholders": [raw_full],
                "placeholder_match_index": match_idx,
                "input_type": "text",
            }
            if group_label:
                row["group_label"] = group_label
            rows.append(row)

    return rows


def normalize_field_schema(schema: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Ensure each row has a valid input_type."""
    out: list[dict[str, Any]] = []
    for row in list(schema or []):
        if not isinstance(row, dict) or not row.get("key"):
            continue
        d = {k: v for k, v in row.items() if k != "input_type"}
        pm = d.get("placeholder_match_index")
        if pm is not None:
            try:
                d["placeholder_match_index"] = int(pm)
            except (TypeError, ValueError):
                d.pop("placeholder_match_index", None)
        gl = d.get("group_label")
        if isinstance(gl, str):
            gl = gl.strip()[:200]
            if gl:
                d["group_label"] = gl
            else:
                d.pop("group_label", None)
        elif "group_label" in d:
            d.pop("group_label", None)
        it = str(row.get("input_type") or "text").strip().lower()
        if it not in ALLOWED_INPUT_TYPES:
            it = "text"
        if it != "radio":
            d.pop("radio_group", None)
            d.pop("radio_option", None)
        else:
            rg = d.get("radio_group")
            if isinstance(rg, str):
                rg = rg.strip()[:128]
                if rg:
                    d["radio_group"] = rg
                else:
                    d.pop("radio_group", None)
            elif "radio_group" in d:
                d.pop("radio_group", None)
            # Admin UI can omit these: one group per detected form section, option value = field key.
            if not str(d.get("radio_group") or "").strip():
                gl_inf = str(d.get("group_label") or "").strip()[:128]
                if gl_inf:
                    d["radio_group"] = gl_inf
                elif d.get("key"):
                    d["radio_group"] = str(d["key"]).strip()[:128]
            if not str(d.get("radio_group") or "").strip():
                it = "text"
                d.pop("radio_group", None)
                d.pop("radio_option", None)
            else:
                ro = d.get("radio_option")
                if ro is not None and not isinstance(ro, str):
                    d.pop("radio_option", None)
                elif isinstance(ro, str):
                    ro = ro.strip()[:256]
                    if ro:
                        d["radio_option"] = ro
                    else:
                        d.pop("radio_option", None)
                if d.get("radio_group") and not d.get("radio_option") and d.get("key"):
                    d["radio_option"] = str(d["key"]).strip()[:256]
        d["input_type"] = it
        out.append(d)
    return out


def merge_detected_with_saved_input_types(
    previous: list[dict[str, Any]] | None,
    detected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """After re-detecting {{}} from document text, keep input_type from previous schema when keys match.

    ``group_label`` comes from the latest document text when detection finds one; otherwise
    the previous value is kept (e.g. legacy rows with no heading in the file).
    """
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
        merged_row: dict[str, Any] = {**row, "input_type": it}
        gl_new = row.get("group_label")
        gl_prev = prev.get("group_label")
        if isinstance(gl_new, str) and gl_new.strip():
            merged_row["group_label"] = gl_new.strip()[:200]
        elif isinstance(gl_prev, str) and gl_prev.strip():
            merged_row["group_label"] = gl_prev.strip()[:200]
        if it == "radio":
            glm = str(merged_row.get("group_label") or "").strip()
            if glm:
                merged_row["radio_group"] = glm[:128]
            elif isinstance(prev.get("radio_group"), str) and str(prev.get("radio_group")).strip():
                merged_row["radio_group"] = str(prev.get("radio_group")).strip()[:128]
            ro_prev = prev.get("radio_option")
            if ro_prev is not None and str(ro_prev).strip():
                merged_row["radio_option"] = str(ro_prev).strip()[:256]
            elif row.get("key"):
                merged_row["radio_option"] = str(row["key"]).strip()[:256]
        merged.append(merged_row)

    return merged
