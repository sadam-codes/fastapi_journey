"""ONLYOFFICE Document Server integration (editor + viewer + callback save)."""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from urllib.parse import quote

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from helpers.auth_helper import JWT_ALGORITHM, JWT_SECRET
from helpers.form_field_detect import detect_dynamic_fields
from helpers.form_text_extract import extract_plain_text_from_upload
from models.form_flow import FormTemplate
from models.user import User

load_dotenv()

ONLYOFFICE_DOCUMENT_SERVER_URL = (os.getenv("ONLYOFFICE_DOCUMENT_SERVER_URL") or "").strip().rstrip("/")
ONLYOFFICE_JWT_SECRET = (os.getenv("ONLYOFFICE_JWT_SECRET") or "").strip()
PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or "http://127.0.0.1:8000").strip().rstrip("/")
ONLYOFFICE_ENABLE_JWT = (os.getenv("ONLYOFFICE_ENABLE_JWT") or "false").lower() in ("1", "true", "yes")

MAX_UPLOAD_BYTES = int(os.getenv("FORM_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))


def _jwt_str(token: Any) -> str:
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return str(token)


def onlyoffice_enabled() -> bool:
    return bool(ONLYOFFICE_DOCUMENT_SERVER_URL)


def _blob_fingerprint(raw: bytes) -> str:
    return hashlib.md5(raw).hexdigest()[:20]


def _document_key(template_id: int, raw: bytes) -> str:
    key = f"tmpl-{template_id}-{_blob_fingerprint(raw)}"
    return key[:120]


def _sign_editor_payload(payload: dict[str, Any]) -> str | None:
    if not ONLYOFFICE_ENABLE_JWT or not ONLYOFFICE_JWT_SECRET:
        return None
    return _jwt_str(jwt.encode(payload, ONLYOFFICE_JWT_SECRET, algorithm=JWT_ALGORITHM))


def _create_download_jwt(*, template_id: int, user: dict) -> str:
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is required for OnlyOffice document URLs.",
        )
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    return _jwt_str(
        jwt.encode(
        {
            "scope": "onlyoffice_dl",
            "tid": template_id,
            "sub": str(user.get("sub", "")),
            "role": str(user.get("role", "")),
            "exp": exp,
        },
        str(JWT_SECRET),
        algorithm=JWT_ALGORITHM,
        )
    )


def _verify_download_jwt(token: str) -> dict[str, Any]:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured.")
    try:
        payload = jwt.decode(token, str(JWT_SECRET), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Document link expired. Reload the editor.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid document link.",
        ) from exc
    if payload.get("scope") != "onlyoffice_dl":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid document scope.")
    return payload


def _parse_template_id_from_oo_key(key: str | None) -> int | None:
    if not key:
        return None
    m = re.match(r"^tmpl-(\d+)-", key)
    if not m:
        return None
    return int(m.group(1))


async def onlyoffice_bootstrap(
    *,
    template_id: int,
    user: dict,
    mode: str,
    admin_route: bool,
) -> dict[str, Any]:
    if not onlyoffice_enabled():
        return {
            "available": False,
            "message": (
                "Set ONLYOFFICE_DOCUMENT_SERVER_URL to your Document Server base URL (e.g. http://localhost:8080). "
                "Set PUBLIC_APP_URL to a URL the Document Server can reach to download files and post callbacks "
                "(e.g. http://host.docker.internal:8000 when Document Server runs in Docker)."
            ),
            "sdkUrl": None,
            "config": None,
            "token": None,
        }

    role = user.get("role")
    if admin_route and role != User.ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")
    if not admin_route and role not in (User.ROLE_ADMIN, User.ROLE_USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")

    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")

    fn = (t.original_filename or "").lower()
    if not fn.endswith(".docx"):
        return {
            "available": False,
            "message": "OnlyOffice is used for Word (.docx) templates only. PDF and images use the built-in preview.",
            "sdkUrl": None,
            "config": None,
            "token": None,
        }

    raw = bytes(t.file_blob)
    doc_key = _document_key(t.id, raw)
    dl_jwt = _create_download_jwt(template_id=t.id, user=user)
    # JWT query values must be percent-encoded (+ and / break many HTTP clients if raw).
    document_url = (
        f"{PUBLIC_APP_URL}/forms/internal/onlyoffice/document?token={quote(dl_jwt, safe='')}"
    )
    callback_url = f"{PUBLIC_APP_URL}/forms/internal/onlyoffice/callback"

    if mode == "edit":
        editor_cfg: dict[str, Any] = {
            "mode": "edit",
            "lang": "en-US",
            "callbackUrl": callback_url,
            "user": {
                "id": str(user.get("sub", "0")),
                "name": str(user.get("email", "User")),
            },
            "customization": {
                "forcesave": True,
                "autosave": True,
                "compactToolbar": False,
                "hideRightMenu": False,
            },
        }
    else:
        editor_cfg = {
            "mode": "view",
            "lang": "en-US",
            "user": {
                "id": str(user.get("sub", "0")),
                "name": str(user.get("email", "User")),
            },
            "customization": {
                "toolbarNoTabs": False,
            },
        }

    payload: dict[str, Any] = {
        "documentType": "word",
        "document": {
            "fileType": "docx",
            "key": doc_key,
            "title": (t.title or "Document")[:200],
            "url": document_url,
            "permissions": {
                "edit": mode == "edit",
                "print": True,
                "download": True,
                "review": True,
            },
        },
        "editorConfig": editor_cfg,
        "height": "100%",
        "width": "100%",
        "type": "desktop",
    }

    token = _sign_editor_payload(payload)
    return {
        "available": True,
        "message": None,
        "sdkUrl": f"{ONLYOFFICE_DOCUMENT_SERVER_URL}/web-apps/apps/api/documents/api.js",
        "config": payload,
        "token": token,
    }


async def onlyoffice_serve_document(token: str) -> StreamingResponse:
    payload = _verify_download_jwt(token)
    tid = int(payload["tid"])
    t = await FormTemplate.get_or_none(id=tid)
    if not t:
        raise HTTPException(status_code=404, detail="Form template not found.")

    raw = bytes(t.file_blob)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")

    guessed = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    safe = (t.original_filename or "document.docx").replace("\r", " ").replace("\n", " ").replace('"', "'")[:200]

    return StreamingResponse(
        BytesIO(raw),
        media_type=guessed,
        headers={
            "Content-Disposition": f'inline; filename="{safe}"',
            "Cache-Control": "private, no-store",
        },
    )


async def onlyoffice_process_callback(
    *,
    authorization: str | None,
    body: dict[str, Any],
) -> dict[str, Any]:
    data: dict[str, Any] = dict(body or {})
    if ONLYOFFICE_ENABLE_JWT and ONLYOFFICE_JWT_SECRET:
        tok: str | None = None
        if authorization and authorization.lower().startswith("bearer "):
            tok = authorization.split(" ", 1)[1].strip()
        elif isinstance(body.get("token"), str):
            tok = body["token"]
        if not tok:
            return {"error": 1}
        try:
            data = jwt.decode(tok, ONLYOFFICE_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError:
            return {"error": 1}

    status_code = data.get("status")
    key = data.get("key")
    tid = _parse_template_id_from_oo_key(key)
    if tid is None:
        return {"error": 0}

    if status_code == 3:
        return {"error": 1}

    if status_code in (2, 6) and data.get("url"):
        url = str(data["url"])
        try:
            async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
                r = await client.get(url)
        except httpx.RequestError:
            return {"error": 1}
        if r.status_code != 200 or not r.content:
            return {"error": 1}

        new_raw = r.content
        if len(new_raw) > MAX_UPLOAD_BYTES:
            return {"error": 1}

        t = await FormTemplate.get_or_none(id=tid)
        if not t:
            return {"error": 1}

        text = extract_plain_text_from_upload(filename=t.original_filename or "x.docx", raw=new_raw)
        if not text.strip():
            return {"error": 1}

        schema = detect_dynamic_fields(text)
        t.file_blob = new_raw
        t.extracted_text = text[:500_000]
        t.fields_schema = schema
        await t.save()

    return {"error": 0}
