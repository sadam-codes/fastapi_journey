import base64
import os
import re
import mimetypes
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from helpers.form_field_detect import (
    ALLOWED_INPUT_TYPES,
    count_field_schema_display_groups,
    detect_dynamic_fields,
    merge_detected_with_saved_input_types,
    normalize_field_schema,
)
from helpers.form_fill import fill_docx, fill_image_overlay, fill_pdf
from helpers.form_text_extract import extract_plain_text_from_upload
from models.form_flow import FormSubmission, FormTemplate
from models.user import User
from schemas.form_schemas import (
    AdminSubmissionDetailResponse,
    AdminSubmissionListItem,
    SubmitBody,
    SubmitResponse,
    TemplateDetailResponse,
    TemplateListItem,
    UploadResponse,
)

MAX_UPLOAD_BYTES = int(os.getenv("FORM_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))

FILL_ROLES = [User.ROLE_USER]


def assert_user_can_fill(user: dict) -> None:
    if user.get("role") not in FILL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only standard user accounts may open and submit these forms.",
        )


def _build_filled_file(
    *,
    raw: bytes,
    original_filename: str,
    schema: list[dict[str, Any]],
    answers: dict[str, str],
) -> tuple[bytes, str, str]:
    lower = original_filename.lower()
    if lower.endswith(".docx"):
        blob = fill_docx(raw, schema, answers)
        return (
            blob,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            f"filled_{original_filename}",
        )
    if lower.endswith(".pdf"):
        blob = fill_pdf(raw, schema, answers)
        return blob, "application/pdf", f"filled_{original_filename}"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff", ".bmp")):
        blob = fill_image_overlay(raw, schema, answers)
        stem = original_filename.rsplit(".", 1)[0]
        return blob, "image/png", f"filled_{stem}.png"
    raise HTTPException(status_code=400, detail="Unsupported template file type for merge.")


async def admin_upload_template(
    *,
    filename: str | None,
    content_type: str | None,
    raw: bytes,
    title: str | None,
) -> UploadResponse:
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max {MAX_UPLOAD_BYTES} bytes.",
        )
    text = extract_plain_text_from_upload(filename=filename, raw=raw)
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No extractable text found. Add visible placeholders (e.g. {client_name}) or use OCR-friendly images.",
        )
    schema = normalize_field_schema(detect_dynamic_fields(text))
    stem = (filename or "template").rsplit(".", 1)[0].strip() or "template"
    display_title = (title or "").strip() or stem
    doc = await FormTemplate.create(
        title=display_title[:255],
        original_filename=filename[:255],
        mime_type=(content_type or "")[:128] or None,
        file_blob=raw,
        extracted_text=text[:500_000],
        fields_schema=schema,
    )
    msg = "Template saved."
    if schema:
        msg = "Template saved. Fill-in fields come from {field_name} placeholders in the text."
    return UploadResponse(
        id=doc.id,
        title=doc.title,
        original_filename=doc.original_filename,
        fields_schema=schema,
        char_count=len(text),
        message=msg,
        file_version=int(getattr(doc, "file_version", None) or 0),
        oo_key_nonce=int(getattr(doc, "oo_key_nonce", None) or 0),
    )


