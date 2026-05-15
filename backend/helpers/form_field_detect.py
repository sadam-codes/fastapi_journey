import hashlib
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


_PH_RX = re.compile(r"(?<!\{)\{\s*([a-zA-Z0-9_,\s-]+?)\s*\}")
_PH_DB_RX = re.compile(r"(?<!\{)\{\{\s*([a-zA-Z0-9_,\s-]+?)\s*\}\}")
# Single-bracket captions for ``{…}`` fields only.
_BRACKET_CAPTION_RX = re.compile(r"(?<!\[)\[(?!\[)([^\]]+)\]")
# Explicit radio: ``[[RADIO_START:Group|Yes|No]] … [[RADIO_END]]`` (``[[RADIO_END]`` with one ``]`` is accepted).
_EXPLICIT_RADIO_BLOCK_RX = re.compile(
    r"\[\[\s*RADIO_START\s*:([^\]]+?)\]\]\s*([\s\S]*?)\[\[\s*RADIO_END\s*(?:\]\]|\])",
    re.IGNORECASE,
)
_EXPLICIT_RADIO_MAX_OPTS = 8
# Explicit checkbox (multi-select): ``[[CHECKBOX_START:Group|Opt1|…]]`` … ``{{keys}}`` … ``[[CHECKBOX_END]]``
_EXPLICIT_CHECKBOX_BLOCK_RX = re.compile(
    r"\[\[\s*CHECKBOX_START\s*:([^\]]+?)\]\]\s*([\s\S]*?)\[\[\s*CHECKBOX_END\s*(?:\]\]|\])",
    re.IGNORECASE,
)
_EXPLICIT_CHECKBOX_MAX_OPTS = 16
# Do not glue across a new roman/arabic section heading (e.g. ``IV. Health``).
_JOIN_SECTION_HEAD_RX = re.compile(r"^\s*(?:[IVXLC]{1,5}|[0-9]{1,2})\.\s+\S", re.I)
_CAPTION_JOIN_MAX_LINES = 24

# DOCX plain text often joins many prompts on one line; text before ``{`` is not a real section title.
_MAX_INLINE_PREFIX_FOR_SECTION = 140
# Stored ``group_label`` above this length is almost always flattened-paragraph noise.
_MAX_GROUP_LABEL_CHARS = 160
_MAX_DOC_BRACKET_LABEL_CHARS = 400
# Radio option text after ``]]`` is only the next word(s); flattened DOCX can put the rest of the page on one line.
_MAX_RADIO_OPTION_TAIL_CHARS = 96


def _strip_trailing_bracket_captions_from_prefix(prefix: str) -> str:
    """Remove trailing single ``[ caption ]`` chunks (not ``[[…]]``) from inline prefix."""
    s = (prefix or "").rstrip()
    while True:
        m = re.search(r"(?<!\[)\[(?!\[)([^\]]+)\]\s*$", s)
        if not m:
            break
        s = s[: m.start()].rstrip()
    return s.strip()


def _last_bracket_caption_before_placeholder(segment: str) -> str | None:
    """Text inside the last single ``[...]`` before a ``{…}`` placeholder (not ``[[…]]``)."""
    inner: str | None = None
    for m in _BRACKET_CAPTION_RX.finditer(segment):
        inner = m.group(1)
    if inner is None:
        return None
    s = inner.strip()
    if not s or len(s) > _MAX_DOC_BRACKET_LABEL_CHARS:
        return None
    return s


def _group_label_from_context(safe_prefix: str, active_section: str | None) -> str | None:
    """Prefer a short inline lead-in; ignore huge flattened-DOCX ``prefix`` blobs."""
    p = (safe_prefix or "").strip()
    a = (active_section or "").strip()
    if len(p) > _MAX_INLINE_PREFIX_FOR_SECTION:
        out = a if a else None
    else:
        out = (p or a) or None
    if out and len(out) > _MAX_GROUP_LABEL_CHARS:
        return out[:_MAX_GROUP_LABEL_CHARS].rstrip()
    return out or None


