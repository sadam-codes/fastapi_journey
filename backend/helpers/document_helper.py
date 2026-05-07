import os

from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile, status

from helpers.chunking import chunk_text
from helpers.embeddings import embed_texts
from helpers.text_extract import assert_allowed_filename, extract_text
from models.document import Document, DocumentChunk

load_dotenv()

MAX_UPLOAD_BYTES = int(os.getenv("RAG_MAX_UPLOAD_BYTES", str(12 * 1024 * 1024)))


async def ingest_upload(*, upload: UploadFile) -> tuple[Document, int]:
    raw = await upload.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {MAX_UPLOAD_BYTES} bytes.",
        )
    filename = upload.filename or "upload.bin"
    assert_allowed_filename(filename)
    text = extract_text(filename=filename, raw=raw)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text (empty file or scanned PDF without a text layer).",
        )

    parts = chunk_text(text)
    if not parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate text chunks from this file.",
        )

    doc = await Document.create(
        original_filename=filename,
        mime_type=upload.content_type,
        char_count=len(text),
        file_blob=raw,
    )

    batch_size = 64
    for start in range(0, len(parts), batch_size):
        batch = parts[start : start + batch_size]
        vectors = await embed_texts(batch)
        for i, (piece, vec) in enumerate(zip(batch, vectors, strict=True)):
            idx = start + i
            await DocumentChunk.create(
                document=doc,
                chunk_index=idx,
                text=piece,
                embedding=vec,
            )

    return doc, len(parts)