async def admin_update_template(
    *,
    template_id: int,
    raw: bytes | None,
    filename: str | None,
    content_type: str | None,
    title: str,
) -> UploadResponse:
    """Replace file and/or display title. Same id and submissions stay linked."""
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")

    title_clean = (title or "").strip()
    has_file = bool(raw and filename)

    if not has_file:
        if not title_clean:
            raise HTTPException(
                status_code=400,
                detail="Upload a new file and/or enter a display title to save changes.",
            )
        if title_clean == t.title:
            return UploadResponse(
                id=t.id,
                title=t.title,
                original_filename=t.original_filename,
                fields_schema=normalize_field_schema(list(t.fields_schema or [])),
                char_count=len(t.extracted_text or ""),
                message="No changes.",
                file_version=int(getattr(t, "file_version", None) or 0),
                oo_key_nonce=int(getattr(t, "oo_key_nonce", None) or 0),
            )
        t.title = title_clean[:255]
        await t.save()
        return UploadResponse(
            id=t.id,
            title=t.title,
            original_filename=t.original_filename,
            fields_schema=normalize_field_schema(list(t.fields_schema or [])),
            char_count=len(t.extracted_text or ""),
            message="Title updated.",
            file_version=int(getattr(t, "file_version", None) or 0),
            oo_key_nonce=int(getattr(t, "oo_key_nonce", None) or 0),
        )

    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max {MAX_UPLOAD_BYTES} bytes.",
        )
    text = extract_plain_text_from_upload(filename=filename, raw=raw)
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No extractable text found. Add visible placeholders (e.g. {client_name}) or use OCR-friendly images.",
        )
    detected = detect_dynamic_fields(text)
    schema = normalize_field_schema(merge_detected_with_saved_input_types(list(t.fields_schema or []), detected))
    t.extracted_text = text[:500_000]
    t.fields_schema = schema
    t.original_filename = filename[:255]
    t.mime_type = (content_type or "")[:128] or None
    t.oo_key_nonce = (getattr(t, "oo_key_nonce", None) or 0) + 1
    if title_clean:
        t.title = title_clean[:255]
    await t.save()

    msg = "Template file replaced."
    if schema:
        msg = "Template file replaced. Fill-in fields follow {field_name} placeholders in the text."
    return UploadResponse(
        id=t.id,
        title=t.title,
        original_filename=t.original_filename,
        fields_schema=schema,
        char_count=len(text),
        message=msg,
        file_version=int(getattr(t, "file_version", None) or 0),
        oo_key_nonce=int(getattr(t, "oo_key_nonce", None) or 0),
    )


async def admin_list_templates() -> list[TemplateListItem]:
    rows = await FormTemplate.all().order_by("-created_at")
    return [
        TemplateListItem(
            id=r.id,
            title=r.title,
            original_filename=r.original_filename,
            field_count=count_field_schema_display_groups(list(r.fields_schema or [])),
            created_at=r.created_at,
        )
        for r in rows
    ]


async def admin_get_template_detail(template_id: int) -> TemplateDetailResponse:
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")
    return TemplateDetailResponse(
        id=t.id,
        title=t.title,
        original_filename=t.original_filename,
        fields_schema=normalize_field_schema(list(t.fields_schema or [])),
        created_at=t.created_at,
        file_version=int(getattr(t, "file_version", None) or 0),
        oo_key_nonce=int(getattr(t, "oo_key_nonce", None) or 0),
    )


async def admin_patch_template_field_types(
    template_id: int,
    *,
    updates: list[dict[str, Any]],
) -> TemplateDetailResponse:
    """Set input_type per field; optional ``radio_group`` / ``radio_option`` for ``radio`` rows."""
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")
    current_list = normalize_field_schema(list(t.fields_schema or []))
    by_key = {str(r["key"]): dict(r) for r in current_list if r.get("key")}
    for item in updates:
        key = str(item.get("key", "")).strip()
        if not key or key not in by_key:
            raise HTTPException(status_code=400, detail=f"Unknown or invalid field key: {key!r}")
        it = str(item.get("input_type", "text")).strip().lower()
        if it not in ALLOWED_INPUT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid input_type for {key!r}: {it!r}. Allowed: {', '.join(sorted(ALLOWED_INPUT_TYPES))}.",
            )
        by_key[key]["input_type"] = it
        if it == "radio":
            by_key[key].pop("checkbox_group", None)
            by_key[key].pop("checkbox_option", None)
            by_key[key].pop("checkbox_question_id", None)
            by_key[key].pop("checkbox_option_keys", None)
            rg = item.get("radio_group")
            if rg is not None:
                by_key[key]["radio_group"] = str(rg).strip()[:128] if str(rg).strip() else None
                if not by_key[key]["radio_group"]:
                    by_key[key].pop("radio_group", None)
            ro = item.get("radio_option")
            if ro is not None:
                by_key[key]["radio_option"] = str(ro).strip()[:256] if str(ro).strip() else None
                if not by_key[key]["radio_option"]:
                    by_key[key].pop("radio_option", None)
        elif it == "checkbox":
            by_key[key].pop("radio_group", None)
            by_key[key].pop("radio_option", None)
            by_key[key].pop("radio_question_id", None)
            by_key[key].pop("radio_option_keys", None)
            cg = item.get("checkbox_group")
            if cg is not None:
                by_key[key]["checkbox_group"] = str(cg).strip()[:128] if str(cg).strip() else None
                if not by_key[key].get("checkbox_group"):
                    by_key[key].pop("checkbox_group", None)
            co = item.get("checkbox_option")
            if co is not None:
                by_key[key]["checkbox_option"] = str(co).strip()[:256] if str(co).strip() else None
                if not by_key[key].get("checkbox_option"):
                    by_key[key].pop("checkbox_option", None)
        else:
            by_key[key].pop("radio_group", None)
            by_key[key].pop("radio_option", None)
            by_key[key].pop("radio_question_id", None)
            by_key[key].pop("radio_option_keys", None)
            by_key[key].pop("checkbox_group", None)
            by_key[key].pop("checkbox_option", None)
            by_key[key].pop("checkbox_question_id", None)
            by_key[key].pop("checkbox_option_keys", None)
    new_schema = [normalize_field_schema([by_key[str(r["key"])]])[0] for r in current_list if r.get("key")]
    t.fields_schema = new_schema
    await t.save()
    return await admin_get_template_detail(template_id)


