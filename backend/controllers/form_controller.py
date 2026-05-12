from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile

from helpers.auth_helper import get_current_user, require_roles
from helpers import form_flow_helper
from models.user import User
from schemas.form_schemas import (
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


@router.get("/templates", response_model=list[TemplateListItem])
async def list_templates(user: dict = Depends(get_current_user)) -> list[TemplateListItem]:
    return await form_flow_helper.list_templates_for_fill_role(user)


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
