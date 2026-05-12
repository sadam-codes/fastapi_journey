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
