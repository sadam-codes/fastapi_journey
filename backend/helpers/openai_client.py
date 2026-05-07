import os

from dotenv import load_dotenv
from fastapi import HTTPException, status
from openai import AsyncOpenAI

load_dotenv()


def async_openai_client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured.",
        )
    return AsyncOpenAI(api_key=api_key)
