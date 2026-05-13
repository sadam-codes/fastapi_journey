from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TemplateListItem(BaseModel):
    id: int
    title: str
    original_filename: str
    field_count: int
    created_at: datetime


class TemplateDetailResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    fields_schema: list[dict[str, Any]]
    created_at: datetime


class UploadResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    fields_schema: list[dict[str, Any]]
    char_count: int
    message: str


class FieldTypeUpdateItem(BaseModel):
    key: str = Field(..., min_length=1, max_length=256)
    input_type: str = Field(..., min_length=1, max_length=32)


class PatchFieldTypesBody(BaseModel):
    fields: list[FieldTypeUpdateItem] = Field(default_factory=list)


class OnlyOfficeBootstrapResponse(BaseModel):
    """Client loads sdkUrl script, then new DocsAPI.DocEditor(divId, { ...config, token })."""

    available: bool
    message: str | None = None
    sdkUrl: str | None = None
    config: dict[str, Any] | None = None
    token: str | None = None


class SubmitBody(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class SubmitResponse(BaseModel):
    submission_id: int
    filled_filename: str
    message: str


class AdminSubmissionListItem(BaseModel):
    id: int
    template_id: int
    template_title: str
    user_id: int
    user_email: str
    user_name: str
    filled_filename: str | None
    has_filled_file: bool
    created_at: datetime


class AdminSubmissionDetailResponse(BaseModel):
    id: int
    template_id: int
    template_title: str
    template_original_filename: str
    fields_schema: list[dict[str, Any]]
    user_id: int
    user_email: str
    user_name: str
    answers: dict[str, str]
    filled_filename: str | None
    has_filled_file: bool
    created_at: datetime
