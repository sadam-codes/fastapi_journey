import io
from typing import Final

from fastapi import HTTPException, status
from pypdf import PdfReader

_ALLOWED_SUFFIXES: Final = {".txt", ".md", ".markdown", ".pdf"}


def assert_allowed_filename(filename: str) -> None:
    lower = filename.lower().strip()
    if not any(lower.endswith(s) for s in _ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(_ALLOWED_SUFFIXES))}",
        )


def extract_text(*, filename: str, raw: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    if lower.endswith((".txt", ".md", ".markdown")):
        return raw.decode("utf-8", errors="replace").strip()

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type.",
    )