def _trim_radio_option_label_tail(tail: str) -> str:
    """Keep only a short human label after ``}}`` or ``]]`` (flattened DOCX often appends junk)."""
    s = (tail or "").strip()
    if not s:
        return ""
    s = s.split("\n", 1)[0].strip()
    cut = s.find("[[")
    if cut >= 0:
        s = s[:cut].strip()
    cut2 = s.find("{{")
    if cut2 >= 0:
        s = s[:cut2].strip()
    toks = s.split()
    if not toks:
        return ""
    if (
        len(toks) >= 2
        and len(toks[0]) <= 4
        and toks[0].lower() in {"a", "an", "the", "in", "on", "at", "of", "to"}
    ):
        s = f"{toks[0]} {toks[1]}".strip()
    else:
        s = toks[0]
    if "[" in s:
        s = s.split("[", 1)[0].strip()
    s = s.strip(".,;: \t")
    if len(s) > _MAX_RADIO_OPTION_TAIL_CHARS:
        s = s[:_MAX_RADIO_OPTION_TAIL_CHARS].rstrip()
    if len(s) > 24:
        m = re.search(r"\[(?!\[)", s)
        if m and m.start() > 0:
            s = s[: m.start()].strip()
    return s


def _radio_option_label_from_tail(tail: str) -> str:
    """Text after ``]]`` until the next ``[[``: prefer `` (Yes) `` / ``(No)`` and ignore anything after the closing ``)``."""
    raw = (tail or "").strip()
    if not raw:
        return ""
    one_line = raw.split("\n", 1)[0].strip()
    s = one_line.lstrip()
    if s.startswith("("):
        depth = 0
        end = -1
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end >= 0:
            return s[1:end].strip()
    return _trim_radio_option_label_tail(one_line)


