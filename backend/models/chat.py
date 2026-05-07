from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatResponse(BaseModel):
    reply: str
    model: str
    finish_reason: str | None = None


class RagChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class RagChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "messages": [
                        {"role": "user", "content": "What does the document say about travel booking?"}
                    ],
                    "document_ids": [3],
                    "top_k": 8,
                    "min_chunk_similarity": None,
                    "model": "gpt-5.2",
                    "reasoning_effort": "none",
                    "max_completion_tokens": 800,
                }
            ]
        }
    )

    messages: list[RagChatMessage] = Field(..., min_length=1)
    document_ids: list[int] | None = None
    top_k: int = Field(default=6, ge=1, le=100)
    min_chunk_similarity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="If best retrieved chunk scores below this (cosine vs query), refuse without calling the model. "
        "None uses server default from RAG_MIN_CHUNK_SIMILARITY (default 0.38).",
    )
    model: str | None = None
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] | None = None
    max_completion_tokens: int | None = Field(
        default=None,
        ge=1,
        le=128_000,
        description="Use at least a few hundred for real answers (e.g. 800). Very small values truncate the reply.",
    )

    @field_validator("document_ids")
    @classmethod
    def document_ids_must_be_positive(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if not value:
            raise ValueError(
                "document_ids cannot be an empty list. Omit document_ids to search all uploads, "
                "or pass positive ids from GET /documents / the upload response (e.g. 3)."
            )
        if any(i < 1 for i in value):
            raise ValueError("document_ids must be positive integers (e.g. 3), not 0.")
        return value


class RagChatResponse(ChatResponse):
    document_ids_searched: list[int]
    chunks_used: int
    best_chunk_similarity: float | None = None
