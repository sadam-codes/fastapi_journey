import json
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from helpers import onlyoffice_helper
from helpers.auth_helper import get_current_user, require_roles
from helpers import form_flow_helper
from models.user import User
from schemas.form_schemas import (
    AdminSubmissionDetailResponse,
    AdminSubmissionListItem,
    OnlyOfficeBootstrapResponse,
    OnlyOfficeForcesaveBody,
    PatchFieldTypesBody,
    SubmitBody,
    SubmitResponse,
    TemplateDetailResponse,
    TemplateListItem,
    UploadResponse,
)

router = APIRouter(prefix="/forms", tags=["forms"])


@router.post("/admin/upload", response_model=UploadResponse)
async def admin_upload_form(
    file: UploadFile = File(...),
    title: str | None = Query(None, max_length=255),
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> UploadResponse:
    raw = await file.read()
    return await form_flow_helper.admin_upload_template(
        filename=file.filename,
        content_type=file.content_type,
        raw=raw,
        title=title,
    )


@router.get("/admin/templates", response_model=list[TemplateListItem])
async def admin_list_templates(
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> list[TemplateListItem]:
    return await form_flow_helper.admin_list_templates()


@router.get("/admin/submissions", response_model=list[AdminSubmissionListItem])
async def admin_list_submissions(
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> list[AdminSubmissionListItem]:
    return await form_flow_helper.admin_list_submissions()


@router.get("/admin/submissions/{submission_id}", response_model=AdminSubmissionDetailResponse)
async def admin_get_submission(
    submission_id: int,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> AdminSubmissionDetailResponse:
    return await form_flow_helper.admin_get_submission_detail(submission_id)


@router.get("/admin/submissions/{submission_id}/preview")
async def admin_submission_filled_preview(
    submission_id: int,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
):
    return await form_flow_helper.admin_submission_filled_preview_response(submission_id)


@router.get("/admin/submissions/{submission_id}/onlyoffice/bootstrap", response_model=OnlyOfficeBootstrapResponse)
async def admin_submission_filled_onlyoffice_bootstrap(
    submission_id: int,
    user: dict = Depends(require_roles([User.ROLE_ADMIN])),
    v: int = Query(0, ge=0, le=2_000_000_000, description="Cache-bust for viewer document key."),
) -> OnlyOfficeBootstrapResponse:
    data = await onlyoffice_helper.onlyoffice_submission_filled_bootstrap(
        submission_id=submission_id, user=user, view_cache_bust=v
    )
    return OnlyOfficeBootstrapResponse(**data)


@router.get("/admin/onlyoffice/status")
async def admin_onlyoffice_status(
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> dict[str, Any]:
    oo = onlyoffice_helper.onlyoffice_enabled()
    jwt_on = onlyoffice_helper.onlyoffice_jwt_signing_enabled()
    hint = None
    if oo and not jwt_on:
        hint = (
            "If the editor shows “document security token is not correctly formed”, your Document Server "
            "expects JWT: set ONLYOFFICE_JWT_SECRET to match the server secret (often the same as Docker JWT_SECRET)."
        )
    public = onlyoffice_helper.PUBLIC_APP_URL
    callback_post = f"{public}/forms/internal/onlyoffice/callback"
    return {
        "enabled": oo,
        "jwt_signing_enabled": jwt_on,
        "jwt_secret_configured": bool(onlyoffice_helper.ONLYOFFICE_JWT_SECRET),
        "hint": hint,
        "public_app_url": public,
        "callback_post_url": callback_post,
        "callback_poll_seconds": onlyoffice_helper.ONLYOFFICE_CALLBACK_POLL_SECONDS,
        "document_server_url": onlyoffice_helper.ONLYOFFICE_DOCUMENT_SERVER_URL or None,
    }


@router.get("/admin/templates/{template_id}/onlyoffice/bootstrap", response_model=OnlyOfficeBootstrapResponse)
async def admin_onlyoffice_bootstrap(
    template_id: int,
    mode: str = Query("edit", pattern="^(edit|view)$"),
    v: int = Query(0, ge=0, le=2_000_000_000, description="Preview reload counter; bumps OnlyOffice document key."),
    user: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> OnlyOfficeBootstrapResponse:
    data = await onlyoffice_helper.onlyoffice_bootstrap(
        template_id=template_id, user=user, mode=mode, admin_route=True, view_cache_bust=v
    )
    return OnlyOfficeBootstrapResponse(**data)


@router.post("/admin/templates/{template_id}/onlyoffice/forcesave")
async def admin_onlyoffice_forcesave(
    template_id: int,
    body: OnlyOfficeForcesaveBody | None = Body(default=None),
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> dict[str, Any]:
    return await onlyoffice_helper.onlyoffice_forcesave(
        template_id=template_id,
        document_key=(body.document_key if body else None),
    )


@router.get("/admin/templates/{template_id}", response_model=TemplateDetailResponse)
async def admin_get_template_detail(
    template_id: int,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> TemplateDetailResponse:
    return await form_flow_helper.admin_get_template_detail(template_id)


@router.patch("/admin/templates/{template_id}/field-types", response_model=TemplateDetailResponse)
async def admin_patch_template_field_types(
    template_id: int,
    body: PatchFieldTypesBody,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> TemplateDetailResponse:
    updates = []
    for f in body.fields:
        u: dict = {"key": f.key, "input_type": f.input_type}
        if f.radio_group is not None:
            u["radio_group"] = f.radio_group
        if f.radio_option is not None:
            u["radio_option"] = f.radio_option
        if f.checkbox_group is not None:
            u["checkbox_group"] = f.checkbox_group
        if f.checkbox_option is not None:
            u["checkbox_option"] = f.checkbox_option
        updates.append(u)
    return await form_flow_helper.admin_patch_template_field_types(template_id, updates=updates)


@router.put("/admin/templates/{template_id}", response_model=UploadResponse)
async def admin_update_template(
    template_id: int,
    file: UploadFile | None = File(None),
    title: str = Form(""),
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> UploadResponse:
    raw: bytes | None = None
    fn: str | None = None
    ct: str | None = None
    if file is not None and file.filename:
        chunk = await file.read()
        if chunk:
            raw = chunk
            fn = file.filename
            ct = file.content_type
    return await form_flow_helper.admin_update_template(
        template_id=template_id,
        raw=raw,
        filename=fn,
        content_type=ct,
        title=title,
    )


@router.get("/admin/templates/{template_id}/download")
async def admin_download_template(
    template_id: int,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
):
    return await form_flow_helper.admin_template_download_response(template_id)


@router.delete("/admin/templates/{template_id}")
async def admin_delete_template(
    template_id: int,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> dict[str, Any]:
    return await form_flow_helper.admin_delete_template(template_id)


@router.get("/internal/onlyoffice/document")
async def onlyoffice_download_document(token: str = Query(..., min_length=10)):
    return await onlyoffice_helper.onlyoffice_serve_document(token)


@router.get("/internal/onlyoffice/submission-filled")
async def onlyoffice_submission_filled_document(token: str = Query(..., min_length=10)):
    return await onlyoffice_helper.onlyoffice_serve_submission_filled_document(token)


@router.post("/internal/onlyoffice/callback")
async def onlyoffice_callback(
    request: Request,
    authorization: str | None = Header(default=None),
):
    raw = await request.body()
    text = raw.decode("utf-8", errors="replace").strip() if raw else ""
    body: dict[str, Any] | str
    if not text:
        body = {}
    elif text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            body = {}
        else:
            if isinstance(parsed, dict):
                body = parsed
            elif isinstance(parsed, str) and len(parsed.split(".")) >= 3:
                body = parsed
            else:
                body = {}
    elif len(text.split(".")) >= 3:
        body = text
    else:
        body = {}

    result = await onlyoffice_helper.onlyoffice_process_callback(authorization=authorization, body=body)
    return JSONResponse(content=result)


@router.get("/templates", response_model=list[TemplateListItem])
async def list_templates(user: dict = Depends(get_current_user)) -> list[TemplateListItem]:
    return await form_flow_helper.list_templates_for_fill_role(user)


@router.get("/templates/{template_id}/onlyoffice/bootstrap", response_model=OnlyOfficeBootstrapResponse)
async def user_onlyoffice_bootstrap(
    template_id: int,
    mode: str = Query("view", pattern="^(edit|view)$"),
    v: int = Query(0, ge=0, le=2_000_000_000),
    user: dict = Depends(get_current_user),
) -> OnlyOfficeBootstrapResponse:
    data = await onlyoffice_helper.onlyoffice_bootstrap(
        template_id=template_id, user=user, mode=mode, admin_route=False, view_cache_bust=v
    )
    return OnlyOfficeBootstrapResponse(**data)


@router.get("/templates/{template_id}/preview")
async def preview_template_file(
    template_id: int,
    user: dict = Depends(get_current_user),
):
    return await form_flow_helper.template_preview_response(template_id, user)


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: int,
    user: dict = Depends(get_current_user),
) -> TemplateDetailResponse:
    return await form_flow_helper.get_template_detail(template_id, user)


@router.post("/templates/{template_id}/submit", response_model=SubmitResponse)
async def submit_filled_form(
    template_id: int,
    body: SubmitBody,
    user: dict = Depends(get_current_user),
) -> SubmitResponse:
    return await form_flow_helper.submit_template_answers(template_id, user, body)


@router.get("/submissions/{submission_id}/download")
async def download_submission(
    submission_id: int,
    user: dict = Depends(get_current_user),
):
    return await form_flow_helper.submission_download_response(submission_id, user)


@router.get("/submissions", response_model=list[dict[str, Any]])
async def list_my_submissions(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    return await form_flow_helper.list_submissions_for_user(user)