def _collapse_whitespace_inside_double_bracket_runs(text: str) -> str:
    """Normalize ``[[ … ]]`` so newlines/extra spaces inside the token do not break detection."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        j = text.find("[[", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = text.find("]]", j + 2)
        if k < 0:
            out.append(text[j:])
            break
        inner = text[j + 2 : k]
        inner_norm = re.sub(r"\s+", " ", inner).strip()
        out.append("[[" + inner_norm + "]]")
        i = k + 2
    return "".join(out)


def _rows_from_explicit_radio_block(
    payload_raw: str,
    body: str,
    *,
    block_uid: int,
    ph_occurrence: dict[str, int],
    base_seq: dict[str, int],
) -> list[dict[str, Any]]:
    payload = re.sub(r"\s+", " ", (payload_raw or "").strip())
    parts = [p.strip() for p in payload.split("|")]
    parts = [p for p in parts if p]
    if len(parts) < 3:
        return []
    group_label = parts[0].strip()
    option_labels = parts[1:]
    if len(option_labels) < 2 or len(option_labels) > _EXPLICIT_RADIO_MAX_OPTS:
        return []
    matches = list(_PH_DB_RX.finditer(body or ""))
    if len(matches) != len(option_labels):
        return []
    slug = "_".join(_normalize_key(x) or "x" for x in option_labels)
    if len(slug) > 80:
        slug = hashlib.md5(payload.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    line_fp = hashlib.md5(f"{block_uid}\0{payload}".encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    radio_group = ("rbexp_" + slug + "_" + line_fp)[:128]
    qid = f"rqexp_{block_uid}"
    peer_keys: list[str] = []
    out: list[dict[str, Any]] = []
    for i, m in enumerate(matches):
        inner_raw = m.group(1)
        nk = _normalize_key(inner_raw)
        if not nk:
            return []
        raw_full = m.group(0)
        match_idx = ph_occurrence.get(raw_full, 0)
        ph_occurrence[raw_full] = match_idx + 1
        base_seq[nk] = base_seq.get(nk, 0) + 1
        seq = base_seq[nk]
        key = nk if seq == 1 else f"{nk}_{seq}"
        peer_keys.append(key)
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        tail = body[m.end() : next_start]
        label = _radio_option_label_from_tail(tail)
        if not label:
            label = option_labels[i]
        opt_slug = _normalize_key(option_labels[i]) or nk
        row: dict[str, Any] = {
            "key": key,
            "label": label,
            "placeholders": [raw_full],
            "placeholder_match_index": match_idx,
            "input_type": "radio",
            "radio_group": radio_group,
            "radio_option": opt_slug,
            "radio_question_id": qid,
            "radio_option_keys": [],
        }
        if group_label:
            row["group_label"] = group_label[:200]
        out.append(row)
    for r in out:
        r["radio_option_keys"] = list(peer_keys)
    return out


def _rows_from_explicit_checkbox_block(
    payload_raw: str,
    body: str,
    *,
    block_uid: int,
    ph_occurrence: dict[str, int],
    base_seq: dict[str, int],
) -> list[dict[str, Any]]:
    payload = re.sub(r"\s+", " ", (payload_raw or "").strip())
    parts = [p.strip() for p in payload.split("|")]
    parts = [p for p in parts if p]
    if len(parts) < 3:
        return []
    group_label = parts[0].strip()
    option_labels = parts[1:]
    if len(option_labels) < 2 or len(option_labels) > _EXPLICIT_CHECKBOX_MAX_OPTS:
        return []
    matches = list(_PH_DB_RX.finditer(body or ""))
    if len(matches) != len(option_labels):
        return []
    slug = "_".join(_normalize_key(x) or "x" for x in option_labels)
    if len(slug) > 80:
        slug = hashlib.md5(payload.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    line_fp = hashlib.md5(f"{block_uid}\0{payload}".encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    checkbox_group = ("cbexp_" + slug + "_" + line_fp)[:128]
    qid = f"cqexp_{block_uid}"
    peer_keys: list[str] = []
    out: list[dict[str, Any]] = []
    for i, m in enumerate(matches):
        inner_raw = m.group(1)
        nk = _normalize_key(inner_raw)
        if not nk:
            return []
        raw_full = m.group(0)
        match_idx = ph_occurrence.get(raw_full, 0)
        ph_occurrence[raw_full] = match_idx + 1
        base_seq[nk] = base_seq.get(nk, 0) + 1
        seq = base_seq[nk]
        key = nk if seq == 1 else f"{nk}_{seq}"
        peer_keys.append(key)
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        tail = body[m.end() : next_start]
        label = _radio_option_label_from_tail(tail)
        if not label:
            label = option_labels[i]
        opt_slug = _normalize_key(option_labels[i]) or nk
        row: dict[str, Any] = {
            "key": key,
            "label": label,
            "placeholders": [raw_full],
            "placeholder_match_index": match_idx,
            "input_type": "checkbox",
            "checkbox_group": checkbox_group,
            "checkbox_option": opt_slug,
            "checkbox_question_id": qid,
            "checkbox_option_keys": [],
        }
        if group_label:
            row["group_label"] = group_label[:200]
        out.append(row)
    for r in out:
        r["checkbox_option_keys"] = list(peer_keys)
    return out


def _unclosed_single_square_bracket_before_double_bracket(s: str) -> bool:
    """True if there is an unclosed ``[`` … ``]`` span before the first ``[[`` (caption split across lines)."""
    anchor = s.find("[[")
    segment = s if anchor < 0 else s[:anchor]
    i = 0
    n = len(segment)
    depth = 0
    while i < n:
        if i + 1 < n and segment[i : i + 2] == "[[":
            i += 2
            continue
        if i + 1 < n and segment[i : i + 2] == "]]":
            i += 2
            continue
        ch = segment[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        i += 1
    return depth > 0


def _join_lines_for_unclosed_captions(lines: list[str]) -> list[str]:
    """Glue paragraphs when Word broke ``[Caption`` … ``text] {field}`` across lines."""
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        if not raw.strip():
            out.append(raw)
            i += 1
            continue
        if not _unclosed_single_square_bracket_before_double_bracket(raw):
            out.append(raw)
            i += 1
            continue
        merged = raw.rstrip()
        j = i + 1
        joined_any = False
        for _ in range(_CAPTION_JOIN_MAX_LINES):
            if not _unclosed_single_square_bracket_before_double_bracket(merged):
                break
            while j < n and not lines[j].strip():
                j += 1
            if j >= n:
                break
            nxt = lines[j].strip()
            if _JOIN_SECTION_HEAD_RX.match(nxt):
                break
            merged = merged + " " + nxt
            joined_any = True
            j += 1
        out.append(merged)
        i = j if joined_any else i + 1
    return out


def _collapse_newlines_after_double_placeholder_keys(text: str) -> str:
    """Turn ``}}`` + line breaks + label into ``}} `` + label (Word/table extraction often splits here).

    Does not touch ``}}`` when the next non-whitespace token is ``{{`` (another placeholder).
    """
    return re.sub(r"(\}\})(\s*\n\s*)+(?!\s*\{\{)", r"\1 ", text)


def detect_dynamic_fields(text: str) -> list[dict[str, Any]]:
    """Detect ``{field}`` text fields and explicit ``[[RADIO_START:…]]`` … ``[[RADIO_END]]`` radio groups.

    **Curly placeholders** — each ``{…}`` is a field (default ``text``). Optional single-bracket
    caption immediately before it on the same line::

        [What is your name] {full_name}

    **Explicit radio** — one logical question, fixed option labels in the start tag, one
    ``{{storage_key}}`` per option (same count as ``|``-separated options after the group title)::

        [[RADIO_START:Lives with client|Yes|No]]
        {{lives_with_client_yes}} Yes {{lives_with_client_no}} No
        [[RADIO_END]]

    ``[[RADIO_END]]`` closes the block; ``[[RADIO_END]`` (single ``]``) is also accepted when Word
    drops one bracket.

    Word often splits a paragraph (or table cell) between ``{{key}}`` and the visible option
    label; newlines there are collapsed to a space so the block still matches.

    The first ``|``-segment is ``group_label``; the rest are option labels. Each radio row uses
    the normalized ``{{…}}`` inner as ``key``, ``radio_option`` from the matching option label,
    and ``radio_question_id`` / ``radio_option_keys`` like other radios.
    """
    rx = _PH_RX
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u2028\u2029\v\f]", "\n", text)
    text = _collapse_newlines_after_double_placeholder_keys(text)
    text = _collapse_whitespace_inside_double_bracket_runs(text)
    lines = _join_lines_for_unclosed_captions(text.split("\n"))
    work = "\n".join(lines)

    base_seq: dict[str, int] = {}
    ph_occurrence: dict[str, int] = {}
    blocks: list[tuple[int, int, list[dict[str, Any]]]] = []
    block_uid = 0
    for m in _EXPLICIT_RADIO_BLOCK_RX.finditer(work):
        br = _rows_from_explicit_radio_block(
            m.group(1),
            m.group(2),
            block_uid=block_uid,
            ph_occurrence=ph_occurrence,
            base_seq=base_seq,
        )
        blocks.append((m.start(), m.end(), br))
        block_uid += 1
    for m in _EXPLICIT_CHECKBOX_BLOCK_RX.finditer(work):
        br = _rows_from_explicit_checkbox_block(
            m.group(1),
            m.group(2),
            block_uid=block_uid,
            ph_occurrence=ph_occurrence,
            base_seq=base_seq,
        )
        blocks.append((m.start(), m.end(), br))
        block_uid += 1
    blocks.sort(key=lambda x: x[0])

    events: list[tuple[int, str, Any]] = [(bs, "b", (be, br)) for bs, be, br in blocks]
    for m in rx.finditer(work):
        if any(bs <= m.start() < be for bs, be, _ in blocks):
            continue
        events.append((m.start(), "p", m))
    events.sort(key=lambda x: x[0])

    _section_roman = re.compile(r"^\s*[IVXLCDM]{1,5}\.\s+\S", re.I)
    _section_numbered = re.compile(r"^\s*\d{1,2}[\).\s]\s*\S")

    def _is_section_heading_line(s: str) -> bool:
        if not s or rx.search(s):
            return False
        if re.search(r"\[\[\s*RADIO_START", s, re.I):
            return False
        if re.search(r"\[\[\s*CHECKBOX_START", s, re.I):
            return False
        if _PH_DB_RX.search(s):
            return False
        if s.endswith(":"):
            return True
        if "(" in s and s.endswith(")"):
            return True
        if s.endswith("?"):
            return len(s.strip()) >= 10
        if _section_numbered.match(s):
            return True
        return bool(_section_roman.match(s))

    def _active_section_before_line_start(line_start: int) -> str | None:
        active: str | None = None
        pos = 0
        for segment in work.split("\n"):
            if pos >= line_start:
                break
            stripped = segment.strip()
            if stripped and not rx.search(segment) and not _PH_DB_RX.search(segment):
                if (
                    not re.search(r"\[\[\s*RADIO_START", segment, re.I)
                    and not re.search(r"\[\[\s*CHECKBOX_START", segment, re.I)
                    and _is_section_heading_line(stripped)
                ):
                    active = stripped[:200]
            pos += len(segment) + 1
        return active

    rows: list[dict[str, Any]] = []
    for _pos, typ, payload in events:
        if typ == "b":
            _be, br = payload
            rows.extend(br)
            continue
        m = payload
        line_start = work.rfind("\n", 0, m.start()) + 1
        active_section = _active_section_before_line_start(line_start)
        rel = work[line_start:]
        line_matches = list(rx.finditer(rel))
        m_rel = m.start() - line_start
        idx = next((i for i, pm in enumerate(line_matches) if pm.start() == m_rel), None)
        if idx is None:
            continue

        fm = line_matches[0]
        first_ph_global = line_start + fm.start()
        lead = work[line_start:first_ph_global]
        safe_lead = _strip_trailing_bracket_captions_from_prefix(lead.strip())
        group_label = _group_label_from_context(safe_lead, active_section)
        if safe_lead and len(safe_lead) <= _MAX_INLINE_PREFIX_FOR_SECTION:
            active_section = safe_lead[:200]

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
        prev_ph_end = line_start + (line_matches[idx - 1].end() if idx > 0 else 0)
        seg = work[prev_ph_end : m.start()]
        doc_caption = _last_bracket_caption_before_placeholder(seg)
        label = doc_caption if doc_caption else _label_from_inner(inner, key)
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
            gl = gl.strip()
            if gl and len(gl) <= _MAX_GROUP_LABEL_CHARS:
                d["group_label"] = gl
            else:
                d.pop("group_label", None)
        elif "group_label" in d:
            d.pop("group_label", None)
        lb = d.get("label")
        if isinstance(lb, str):
            lb = lb.strip()[:_MAX_DOC_BRACKET_LABEL_CHARS]
            pm_i = d.get("placeholder_match_index")
            if isinstance(pm_i, int) and pm_i > 0 and lb:
                m_suf = re.search(r" \(([1-9][0-9]*)\)$", lb)
                if m_suf and int(m_suf.group(1)) == pm_i + 1:
                    lb = lb[: m_suf.start()].rstrip()
            if lb:
                d["label"] = lb
            else:
                d.pop("label", None)
        elif "label" in d:
            d.pop("label", None)
        d.pop("frontend_label", None)
        it = str(row.get("input_type") or "text").strip().lower()
        if it not in ALLOWED_INPUT_TYPES:
            it = "text"
        if it != "radio":
            d.pop("radio_group", None)
            d.pop("radio_option", None)
            d.pop("radio_question_id", None)
            d.pop("radio_option_keys", None)
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
                d.pop("radio_question_id", None)
                d.pop("radio_option_keys", None)
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
                    kk = str(d["key"]).strip()
                    mro = re.match(r"^r\d+_(.+)$", kk)
                    if mro:
                        d["radio_option"] = mro.group(1).strip()[:256]
                    else:
                        d["radio_option"] = kk[:256]
            rqid = d.get("radio_question_id")
            if isinstance(rqid, str) and rqid.strip():
                d["radio_question_id"] = rqid.strip()[:128]
            else:
                d.pop("radio_question_id", None)
            rok = d.get("radio_option_keys")
            if isinstance(rok, list) and rok:
                d["radio_option_keys"] = [str(x).strip()[:256] for x in rok if str(x).strip()][:8]
            else:
                d.pop("radio_option_keys", None)
        if it != "checkbox":
            d.pop("checkbox_group", None)
            d.pop("checkbox_option", None)
            d.pop("checkbox_question_id", None)
            d.pop("checkbox_option_keys", None)
        else:
            cg = d.get("checkbox_group")
            if isinstance(cg, str):
                cg = cg.strip()[:128]
                if cg:
                    d["checkbox_group"] = cg
                else:
                    d.pop("checkbox_group", None)
            elif "checkbox_group" in d:
                d.pop("checkbox_group", None)
            co = d.get("checkbox_option")
            if co is not None and not isinstance(co, str):
                d.pop("checkbox_option", None)
            elif isinstance(co, str):
                co = co.strip()[:256]
                if co:
                    d["checkbox_option"] = co
                else:
                    d.pop("checkbox_option", None)
            if d.get("checkbox_group") and not d.get("checkbox_option") and d.get("key"):
                kk = str(d["key"]).strip()
                d["checkbox_option"] = kk[:256]
            cqid = d.get("checkbox_question_id")
            if isinstance(cqid, str) and cqid.strip():
                d["checkbox_question_id"] = cqid.strip()[:128]
            else:
                d.pop("checkbox_question_id", None)
            cok = d.get("checkbox_option_keys")
            if isinstance(cok, list) and cok:
                d["checkbox_option_keys"] = [str(x).strip()[:256] for x in cok if str(x).strip()][
                    :_EXPLICIT_CHECKBOX_MAX_OPTS
                ]
            else:
                d.pop("checkbox_option_keys", None)
        d["input_type"] = it
        out.append(d)
    return out


def merge_detected_with_saved_input_types(
    previous: list[dict[str, Any]] | None,
    detected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """After re-detecting placeholders from document text, keep input_type from previous schema when keys match."""
    prev_list = [r for r in (previous or []) if isinstance(r, dict) and r.get("key")]
    prev_map = {str(r["key"]): r for r in prev_list}

    def _prev_for_detected_row(cur: dict[str, Any]) -> dict[str, Any]:
        k = str(cur.get("key", ""))
        if k in prev_map:
            return prev_map[k]
        phs = tuple(cur.get("placeholders") or [])
        pm = cur.get("placeholder_match_index")
        for pr in prev_list:
            if tuple(pr.get("placeholders") or []) == phs and pr.get("placeholder_match_index") == pm:
                return pr
        return {}

    merged: list[dict[str, Any]] = []
    for row in detected:
        if not isinstance(row, dict) or not row.get("key"):
            continue
        key = str(row["key"])
        prev = _prev_for_detected_row(row)
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
        lb_new = row.get("label")
        lb_prev = prev.get("label")
        if isinstance(lb_new, str) and lb_new.strip():
            merged_row["label"] = lb_new.strip()[:_MAX_DOC_BRACKET_LABEL_CHARS]
        elif isinstance(lb_prev, str) and lb_prev.strip():
            merged_row["label"] = lb_prev.strip()[:_MAX_DOC_BRACKET_LABEL_CHARS]
        if it == "radio":
            rg_new = str(row.get("radio_group") or "").strip()
            if rg_new:
                merged_row["radio_group"] = rg_new[:128]
            else:
                glm = str(merged_row.get("group_label") or "").strip()
                if glm:
                    merged_row["radio_group"] = glm[:128]
                elif isinstance(prev.get("radio_group"), str) and str(prev.get("radio_group")).strip():
                    merged_row["radio_group"] = str(prev.get("radio_group")).strip()[:128]
            ro_prev = prev.get("radio_option")
            ro_det = str(row.get("radio_option") or "").strip()
            if ro_prev is not None and str(ro_prev).strip():
                merged_row["radio_option"] = str(ro_prev).strip()[:256]
            elif ro_det:
                merged_row["radio_option"] = ro_det[:256]
            elif row.get("key"):
                merged_row["radio_option"] = str(row["key"]).strip()[:256]
            rqid_det = row.get("radio_question_id")
            if isinstance(rqid_det, str) and rqid_det.strip():
                merged_row["radio_question_id"] = rqid_det.strip()[:128]
            elif isinstance(prev.get("radio_question_id"), str) and str(prev.get("radio_question_id")).strip():
                merged_row["radio_question_id"] = str(prev.get("radio_question_id")).strip()[:128]
            rok_det = row.get("radio_option_keys")
            if isinstance(rok_det, list) and rok_det:
                merged_row["radio_option_keys"] = [str(x).strip()[:256] for x in rok_det if str(x).strip()][:8]
            elif isinstance(prev.get("radio_option_keys"), list) and prev.get("radio_option_keys"):
                merged_row["radio_option_keys"] = [
                    str(x).strip()[:256] for x in prev.get("radio_option_keys") or [] if str(x).strip()
                ][:8]
        elif it == "checkbox":
            cg_new = str(row.get("checkbox_group") or "").strip()
            if cg_new:
                merged_row["checkbox_group"] = cg_new[:128]
            else:
                glm = str(merged_row.get("group_label") or "").strip()
                if glm:
                    merged_row["checkbox_group"] = glm[:128]
                elif isinstance(prev.get("checkbox_group"), str) and str(prev.get("checkbox_group")).strip():
                    merged_row["checkbox_group"] = str(prev.get("checkbox_group")).strip()[:128]
            co_prev = prev.get("checkbox_option")
            co_det = str(row.get("checkbox_option") or "").strip()
            if co_prev is not None and str(co_prev).strip():
                merged_row["checkbox_option"] = str(co_prev).strip()[:256]
            elif co_det:
                merged_row["checkbox_option"] = co_det[:256]
            elif row.get("key"):
                merged_row["checkbox_option"] = str(row["key"]).strip()[:256]
            cqid_det = row.get("checkbox_question_id")
            if isinstance(cqid_det, str) and cqid_det.strip():
                merged_row["checkbox_question_id"] = cqid_det.strip()[:128]
            elif isinstance(prev.get("checkbox_question_id"), str) and str(prev.get("checkbox_question_id")).strip():
                merged_row["checkbox_question_id"] = str(prev.get("checkbox_question_id")).strip()[:128]
            cok_det = row.get("checkbox_option_keys")
            if isinstance(cok_det, list) and cok_det:
                merged_row["checkbox_option_keys"] = [
                    str(x).strip()[:256] for x in cok_det if str(x).strip()
                ][: _EXPLICIT_CHECKBOX_MAX_OPTS]
            elif isinstance(prev.get("checkbox_option_keys"), list) and prev.get("checkbox_option_keys"):
                merged_row["checkbox_option_keys"] = [
                    str(x).strip()[:256] for x in prev.get("checkbox_option_keys") or [] if str(x).strip()
                ][: _EXPLICIT_CHECKBOX_MAX_OPTS]
        merged_row.pop("frontend_label", None)
        merged.append(merged_row)

    return merged


def _inferred_radio_group_key(row: dict[str, Any]) -> str:
    """Match admin UI ``inferredRadioGroup``: cluster consecutive radio rows."""
    rg = str(row.get("radio_group") or "").strip()
    if rg:
        return rg[:128]
    gl = str(row.get("group_label") or "").strip()
    if gl:
        return gl[:128]
    return str(row.get("key") or "").strip()[:128]


def _inferred_checkbox_group_key(row: dict[str, Any]) -> str:
    """Cluster consecutive explicit checkbox rows (same ``checkbox_group``)."""
    cg = str(row.get("checkbox_group") or "").strip()
    if cg:
        return cg[:128]
    gl = str(row.get("group_label") or "").strip()
    if gl:
        return gl[:128]
    return str(row.get("key") or "").strip()[:128]


def count_field_schema_display_groups(schema: list[dict[str, Any]] | None) -> int:
    """Count UI blocks: each radio group = 1; each explicit checkbox group = 1; else one per row."""
    rows = [r for r in list(schema or []) if isinstance(r, dict) and r.get("key")]
    if not rows:
        return 0
    n = 0
    i = 0
    while i < len(rows):
        it = str(rows[i].get("input_type") or "text").strip().lower()
        if it == "radio":
            gk = _inferred_radio_group_key(rows[i])
            j = i + 1
            while j < len(rows):
                it2 = str(rows[j].get("input_type") or "text").strip().lower()
                if it2 != "radio" or _inferred_radio_group_key(rows[j]) != gk:
                    break
                j += 1
            n += 1
            i = j
            continue
        if it == "checkbox" and str(rows[i].get("checkbox_group") or "").strip():
            gk = _inferred_checkbox_group_key(rows[i])
            j = i + 1
            while j < len(rows):
                it2 = str(rows[j].get("input_type") or "text").strip().lower()
                if it2 != "checkbox" or not str(rows[j].get("checkbox_group") or "").strip():
                    break
                if _inferred_checkbox_group_key(rows[j]) != gk:
                    break
                j += 1
            n += 1
            i = j
            continue
        n += 1
        i += 1
    return n
