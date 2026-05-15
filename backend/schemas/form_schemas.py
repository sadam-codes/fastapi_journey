from datetime import datetime
from typing import Any

from typing import Optional

from pydantic import BaseModel, Field


class TemplateListItem(BaseModel):
    id: int
    title: str
    original_filename: str
    field_count: int = Field(
        ...,
        description="Number of Generated-fields cards (radio Yes/No counts once, not per option).",
    )
    created_at: datetime


class TemplateDetailResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    fields_schema: list[dict[str, Any]]
    created_at: datetime
    file_version: int = 0
    oo_key_nonce: int = 0


class UploadResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    fields_schema: list[dict[str, Any]]
    char_count: int
    message: str
    file_version: int = 0
    oo_key_nonce: int = 0


class FieldTypeUpdateItem(BaseModel):
    key: str = Field(..., min_length=1, max_length=256)
    input_type: str = Field(..., min_length=1, max_length=32)
    radio_group: Optional[str] = Field(default=None, max_length=128)
    radio_option: Optional[str] = Field(default=None, max_length=256)
    checkbox_group: Optional[str] = Field(default=None, max_length=128)
    checkbox_option: Optional[str] = Field(default=None, max_length=256)


class PatchFieldTypesBody(BaseModel):
    fields: list[FieldTypeUpdateItem] = Field(default_factory=list)


class OnlyOfficeBootstrapResponse(BaseModel):
    """Client loads sdkUrl script, then new DocsAPI.DocEditor(divId, { ...config, token })."""

    available: bool
    message: str | None = None
    sdkUrl: str | None = None
    config: dict[str, Any] | None = None
    token: str | None = None
    file_version: int | None = Field(default=None, description="Template blob revision; bumps after each OnlyOffice save.")
    document_key: str | None = Field(
        default=None,
        description="Same as config.document.key; send back with forcesave so the command targets the open session.",
    )
    setup_hint: str | None = Field(
        default=None,
        description="Non-fatal connectivity note (e.g. localhost PUBLIC_APP_URL vs Docker Document Server).",
    )


class OnlyOfficeForcesaveBody(BaseModel):
    """Optional body so forcesave targets the editor session key (avoids mismatch after autosave bumps file_version)."""

    document_key: str | None = Field(default=None, max_length=130)


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
