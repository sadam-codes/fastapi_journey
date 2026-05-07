from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from helpers.document_helper import ingest_upload
from models.document import Document, DocumentChunk

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    id: int
    original_filename: str
    chunks_indexed: int
    char_count: int


class DocumentListItem(BaseModel):
    id: int
    original_filename: str
    char_count: int
    chunk_count: int
    created_at: datetime


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing filename.",
        )
    doc, chunk_count = await ingest_upload(upload=file)
    return DocumentUploadResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        chunks_indexed=chunk_count,
        char_count=doc.char_count,
    )


@router.get("", response_model=list[DocumentListItem])
async def list_documents() -> list[DocumentListItem]:
    rows = await Document.all().order_by("-created_at")
    out: list[DocumentListItem] = []
    for d in rows:
        chunk_count = await DocumentChunk.filter(document_id=d.id).count()
        out.append(
            DocumentListItem(
                id=d.id,
                original_filename=d.original_filename,
                char_count=d.char_count,
                chunk_count=chunk_count,
                created_at=d.created_at,
            )
        )
    return out
