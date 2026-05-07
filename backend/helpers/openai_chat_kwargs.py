from __future__ import annotations

from typing import Any


def chat_completion_create_kwargs(
    *,
    model: str,
    messages: list[dict[str, Any]],
    reasoning_effort: str | None,
    max_completion_tokens: int | None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Kwargs for AsyncOpenAI.chat.completions.create.

    Older SDK builds may omit newer Chat Completions body fields (`reasoning_effort`,
    `max_completion_tokens`, etc.) from the typed `create()` signature. The HTTP API
    still accepts them, so we merge those into extra_body when set.
    """
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    extra: dict[str, Any] = {}
    if max_completion_tokens is not None:
        extra["max_completion_tokens"] = max_completion_tokens
    if reasoning_effort is not None:
        extra["reasoning_effort"] = reasoning_effort
    if temperature is not None:
        extra["temperature"] = temperature
    if extra:
        kwargs["extra_body"] = extra
    return kwargs
