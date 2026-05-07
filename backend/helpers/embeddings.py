import os

from dotenv import load_dotenv

from helpers.openai_client import async_openai_client

load_dotenv()

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = async_openai_client()
    resp = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    data = sorted(resp.data, key=lambda d: d.index)
    return [list(item.embedding) for item in data]


async def embed_query(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0]
