from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from helpers import onlyoffice_helper
from helpers.auth_helper import get_current_user, require_roles
from helpers import form_flow_helper
from models.user import User
from schemas.form_schemas import (
    OnlyOfficeBootstrapResponse,
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


@router.get("/admin/onlyoffice/status")
async def admin_onlyoffice_status(
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> dict[str, Any]:
    return {"enabled": onlyoffice_helper.onlyoffice_enabled()}


@router.get("/admin/templates/{template_id}/onlyoffice/bootstrap", response_model=OnlyOfficeBootstrapResponse)
async def admin_onlyoffice_bootstrap(
    template_id: int,
    mode: str = Query("edit", pattern="^(edit|view)$"),
    user: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> OnlyOfficeBootstrapResponse:
    data = await onlyoffice_helper.onlyoffice_bootstrap(
        template_id=template_id, user=user, mode=mode, admin_route=True
    )
    return OnlyOfficeBootstrapResponse(**data)


@router.get("/admin/templates/{template_id}", response_model=TemplateDetailResponse)
async def admin_get_template_detail(
    template_id: int,
    _: dict = Depends(require_roles([User.ROLE_ADMIN])),
) -> TemplateDetailResponse:
    return await form_flow_helper.admin_get_template_detail(template_id)


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


@router.post("/internal/onlyoffice/callback")
async def onlyoffice_callback(
    request: Request,
    authorization: str | None = Header(default=None),
):
    try:
        body = await request.json()
    except Exception:
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
    user: dict = Depends(get_current_user),
) -> OnlyOfficeBootstrapResponse:
    data = await onlyoffice_helper.onlyoffice_bootstrap(
        template_id=template_id, user=user, mode=mode, admin_route=False
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
