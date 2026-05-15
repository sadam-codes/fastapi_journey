"""ONLYOFFICE Document Server integration (editor + viewer + callback save)."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from fastapi.responses import Response

from helpers.auth_helper import JWT_ALGORITHM, JWT_SECRET, JWT_SIGNING_KEY
from helpers.form_field_detect import (
    count_field_schema_display_groups,
    detect_dynamic_fields,
    merge_detected_with_saved_input_types,
    normalize_field_schema,
)
from helpers.form_text_extract import extract_plain_text_from_upload
from models.form_flow import FormSubmission, FormTemplate
from models.user import User

load_dotenv()

logger = logging.getLogger(__name__)

ONLYOFFICE_DOCUMENT_SERVER_URL = (os.getenv("ONLYOFFICE_DOCUMENT_SERVER_URL") or "").strip().rstrip("/")
ONLYOFFICE_JWT_SECRET = (os.getenv("ONLYOFFICE_JWT_SECRET") or "").strip()
PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or "http://127.0.0.1:8000").strip().rstrip("/")
_explicit_jwt = (os.getenv("ONLYOFFICE_ENABLE_JWT") or "").strip().lower()
if _explicit_jwt in ("0", "false", "no", "off"):
    ONLYOFFICE_ENABLE_JWT = False
elif _explicit_jwt in ("1", "true", "yes", "on"):
    ONLYOFFICE_ENABLE_JWT = True
else:
    ONLYOFFICE_ENABLE_JWT = bool(ONLYOFFICE_JWT_SECRET)
MAX_UPLOAD_BYTES = int(os.getenv("FORM_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
ONLYOFFICE_CALLBACK_POLL_SECONDS = float(os.getenv("ONLYOFFICE_CALLBACK_POLL_SECONDS", "35"))
# How often we re-read the DB while waiting for the callback after a forcesave command (smaller = snappier UI).
ONLYOFFICE_FORCESAVE_POLL_INTERVAL_S = float(os.getenv("ONLYOFFICE_FORCESAVE_POLL_INTERVAL_S", "0.05"))

_oo_command_client: httpx.AsyncClient | None = None
# Remember which Document Server command endpoint works (avoids a wasted round-trip on every save).
_oo_command_url_base: str | None = None


def _onlyoffice_setup_hint() -> str | None:
    """If Document Server runs in Docker, it cannot reach the host API at localhost/127.0.0.1."""
    p = (PUBLIC_APP_URL or "").strip().lower()
    if not p:
        return None
    if "127.0.0.1" in p or "localhost" in p:
        return (
            "PUBLIC_APP_URL uses localhost. If OnlyOffice runs in Docker, the server cannot download your "
            "document from localhost. Set PUBLIC_APP_URL to http://host.docker.internal:8000 (Windows/Mac) "
            "or your machine's LAN IP so the Document Server can reach this API."
        )
    return None


def _jwt_str(token: Any) -> str:
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return str(token)


def onlyoffice_enabled() -> bool:
    return bool(ONLYOFFICE_DOCUMENT_SERVER_URL)


def _oo_command_http() -> httpx.AsyncClient:
    """Reuse one client for Command Service calls (avoids TLS + TCP setup on every Save click)."""
    global _oo_command_client
    if _oo_command_client is None or getattr(_oo_command_client, "is_closed", False):
        _oo_command_client = httpx.AsyncClient(timeout=45.0, follow_redirects=True)
    return _oo_command_client


async def close_onlyoffice_http_clients() -> None:
    global _oo_command_client
    c = _oo_command_client
    _oo_command_client = None
    if c is not None and not getattr(c, "is_closed", False):
        await c.aclose()


def _command_service_urls() -> tuple[str, ...]:
    base = ONLYOFFICE_DOCUMENT_SERVER_URL
    primary = f"{base}/coauthoring/CommandService.ashx"
    secondary = f"{base}/command"
    global _oo_command_url_base
    if _oo_command_url_base == primary:
        return (primary, secondary)
    if _oo_command_url_base == secondary:
        return (secondary, primary)
    return (primary, secondary)


def onlyoffice_jwt_signing_enabled() -> bool:
    """True when editor bootstrap will include a JWT for the Document Server."""
    return bool(ONLYOFFICE_ENABLE_JWT and ONLYOFFICE_JWT_SECRET)


def _edit_document_key(template_id: int, nonce: int, file_version: int) -> str:
    """Bumps with ``file_version`` after each successful save so OnlyOffice reload fetches new bytes."""
    return f"tmpl-{template_id}-e{int(nonce)}-{int(file_version)}"[:120]


def _view_document_key(template_id: int, cache_bust: int) -> str:
    """New key whenever preview reload rev bumps so OnlyOffice does not reuse a cached document."""
    return f"tmpl-{template_id}-v{int(cache_bust)}"[:120]


def _sign_editor_payload(payload: dict[str, Any]) -> str | None:
    if not ONLYOFFICE_ENABLE_JWT or not ONLYOFFICE_JWT_SECRET:
        return None
    return _jwt_str(jwt.encode(payload, ONLYOFFICE_JWT_SECRET, algorithm=JWT_ALGORITHM))


def _create_download_jwt(*, template_id: int, user: dict) -> str:
    if not JWT_SECRET or JWT_SIGNING_KEY is None:
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
            JWT_SIGNING_KEY,
            algorithm=JWT_ALGORITHM,
        )
    )


def _verify_download_jwt(token: str) -> dict[str, Any]:
    if not JWT_SECRET or JWT_SIGNING_KEY is None:
        raise HTTPException(status_code=500, detail="Server misconfigured.")
    try:
        payload = jwt.decode(token, JWT_SIGNING_KEY, algorithms=[JWT_ALGORITHM])
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


OO_SUB_FILLED_SCOPE = "onlyoffice_sub_filled"


def _create_submission_filled_download_jwt(*, submission_id: int, user: dict) -> str:
    if not JWT_SECRET or JWT_SIGNING_KEY is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is required for submission document URLs.",
        )
    if user.get("role") != User.ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    return _jwt_str(
        jwt.encode(
            {
                "scope": OO_SUB_FILLED_SCOPE,
                "sid": submission_id,
                "sub": str(user.get("sub", "")),
                "role": str(user.get("role", "")),
                "exp": exp,
            },
            JWT_SIGNING_KEY,
            algorithm=JWT_ALGORITHM,
        )
    )


def _verify_submission_filled_download_jwt(token: str) -> dict[str, Any]:
    if not JWT_SECRET or JWT_SIGNING_KEY is None:
        raise HTTPException(status_code=500, detail="Server misconfigured.")
    try:
        payload = jwt.decode(token, JWT_SIGNING_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Document link expired. Reload the page.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid document link.",
        ) from exc
    if payload.get("scope") != OO_SUB_FILLED_SCOPE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid document scope.")
    return payload


def _parse_template_id_from_oo_key(key: str | None) -> int | None:
    if not key:
        return None
    m = re.match(r"^tmpl-(\d+)-", key)
    if not m:
        return None
    return int(m.group(1))


def _callback_status_int(val: Any) -> int:
    try:
        return int(val)  
    except (TypeError, ValueError):
        return -1


def _callback_document_key(data: dict[str, Any]) -> str | None:
    k = data.get("key")
    if isinstance(k, str) and k.strip():
        return k.strip()
    doc = data.get("document")
    if isinstance(doc, dict):
        k2 = doc.get("key")
        if isinstance(k2, str) and k2.strip():
            return k2.strip()
    return None


def _callback_download_url(data: dict[str, Any]) -> str | None:
    for name in ("url", "URL"):
        u = data.get(name)
        if isinstance(u, str) and u.strip():
            return u.strip()
    return None


async def onlyoffice_bootstrap(
    *,
    template_id: int,
    user: dict,
    mode: str,
    admin_route: bool,
    view_cache_bust: int = 0,
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
            "setup_hint": None,
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
            "setup_hint": None,
        }

    nonce = int(getattr(t, "oo_key_nonce", None) or 0)
    fv = int(getattr(t, "file_version", None) or 0)
    if mode == "edit":
        doc_key = _edit_document_key(t.id, nonce, fv)
    else:
        doc_key = _view_document_key(t.id, int(view_cache_bust) or 0)
    dl_jwt = _create_download_jwt(template_id=t.id, user=user)
    document_url = (
        f"{PUBLIC_APP_URL}/forms/internal/onlyoffice/document?token={quote(dl_jwt, safe='')}&fv={fv}"
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
                "copy": True,
                "modifyFilter": True,
                "fillForms": True,
            },
        },
        "editorConfig": editor_cfg,
        "height": "100%",
        "width": "100%",
        "type": "desktop",
        "events": {},
    }

    if ONLYOFFICE_ENABLE_JWT and not ONLYOFFICE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "ONLYOFFICE_ENABLE_JWT is on but ONLYOFFICE_JWT_SECRET is empty. "
                "Set ONLYOFFICE_JWT_SECRET to the same value as your Document Server JWT secret "
                "(e.g. Docker env JWT_SECRET for onlyoffice/documentserver), or set ONLYOFFICE_ENABLE_JWT=false."
            ),
        )

    token = _sign_editor_payload(payload)
    return {
        "available": True,
        "message": None,
        "sdkUrl": f"{ONLYOFFICE_DOCUMENT_SERVER_URL}/web-apps/apps/api/documents/api.js",
        "config": payload,
        "token": token,
        "file_version": fv,
        "document_key": doc_key,
        "setup_hint": _onlyoffice_setup_hint(),
    }


def _subfilled_view_key(submission_id: int, cache_bust: int) -> str:
    return f"subfil-{submission_id}-v{int(cache_bust)}"[:120]


async def onlyoffice_submission_filled_bootstrap(
    *,
    submission_id: int,
    user: dict,
    view_cache_bust: int = 0,
) -> dict[str, Any]:
    """View-only OnlyOffice config for the merged .docx stored on a submission (admin)."""
    if not onlyoffice_enabled():
        return {
            "available": False,
            "message": (
                "Set ONLYOFFICE_DOCUMENT_SERVER_URL to your Document Server base URL (e.g. http://localhost:8080). "
                "Set PUBLIC_APP_URL to a URL the Document Server can reach to download files "
                "(e.g. http://host.docker.internal:8000 when Document Server runs in Docker)."
            ),
            "sdkUrl": None,
            "config": None,
            "token": None,
            "setup_hint": None,
        }
    if user.get("role") != User.ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")

    sub = await FormSubmission.filter(id=submission_id).select_related("template").first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if not sub.filled_file_blob:
        return {
            "available": False,
            "message": "This submission has no merged file to preview.",
            "sdkUrl": None,
            "config": None,
            "token": None,
            "setup_hint": None,
        }
    fn = (sub.filled_filename or "").lower()
    if not fn.endswith(".docx"):
        return {
            "available": False,
            "message": "In-browser preview uses OnlyOffice for filled Word (.docx) only. Download the file for PDF or images.",
            "sdkUrl": None,
            "config": None,
            "token": None,
            "setup_hint": None,
        }

    tpl = sub.template
    doc_key = _subfilled_view_key(sub.id, int(view_cache_bust) or 0)
    dl_jwt = _create_submission_filled_download_jwt(submission_id=sub.id, user=user)
    document_url = f"{PUBLIC_APP_URL}/forms/internal/onlyoffice/submission-filled?token={quote(dl_jwt, safe='')}"
    title = (sub.filled_filename or (tpl.title if tpl else None) or "Filled document")[:200]

    editor_cfg: dict[str, Any] = {
        "mode": "view",
        "lang": "en-US",
        "user": {
            "id": str(user.get("sub", "0")),
            "name": str(user.get("email", "Admin")),
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
            "title": title,
            "url": document_url,
            "permissions": {
                "edit": False,
                "print": True,
                "download": True,
                "review": False,
                "copy": True,
                "modifyFilter": False,
                "fillForms": False,
            },
        },
        "editorConfig": editor_cfg,
        "height": "100%",
        "width": "100%",
        "type": "desktop",
        "events": {},
    }

    if ONLYOFFICE_ENABLE_JWT and not ONLYOFFICE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "ONLYOFFICE_ENABLE_JWT is on but ONLYOFFICE_JWT_SECRET is empty. "
                "Set ONLYOFFICE_JWT_SECRET to the same value as your Document Server JWT secret "
                "(e.g. Docker env JWT_SECRET for onlyoffice/documentserver), or set ONLYOFFICE_ENABLE_JWT=false."
            ),
        )

    token = _sign_editor_payload(payload)
    return {
        "available": True,
        "message": None,
        "sdkUrl": f"{ONLYOFFICE_DOCUMENT_SERVER_URL}/web-apps/apps/api/documents/api.js",
        "config": payload,
        "token": token,
        "file_version": None,
        "document_key": None,
        "setup_hint": _onlyoffice_setup_hint(),
    }


async def onlyoffice_forcesave(*, template_id: int, document_key: str | None = None) -> dict[str, Any]:
    """Ask Document Server to save the open editing session to callbackUrl (forcesave command)."""
    if not onlyoffice_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OnlyOffice is not configured.",
        )
    t = await FormTemplate.get_or_none(id=template_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form template not found.")
    fn = (t.original_filename or "").lower()
    if not fn.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OnlyOffice applies to .docx templates only.",
        )

    nonce = int(getattr(t, "oo_key_nonce", None) or 0)
    fv = int(getattr(t, "file_version", None) or 0)
    dk = (document_key or "").strip()[:120] if document_key else ""
    if dk:
        tid = _parse_template_id_from_oo_key(dk)
        if tid != template_id or not dk.startswith(f"tmpl-{template_id}-"):
            dk = ""
    doc_key = dk if dk else _edit_document_key(t.id, nonce, fv)
    v_before = fv
    cmd_payload: dict[str, Any] = {"c": "forcesave", "key": doc_key}
    if ONLYOFFICE_ENABLE_JWT and ONLYOFFICE_JWT_SECRET:
        body: dict[str, Any] = {
            "token": _jwt_str(
                jwt.encode(cmd_payload, ONLYOFFICE_JWT_SECRET, algorithm=JWT_ALGORITHM),
            ),
        }
    else:
        body = cmd_payload

    command_urls = _command_service_urls()
    last_detail = "Could not reach OnlyOffice command service."
    client = _oo_command_http()
    global _oo_command_url_base
    for cmd_url in command_urls:
        try:
            url = f"{cmd_url}?shardkey={quote(doc_key, safe='')}"
            r = await client.post(url, json=body)
        except httpx.RequestError as exc:
            last_detail = str(exc) or last_detail
            continue
        if r.status_code == 404:
            continue
        try:
            data = r.json() if r.content else {}
        except Exception:
            last_detail = r.text[:300] if r.text else "Invalid JSON from command service."
            continue
        err = data.get("error", -1)
        if err == 0:
            _oo_command_url_base = cmd_url
            poll_slice = max(0.02, ONLYOFFICE_FORCESAVE_POLL_INTERVAL_S)
            max_poll = max(1, int(ONLYOFFICE_CALLBACK_POLL_SECONDS / poll_slice))
            for _ in range(max_poll):
                t2 = await FormTemplate.get_or_none(id=template_id)
                if t2 and int(getattr(t2, "file_version", None) or 0) > v_before:
                    n_labels = count_field_schema_display_groups(list(t2.fields_schema or []))
                    return {
                        "success": True,
                        "unchanged": False,
                        "file_version": t2.file_version,
                        "field_count": n_labels,
                        "message": (
                            f"Saved on the server ({n_labels} label{'s' if n_labels != 1 else ''} in Generated fields). "
                            "Open Preview and tap Reload to refresh the viewer."
                        ),
                    }
                await asyncio.sleep(poll_slice)
            t3 = await FormTemplate.get_or_none(id=template_id)
            n_labels = count_field_schema_display_groups(list(t3.fields_schema or [])) if t3 else 0
            return {
                "success": True,
                "unchanged": False,
                "timed_out": True,
                "file_version": int(getattr(t3, "file_version", None) or 0) if t3 else v_before,
                "field_count": n_labels,
                "message": (
                    "OnlyOffice accepted the save, but the API did not see the storage callback in time "
                    f"({ONLYOFFICE_CALLBACK_POLL_SECONDS:.0f}s). Wait a few seconds, then Preview → Reload. "
                    "If this keeps happening: (1) run uvicorn with --host 0.0.0.0 so Docker can reach port 8000, "
                    "(2) set PUBLIC_APP_URL to a URL the document server container can open "
                    "(e.g. http://host.docker.internal:8000 on Docker Desktop), "
                    "(3) on Linux add extra_hosts host.docker.internal:host-gateway to the documentserver service, "
                    "(4) match ONLYOFFICE_JWT_SECRET with the document server's JWT_SECRET."
                ),
            }
        if err == 4:
            _oo_command_url_base = cmd_url
            t4 = await FormTemplate.get_or_none(id=template_id)
            n_labels = count_field_schema_display_groups(list(t4.fields_schema or [])) if t4 else 0
            return {
                "success": True,
                "unchanged": True,
                "file_version": int(getattr(t4, "file_version", None) or 0) if t4 else v_before,
                "field_count": n_labels,
                "message": "No new changes to save since the last version on the server.",
            }
        messages: dict[int, str] = {
            1: "No active edit session for this document — wait until the editor finishes loading, then try again.",
            2: "OnlyOffice rejected the callback URL configuration.",
            3: "OnlyOffice internal error while saving.",
            6: "Invalid command JWT — check ONLYOFFICE_JWT_SECRET matches the document server.",
        }
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=messages.get(err, f"OnlyOffice save command failed (error {err})."),
        )

    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=last_detail)


async def onlyoffice_serve_document(token: str) -> Response:
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

    return Response(
        content=raw,
        media_type=guessed,
        headers={
            "Content-Disposition": f'inline; filename="{safe}"',
            "Cache-Control": "private, no-store",
        },
    )


async def onlyoffice_serve_submission_filled_document(token: str) -> Response:
    """Serve merged submission bytes to OnlyOffice (JWT from admin bootstrap)."""
    payload = _verify_submission_filled_download_jwt(token)
    sid = int(payload["sid"])
    sub = await FormSubmission.get_or_none(id=sid)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if not sub.filled_file_blob:
        raise HTTPException(status_code=404, detail="Filled file is missing.")

    raw = bytes(sub.filled_file_blob)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")

    guessed = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    safe = (sub.filled_filename or "filled.docx").replace("\r", " ").replace("\n", " ").replace('"', "'")[:200]

    return Response(
        content=raw,
        media_type=guessed,
        headers={
            "Content-Disposition": f'inline; filename="{safe}"',
            "Cache-Control": "private, no-store",
        },
    )


def _onlyoffice_callback_fail(reason: str, *, template_id: int | None = None, detail: str | None = None) -> dict[str, Any]:
    parts = [f"onlyoffice_callback {reason}"]
    if template_id is not None:
        parts.append(f"template_id={template_id}")
    if detail:
        parts.append(detail)
    logger.warning(" ".join(parts))
    return {"error": 1}


async def onlyoffice_process_callback(
    *,
    authorization: str | None,
    body: dict[str, Any] | str | None,
) -> dict[str, Any]:
    data: dict[str, Any]
    if isinstance(body, str):
        tok_outer = body.strip()
        if not ONLYOFFICE_ENABLE_JWT or not ONLYOFFICE_JWT_SECRET:
            return _onlyoffice_callback_fail("jwt_string_body_requires_jwt_secret")
        if len(tok_outer.split(".")) < 3:
            return _onlyoffice_callback_fail("invalid_jwt_string_body")
        try:
            data = jwt.decode(tok_outer, ONLYOFFICE_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError:
            return _onlyoffice_callback_fail("jwt_decode_failed")
    else:
        raw = dict(body or {})
        # Plain JSON fields (status, url, key) often stay in the body while Authorization carries a slim JWT.
        base = {k: v for k, v in raw.items() if k != "token"}
        if ONLYOFFICE_ENABLE_JWT and ONLYOFFICE_JWT_SECRET:
            tok: str | None = None
            if authorization and authorization.lower().startswith("bearer "):
                tok = authorization.split(" ", 1)[1].strip()
            elif isinstance(raw.get("token"), str):
                tok = raw["token"]
            if not tok:
                return _onlyoffice_callback_fail("missing_jwt_token")
            try:
                decoded = jwt.decode(tok, ONLYOFFICE_JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except jwt.PyJWTError:
                return _onlyoffice_callback_fail("jwt_decode_failed")
            if isinstance(decoded, dict):
                # Signed JWT fields win on overlap; JSON body fills url/status when the header JWT is slim (7.x+).
                data = {**base, **decoded}
            else:
                data = base
        else:
            data = base

    status_int = _callback_status_int(data.get("status"))
    key = _callback_document_key(data)
    tid = _parse_template_id_from_oo_key(key)
    if tid is None:
        if key:
            logger.warning("onlyoffice_callback unparseable_key key=%r", key[:160])
        return {"error": 0}

    if status_int == 3:
        return _onlyoffice_callback_fail("status_document_saving_error", template_id=tid)

    if status_int == 7:
        return _onlyoffice_callback_fail("status_force_save_error", template_id=tid)

    url = _callback_download_url(data)
    if status_int in (2, 6) and url:
        try:
            async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
                r = await client.get(url)
        except httpx.RequestError as exc:
            return _onlyoffice_callback_fail(
                "download_request_failed", template_id=tid, detail=str(exc.__class__.__name__)
            )
        if r.status_code != 200 or not r.content:
            return _onlyoffice_callback_fail(
                "download_bad_response",
                template_id=tid,
                detail=f"http_status={r.status_code} bytes={len(r.content or b'')}",
            )

        new_raw = r.content
        if len(new_raw) > MAX_UPLOAD_BYTES:
            return _onlyoffice_callback_fail(
                "file_too_large", template_id=tid, detail=f"bytes={len(new_raw)} max={MAX_UPLOAD_BYTES}"
            )

        t = await FormTemplate.get_or_none(id=tid)
        if not t:
            return _onlyoffice_callback_fail("template_not_found", template_id=tid)

        saved_schema = list(t.fields_schema or [])
        new_ver = int(getattr(t, "file_version", None) or 0) + 1
        t.file_blob = new_raw
        t.file_version = new_ver
        # Persist bytes first so admin "Save" / forcesave polling returns without waiting
        # for full DOCX text extraction and placeholder detection.
        await t.save(update_fields=["file_blob", "file_version"])

        async def _refresh_extracted_and_schema() -> None:
            t2 = await FormTemplate.get_or_none(id=tid)
            if not t2 or int(getattr(t2, "file_version", None) or 0) != new_ver:
                return
            try:
                text = extract_plain_text_from_upload(
                    filename=t2.original_filename or "x.docx", raw=new_raw
                )
                if not text.strip():
                    prev = (t2.extracted_text or "").strip()
                    text = (prev[:500_000] if prev else " ")
                detected = detect_dynamic_fields(text)
                schema = normalize_field_schema(
                    merge_detected_with_saved_input_types(saved_schema, detected)
                )
                t2.extracted_text = text[:500_000]
                t2.fields_schema = schema
                await t2.save(update_fields=["extracted_text", "fields_schema"])
            except Exception:
                logger.exception(
                    "onlyoffice_callback saved blob but schema refresh failed template_id=%s file_version=%s",
                    tid,
                    new_ver,
                )

        asyncio.create_task(_refresh_extracted_and_schema())

        logger.info(
            "onlyoffice_callback saved template_id=%s file_version=%s status=%s",
            tid,
            new_ver,
            status_int,
        )

    return {"error": 0}