async def admin_delete_template(template_id: int) -> dict[str, Any]:
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")
    await t.delete()
    return {"message": "Template deleted.", "id": template_id}


async def admin_template_download_response(template_id: int) -> StreamingResponse:
    """Original file for admins to download, edit locally (e.g. add {fields}), and re-upload."""
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")

    raw = bytes(t.file_blob)
    guessed, _ = mimetypes.guess_type(t.original_filename)
    media_type = guessed or (t.mime_type or "application/octet-stream")
    safe_name = (t.original_filename or "template").replace("\r", " ").replace("\n", " ").replace('"', "'")[:200]

    return StreamingResponse(
        BytesIO(raw),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "private, no-store",
        },
    )


async def list_templates_for_fill_role(user: dict) -> list[TemplateListItem]:
    assert_user_can_fill(user)
    rows = await FormTemplate.all().order_by("-created_at")
    return [
        TemplateListItem(
            id=r.id,
            title=r.title,
            original_filename=r.original_filename,
            field_count=count_field_schema_display_groups(list(r.fields_schema or [])),
            created_at=r.created_at,
        )
        for r in rows
    ]


async def get_template_detail(template_id: int, user: dict) -> TemplateDetailResponse:
    assert_user_can_fill(user)
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")
    return TemplateDetailResponse(
        id=t.id,
        title=t.title,
        original_filename=t.original_filename,
        fields_schema=normalize_field_schema(list(t.fields_schema or [])),
        created_at=t.created_at,
        file_version=int(getattr(t, "file_version", None) or 0),
        oo_key_nonce=int(getattr(t, "oo_key_nonce", None) or 0),
    )


async def template_preview_response(template_id: int, user: dict) -> StreamingResponse:
    """Stream original template bytes for in-browser preview (admin or fill-eligible user)."""
    role = user.get("role")
    if role == User.ROLE_ADMIN:
        pass
    elif role == User.ROLE_USER:
        assert_user_can_fill(user)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to preview templates.")

    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")

    raw = bytes(t.file_blob)
    guessed, _ = mimetypes.guess_type(t.original_filename)
    media_type = guessed or (t.mime_type or "application/octet-stream")
    safe_name = (t.original_filename or "template").replace("\r", " ").replace("\n", " ").replace('"', "'")[:200]

    return StreamingResponse(
        BytesIO(raw),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            # Template bytes change after admin edits; avoid stale preview in the browser.
            "Cache-Control": "private, no-store",
        },
    )


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _radio_allowed_options(schema: list[dict[str, Any]], group: str) -> set[str]:
    opts: set[str] = set()
    g = group.strip()
    for row in schema:
        if str(row.get("input_type") or "").lower() != "radio":
            continue
        rgs = str(row.get("radio_group") or "").strip()
        if rgs != g:
            continue
        opt = str(row.get("radio_option") or row.get("key") or "").strip()
        if opt:
            opts.add(opt)
    return opts


