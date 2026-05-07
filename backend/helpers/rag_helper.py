import math
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException, status
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)

from helpers.embeddings import embed_query
from helpers.openai_chat_kwargs import chat_completion_create_kwargs
from helpers.openai_client import async_openai_client
from models.chat import RagChatRequest, RagChatResponse
from models.document import DocumentChunk

load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")

RAG_REFUSAL_MESSAGE = (
    "The provided documents do not contain enough information to answer this question."
)

def _default_min_chunk_similarity() -> float:
    try:
        v = float(os.getenv("RAG_MIN_CHUNK_SIMILARITY", "0.38"))
    except ValueError:
        return 0.38
    return max(0.0, min(1.0, v))


DEFAULT_MIN_CHUNK_SIMILARITY = _default_min_chunk_similarity()

STRICT_RAG_SYSTEM_PREFIX = f"""You are a strict document-only assistant.

OUTPUT CONTRACT (highest priority — follow exactly):
- If every substantive claim in your answer cannot be traced to a specific sentence or phrase inside CONTEXT below, you must output ONLY this exact line (nothing before or after, no punctuation changes):
  {RAG_REFUSAL_MESSAGE}
- That includes questions about people, politics, history, geography, products, or any general knowledge: unless CONTEXT explicitly contains that information, you must output ONLY that exact line.
- FORBIDDEN: Wikipedia-style answers, biographies, definitions, or facts from your training data when they are not verbatim or clearly paraphrased from CONTEXT.
- FORBIDDEN: Filling gaps with plausible or common knowledge.

When CONTEXT does support an answer:
- Stay short; quote or closely paraphrase CONTEXT only.
- After each factual claim, cite the bracket label it came from (e.g. [document_id=3 chunk_index=2]).
"""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _last_user_content(messages: list[Any]) -> str:
    for m in reversed(messages):
        if getattr(m, "role", None) == "user":
            return str(m.content)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="RAG chat requires at least one user message.",
    )


def _format_context(rows: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for row in rows:
        label = f"[document_id={row['document_id']} chunk_index={row['chunk_index']}]"
        blocks.append(f"{label}\n{row['text']}")
    return "\n\n---\n\n".join(blocks)


async def rag_completion(payload: RagChatRequest) -> RagChatResponse:
    query = _last_user_content(payload.messages)

    q = DocumentChunk.all()
    if payload.document_ids:
        q = q.filter(document_id__in=payload.document_ids)

    chunks_list: list[DocumentChunk] = await q
    rows: list[dict[str, Any]] = []
    for c in chunks_list:
        doc_id = c.document_id
        if c.embedding is None:
            continue
        rows.append(
            {
                "id": c.id,
                "document_id": doc_id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "embedding": c.embedding,
            }
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No indexed chunks found. Upload supported documents first, or adjust document_ids.",
        )

    query_embedding = await embed_query(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        sim = cosine_similarity(query_embedding, row["embedding"])
        scored.append((sim, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0] if scored else 0.0
    min_sim = (
        payload.min_chunk_similarity
        if payload.min_chunk_similarity is not None
        else DEFAULT_MIN_CHUNK_SIMILARITY
    )
    top = [t[1] for t in scored[: payload.top_k]]

    searched_ids = (
        list(payload.document_ids) if payload.document_ids else sorted({r["document_id"] for r in rows})
    )

    if best_score < min_sim:
        return RagChatResponse(
            reply=RAG_REFUSAL_MESSAGE,
            model=payload.model or DEFAULT_MODEL,
            finish_reason="similarity_gate",
            document_ids_searched=searched_ids,
            chunks_used=len(top),
            best_chunk_similarity=best_score,
        )

    context_block = _format_context(top)
    system_message = (
        f"{STRICT_RAG_SYSTEM_PREFIX}\n\nCONTEXT:\n{context_block}\n\n"
        "FINAL CHECK: Before sending your reply, verify every sentence is grounded in CONTEXT. "
        f"If not, your entire reply must be exactly: {RAG_REFUSAL_MESSAGE}"
    )

    openai_messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]
    for m in payload.messages:
        openai_messages.append({"role": m.role, "content": m.content})

    model = payload.model or DEFAULT_MODEL
    kwargs = chat_completion_create_kwargs(
        model=model,
        messages=openai_messages,
        reasoning_effort=payload.reasoning_effort,
        max_completion_tokens=payload.max_completion_tokens,
        temperature=0.0,
    )

    client = async_openai_client()
    try:
        response = await client.chat.completions.create(**kwargs)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI authentication failed. Check OPENAI_API_KEY.",
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OpenAI rate limit exceeded. Try again shortly.",
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach OpenAI.",
        ) from exc
    except APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message or "OpenAI API error.",
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    choice = response.choices[0]
    content = choice.message.content
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned no text content.",
        )

    return RagChatResponse(
        reply=content,
        model=response.model,
        finish_reason=choice.finish_reason,
        document_ids_searched=searched_ids,
        chunks_used=len(top),
        best_chunk_similarity=best_score,
    )
