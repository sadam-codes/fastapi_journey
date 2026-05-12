import io
from typing import Any

from fastapi import HTTPException, status
from PIL import Image, ImageDraw, ImageFont


def _replacement_pairs(schema: list[dict[str, Any]], answers: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in schema:
        key = row["key"]
        val = str(answers.get(key, "") if answers.get(key) is not None else "")
        for ph in row.get("placeholders", []):
            pairs.append((ph, val))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def fill_docx(blob: bytes, schema: list[dict[str, Any]], answers: dict[str, Any]) -> bytes:
    try:
        from docx import Document
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DOCX support is not available.",
        ) from exc

    doc = Document(io.BytesIO(blob))
    repl = _replacement_pairs(schema, answers)

    def apply_paragraph(p) -> None:
        text = "".join(r.text for r in p.runs)
        for ph, val in repl:
            text = text.replace(ph, val)
        if p.runs:
            p.runs[0].text = text
            for r in p.runs[1:]:
                r.text = ""

    for p in doc.paragraphs:
        apply_paragraph(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    apply_paragraph(p)

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
    repl = _replacement_pairs(schema, answers)

    for page in doc:
        for ph, val in repl:
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
    lines = [f"{row['label']}: {answers.get(row['key'], '')}" for row in schema]
    text_block = "\n".join(lines) if lines else "(no fields)"
    line_h = 18
    extra = min(520, max(80, len(lines) * line_h + 24))
    new_img = Image.new("RGB", (w, h + extra), (252, 252, 254))
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((14, h + 10), text_block, fill=(30, 27, 45), font=font, spacing=4)
    buf = io.BytesIO()
    new_img.save(buf, format="PNG")
    return buf.getvalue()