def _normalize_radio_submission(schema: list[dict[str, Any]], group: str, raw: Any) -> str:
    s = "" if raw is None else str(raw).strip()
    if not s:
        return ""
    allowed = _radio_allowed_options(schema, group)
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail=f"No radio options configured for group {group!r}.",
        )
    if s in allowed:
        return s
    lower_map = {a.lower(): a for a in allowed}
    hit = lower_map.get(s.lower())
    if hit is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid radio choice for {group!r}: {raw!r}. Allowed: {', '.join(sorted(allowed))}.",
        )
    return hit


def _build_answers_from_submit(schema: list[dict[str, Any]], body: SubmitBody) -> dict[str, str]:
    src = dict(body.answers or {})
    out: dict[str, str] = {}
    seen_radio: set[str] = set()
    for row in schema:
        if str(row.get("input_type") or "").lower() != "radio":
            continue
        rg = str(row.get("radio_group") or "").strip()
        gkey = rg if rg else str(row.get("key", ""))
        if not gkey or gkey in seen_radio:
            continue
        seen_radio.add(gkey)
        out[gkey] = _normalize_radio_submission(schema, gkey, src.get(gkey))

    for row in schema:
        if str(row.get("input_type") or "").lower() == "radio":
            continue
        key = str(row["key"])
        if key in out:
            continue
        out[key] = _answer_value_for_type(row, src.get(key))
    return out


def _missing_answer_keys(schema: list[dict[str, Any]], answers: dict[str, str]) -> list[str]:
    missing: list[str] = []
    seen_radio: set[str] = set()
    for row in schema:
        it = str(row.get("input_type") or "text").strip().lower()
        if it == "checkbox":
            continue
        if it == "radio":
            gkey = str(row.get("radio_group") or row.get("key") or "").strip()
            if not gkey:
                continue
            if str(row.get("radio_group") or "").strip():
                if gkey in seen_radio:
                    continue
                seen_radio.add(gkey)
            if row.get("required") is True and not (answers.get(gkey) or "").strip():
                missing.append(gkey)
            continue
        key = str(row["key"])
        if _answer_is_empty(row, answers.get(key, "")):
            missing.append(key)
    return missing


def _answer_value_for_type(row: dict[str, Any], raw: Any) -> str:
    """Normalize client answer to a string stored in DB and used for merge."""
    it = str(row.get("input_type") or "text").strip().lower()
    if it not in ALLOWED_INPUT_TYPES:
        it = "text"
    s = "" if raw is None else str(raw).strip()

    if it == "checkbox":
        low = s.lower()
        return "true" if low in ("true", "1", "yes", "on") else ""

    if it == "radio":
        return s
        if not s:
            return ""
        try:
            n = float(s.replace(",", ""))
            if n.is_integer():
                return str(int(n))
            return str(n)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid number for field {row.get('key')!r}: {s!r}.",
            )

    if it == "date":
        if not s:
            return ""
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date for field {row.get('key')!r}; use YYYY-MM-DD.",
            )
        return s

    if it == "email":
        if not s:
            return ""
        if not _EMAIL_RE.match(s):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email for field {row.get('key')!r}.",
            )
        return s

    if it == "signature":
        if not s:
            return ""
        if not s.startswith("data:image/") or ";base64," not in s:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid signature for field {row.get('key')!r}; expected a data URL image.",
            )
        try:
            b64 = s.split(",", 1)[1]
            base64.b64decode(b64, validate=True)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid signature image for field {row.get('key')!r}.",
            ) from exc
        if len(b64) < 80:
            raise HTTPException(
                status_code=400,
                detail=f"Signature for field {row.get('key')!r} is too small or empty.",
            )
        return s

    return s


def _answer_is_empty(row: dict[str, Any], stored: str) -> bool:
    it = str(row.get("input_type") or "text").strip().lower()
    if it not in ALLOWED_INPUT_TYPES:
        it = "text"
    if it == "checkbox":
        # Unchecked is a valid answer (☐ in merge); never block submit for "empty" checkbox.
        return False
    if it == "radio":
        return False
    return not (stored or "").strip()


