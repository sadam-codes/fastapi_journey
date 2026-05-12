import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from tortoise import Tortoise

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def sanitize_db_url(url: str) -> str:
    parsed = urlparse(url)
    scheme_map = {
        "postgresql": "postgres",
        "postgresql+asyncpg": "postgres",
        "postgresql+psycopg": "postgres",
        "postgres": "postgres",
    }
    normalized_scheme = scheme_map.get(parsed.scheme.lower(), parsed.scheme.lower())
    query_items = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() != "pgbouncer"]
    query_map = {k: v for k, v in query_items}
    query_map["statement_cache_size"] = "0"
    return urlunparse(parsed._replace(scheme=normalized_scheme, query=urlencode(query_map)))


if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing in environment variables.")

db_url = sanitize_db_url(DATABASE_URL)


async def init_db() -> None:
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["models.user", "models.form_flow"]},
    )
    await Tortoise.generate_schemas()


async def is_db_connected() -> bool:
    try:
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1")
        return True
    except Exception:
        return False


async def close_db() -> None:
    await Tortoise.close_connections()
