import os
import mimetypes
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from helpers.form_field_detect import detect_dynamic_fields
from helpers.form_fill import fill_docx, fill_image_overlay, fill_pdf
from helpers.form_text_extract import extract_plain_text_from_upload
from models.form_flow import FormSubmission, FormTemplate
from models.user import User
from schemas.form_schemas import (
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
            detail="No extractable text found. Add visible placeholders (e.g. {{client_name}}) or use OCR-friendly images.",
        )
    schema = detect_dynamic_fields(text)
    display_title = (title or "").strip() or filename
    doc = await FormTemplate.create(
        title=display_title[:255],
        original_filename=filename[:255],
        mime_type=(content_type or "")[:128] or None,
        file_blob=raw,
        extracted_text=text[:500_000],
        fields_schema=schema,
    )
    msg = "Template saved; form fields are taken only from {{field_name}} placeholders."
    if not schema:
        msg = (
            "Template saved but no {{field_name}} placeholders were found in the text. "
            "Wrap each fill-in in double braces, e.g. {{date}}, {{client_name}}, then re-upload."
        )
    return UploadResponse(
        id=doc.id,
        title=doc.title,
        original_filename=doc.original_filename,
        fields_schema=schema,
        char_count=len(text),
        message=msg,
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
                fields_schema=list(t.fields_schema or []),
                char_count=len(t.extracted_text or ""),
                message="No changes.",
            )
        t.title = title_clean[:255]
        await t.save()
        return UploadResponse(
            id=t.id,
            title=t.title,
            original_filename=t.original_filename,
            fields_schema=list(t.fields_schema or []),
            char_count=len(t.extracted_text or ""),
            message="Title updated.",
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
            detail="No extractable text found. Add visible placeholders (e.g. {{client_name}}) or use OCR-friendly images.",
        )
    schema = detect_dynamic_fields(text)
    t.file_blob = raw
    t.extracted_text = text[:500_000]
    t.fields_schema = schema
    t.original_filename = filename[:255]
    t.mime_type = (content_type or "")[:128] or None
    if title_clean:
        t.title = title_clean[:255]
    await t.save()

    msg = "Template file replaced; form fields follow {{field_name}} placeholders only."
    if not schema:
        msg = (
            "File updated but no {{field_name}} placeholders were found. "
            "Add markers such as {{date}}, {{client_name}}, then save again."
        )
    return UploadResponse(
        id=t.id,
        title=t.title,
        original_filename=t.original_filename,
        fields_schema=schema,
        char_count=len(text),
        message=msg,
    )


async def admin_list_templates() -> list[TemplateListItem]:
    rows = await FormTemplate.all().order_by("-created_at")
    return [
        TemplateListItem(
            id=r.id,
            title=r.title,
            original_filename=r.original_filename,
            field_count=len(r.fields_schema or []),
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
        fields_schema=list(t.fields_schema or []),
        created_at=t.created_at,
    )


async def admin_delete_template(template_id: int) -> dict[str, Any]:
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")
    await t.delete()
    return {"message": "Template deleted.", "id": template_id}


async def admin_template_download_response(template_id: int) -> StreamingResponse:
    """Original file for admins to download, edit locally (e.g. add {{fields}}), and re-upload."""
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
            field_count=len(r.fields_schema or []),
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
        fields_schema=list(t.fields_schema or []),
        created_at=t.created_at,
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


async def submit_template_answers(
    template_id: int,
    user: dict,
    body: SubmitBody,
) -> SubmitResponse:
    assert_user_can_fill(user)
    template = await FormTemplate.get_or_none(id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Form template not found.")
    schema: list[dict[str, Any]] = list(template.fields_schema or [])
    if not schema:
        raise HTTPException(status_code=400, detail="This template has no detected fields to fill.")
    answers = {k: str(v) for k, v in body.answers.items()}
    missing = [row["key"] for row in schema if not answers.get(row["key"], "").strip()]
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