async def submit_template_answers(
    template_id: int,
    user: dict,
    body: SubmitBody,
) -> SubmitResponse:
    assert_user_can_fill(user)
    template = await FormTemplate.get_or_none(id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Form template not found.")
    schema = normalize_field_schema(list(template.fields_schema or []))
    if not schema:
        raise HTTPException(status_code=400, detail="This template has no detected fields to fill.")
    answers = _build_answers_from_submit(schema, body)
    missing = _missing_answer_keys(schema, answers)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing or empty answers for: {', '.join(missing)}",
        )
    raw = bytes(template.file_blob)
    filled_blob, filled_mime, filled_name = _build_filled_file(
        raw=raw,
        original_filename=template.original_filename,
        schema=schema,
        answers=answers,
    )
    uid = int(user["sub"])
    sub = await FormSubmission.create(
        template=template,
        user_id=uid,
        answers=answers,
        filled_file_blob=filled_blob,
        filled_mime_type=filled_mime[:128],
        filled_filename=filled_name[:255],
    )
    return SubmitResponse(
        submission_id=sub.id,
        filled_filename=filled_name,
        message="Form merged successfully. Download the filled file from the submissions list.",
    )


async def submission_download_response(submission_id: int, user: dict) -> StreamingResponse:
    sub = await FormSubmission.get_or_none(id=submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    uid = int(user["sub"])
    role = user.get("role")
    if sub.user_id != uid and role != User.ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed to download this submission.")
    if not sub.filled_file_blob:
        raise HTTPException(status_code=404, detail="Filled file is missing.")
    mime = sub.filled_mime_type or "application/octet-stream"
    name = sub.filled_filename or f"submission_{submission_id}"
    return StreamingResponse(
        BytesIO(bytes(sub.filled_file_blob)),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


async def list_submissions_for_user(user: dict) -> list[dict[str, Any]]:
    assert_user_can_fill(user)
    uid = int(user["sub"])
    rows = await FormSubmission.filter(user_id=uid).order_by("-created_at").select_related("template")
    out: list[dict[str, Any]] = []
    for s in rows:
        tpl = s.template
        out.append(
            {
                "id": s.id,
                "template_id": tpl.id,
                "template_title": tpl.title,
                "filled_filename": s.filled_filename,
                "created_at": s.created_at.isoformat(),
            }
        )
    return out


async def admin_list_submissions() -> list[AdminSubmissionListItem]:
    rows = await FormSubmission.all().order_by("-created_at").select_related("template", "user")
    out: list[AdminSubmissionListItem] = []
    for s in rows:
        tpl = s.template
        usr = s.user
        out.append(
            AdminSubmissionListItem(
                id=s.id,
                template_id=tpl.id,
                template_title=tpl.title,
                user_id=usr.id,
                user_email=usr.email,
                user_name=str(getattr(usr, "name", None) or ""),
                filled_filename=s.filled_filename,
                has_filled_file=bool(s.filled_file_blob),
                created_at=s.created_at,
            )
        )
    return out


async def admin_get_submission_detail(submission_id: int) -> AdminSubmissionDetailResponse:
    sub = await FormSubmission.filter(id=submission_id).select_related("template", "user").first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    tpl = sub.template
    usr = sub.user
    raw_answers = sub.answers or {}
    answers = {str(k): str(v) if v is not None else "" for k, v in raw_answers.items()}
    return AdminSubmissionDetailResponse(
        id=sub.id,
        template_id=tpl.id,
        template_title=tpl.title,
        template_original_filename=tpl.original_filename,
        fields_schema=list(tpl.fields_schema or []),
        user_id=usr.id,
        user_email=usr.email,
        user_name=str(getattr(usr, "name", None) or ""),
        answers=answers,
        filled_filename=sub.filled_filename,
        has_filled_file=bool(sub.filled_file_blob),
        created_at=sub.created_at,
    )


async def admin_submission_filled_preview_response(submission_id: int) -> StreamingResponse:
    """Inline stream of merged submission file for admin browser preview (PDF / image / etc.)."""
    sub = await FormSubmission.filter(id=submission_id).first()
    if not sub or not sub.filled_file_blob:
        raise HTTPException(status_code=404, detail="Submission or filled file not found.")
    raw = bytes(sub.filled_file_blob)
    name = sub.filled_filename or f"submission_{submission_id}"
    guessed, _ = mimetypes.guess_type(name)
    media_type = guessed or (sub.filled_mime_type or "application/octet-stream")
    safe = name.replace("\r", " ").replace("\n", " ").replace('"', "'")[:200]
    return StreamingResponse(
        BytesIO(raw),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe}"',
            "Cache-Control": "private, no-store",
        },
    )
