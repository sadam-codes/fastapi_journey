import base64
import io
from typing import Any

from fastapi import HTTPException, status
from PIL import Image, ImageDraw, ImageFont


def _decode_data_url_image(val: str) -> bytes | None:
    """Return raw image bytes from a data URL, or None."""
    if not isinstance(val, str) or not val.startswith("data:image/") or ";base64," not in val:
        return None
    try:
        b64 = val.split(",", 1)[1]
        return base64.b64decode(b64, validate=True)
    except Exception:
        return None


def _image_bytes_for_embed(val: str) -> bytes | None:
    """Decode data URL and normalize to PNG for reliable embedding in DOCX/PDF."""
    raw = _decode_data_url_image(val)
    if not raw:
        return None
    try:
        im = Image.open(io.BytesIO(raw))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _signature_fallback_text(val: str) -> str:
    """Short line when no drawable signature image is available."""
    if val and val.strip() and not val.startswith("data:image/"):
        return str(val).strip()
    return "[Signed electronically]" if val and val.strip() else ""


def _placeholder_specs(schema: list[dict[str, Any]], answers: dict[str, Any]) -> list[tuple[str, str | bytes]]:
    """Each placeholder maps to replacement text (str) or PNG bytes for inline image."""
    out: list[tuple[str, str | bytes]] = []
    for row in schema:
        key = row["key"]
        val = str(answers.get(key, "") if answers.get(key) is not None else "")
        it = str(row.get("input_type") or "text").strip().lower()
        for ph in row.get("placeholders", []) or []:
            phs = str(ph)
            if not phs:
                continue
            if it == "signature":
                img = _image_bytes_for_embed(val)
                if img:
                    out.append((phs, img))
                else:
                    out.append((phs, _signature_fallback_text(val)))
            else:
                out.append((phs, val))
    out.sort(key=lambda x: -len(x[0]))
    return out


def _full_string_to_segments(full: str, specs: list[tuple[str, str | bytes]]) -> list[str | bytes]:
    """Split document text into alternating literal strings and raw PNG segments."""
    out: list[str | bytes] = []
    buf: list[str] = []
    i = 0
    n = len(full)

    def flush_buf() -> None:
        nonlocal buf
        if buf:
            out.append("".join(buf))
            buf = []

    while i < n:
        matched = False
        for ph, repl in specs:
            if ph and full.startswith(ph, i):
                flush_buf()
                if isinstance(repl, bytes):
                    out.append(repl)
                elif repl:
                    out.append(repl)
                i += len(ph)
                matched = True
                break
        if not matched:
            buf.append(full[i])
            i += 1
    flush_buf()
    return out


def _rebuild_docx_paragraph(paragraph, full: str, specs: list[tuple[str, str | bytes]]) -> None:
    try:
        from docx.oxml.ns import qn
        from docx.shared import Inches
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DOCX support is not available.",
        ) from exc

    segments = _full_string_to_segments(full, specs)
    p_el = paragraph._element
    for child in list(p_el):
        if child.tag != qn("w:pPr"):
            p_el.remove(child)
    for seg in segments:
        if isinstance(seg, bytes):
            run = paragraph.add_run()
            run.add_picture(io.BytesIO(seg), width=Inches(1.65))
        else:
            paragraph.add_run(seg)


def _iter_docx_paragraphs(doc: Any):
    for p in doc.paragraphs:
        yield p
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    yield p
    for sec in doc.sections:
        for hf in (sec.header, sec.footer):
            if hf is None:
                continue
            for p in hf.paragraphs:
                yield p
            for table in hf.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            yield p


def fill_docx(blob: bytes, schema: list[dict[str, Any]], answers: dict[str, Any]) -> bytes:
    try:
        from docx import Document
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DOCX support is not available.",
        ) from exc

    doc = Document(io.BytesIO(blob))
    specs = _placeholder_specs(schema, answers)
    for p in _iter_docx_paragraphs(doc):
        full = "".join(r.text for r in p.runs)
        if not full or not any(ph in full for ph, _ in specs):
            continue
        _rebuild_docx_paragraph(p, full, specs)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def fill_pdf(blob: bytes, schema: list[dict[str, Any]], answers: dict[str, Any]) -> bytes:
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF fill support (PyMuPDF) is not available.",
        ) from exc

    doc = fitz.open(stream=blob, filetype="pdf")
    specs = _placeholder_specs(schema, answers)
    image_jobs = [(ph, repl) for ph, repl in specs if isinstance(repl, bytes)]
    text_jobs = [(ph, repl) for ph, repl in specs if isinstance(repl, str)]

    for page in doc:
        for ph, img_bytes in image_jobs:
            while True:
                hits = page.search_for(ph)
                if not hits:
                    break
                rect = hits[0]
                page.add_redact_annot(rect)
                page.apply_redactions()
                try:
                    page.insert_image(rect, stream=img_bytes, keep_proportion=True)
                except Exception:
                    page.insert_image(rect, stream=img_bytes)

        for ph, val in text_jobs:
            while True:
                hits = page.search_for(ph)
                if not hits:
                    break
                rect = hits[0]
                try:
                    page.add_redact_annot(
                        rect,
                        text=val,
                        fontsize=10,
                        fontname="helv",
                        text_color=(0, 0, 0),
                        fill=(1, 1, 1),
                    )
                    page.apply_redactions()
                except TypeError:
                    page.add_redact_annot(rect)
                    page.apply_redactions()
                    page.insert_text(rect.tl, val, fontsize=10, fontname="helv", color=(0, 0, 0))

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


def fill_image_overlay(blob: bytes, schema: list[dict[str, Any]], answers: dict[str, Any]) -> bytes:
    img = Image.open(io.BytesIO(blob)).convert("RGB")
    w, h = img.size
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()

    row_blocks: list[tuple[str, Image.Image | None]] = []
    extra_h = 24
    for row in schema:
        key = row["key"]
        raw = str(answers.get(key, "") if answers.get(key) is not None else "")
        it = str(row.get("input_type") or "text").strip().lower()
        label = str(row.get("label") or key)
        if it == "signature":
            ib = _image_bytes_for_embed(raw)
            if ib:
                try:
                    sig = Image.open(io.BytesIO(ib)).convert("RGBA")
                    sig.thumbnail((max(120, w - 36), 100))
                    row_blocks.append((label, sig))
                    extra_h += sig.size[1] + 28
                    continue
                except Exception:
                    pass
            row_blocks.append((f"{label}: {_signature_fallback_text(raw)}", None))
            extra_h += 22
        else:
            row_blocks.append((f"{label}: {raw}", None))
            extra_h += 22

    extra = min(640, max(100, extra_h))
    new_img = Image.new("RGB", (w, h + extra), (252, 252, 254))
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    y = h + 12
    for text_line, sig_img in row_blocks:
        if sig_img is None:
            draw.text((14, y), text_line, fill=(30, 27, 45), font=font, spacing=4)
            y += 22
        else:
            draw.text((14, y), f"{text_line}", fill=(30, 27, 45), font=font, spacing=4)
            y += 20
            new_img.paste(sig_img, (14, y), sig_img)
            y += sig_img.size[1] + 10

    buf = io.BytesIO()
    new_img.save(buf, format="PNG")
    return buf.getvalue()
