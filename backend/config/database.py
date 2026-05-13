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

# Used by Aerich: `aerich init -t config.database.TORTOISE_ORM` (run from the `backend` directory).
TORTOISE_ORM = {
    "connections": {"default": db_url},
    "apps": {
        "models": {
            "models": ["models.user", "models.form_flow"],
            "default_connection": "default",
        },
    },
}


async def _ensure_form_template_oo_columns() -> None:
    """Add OnlyOffice-related columns if the DB predates them (idempotent)."""
    conn = Tortoise.get_connection("default")
    raw_url = (os.getenv("DATABASE_URL") or "").lower()
    if "postgres" in raw_url or "asyncpg" in raw_url:
        for stmt in (
            "ALTER TABLE form_templates ADD COLUMN IF NOT EXISTS oo_key_nonce INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE form_templates ADD COLUMN IF NOT EXISTS file_version INTEGER NOT NULL DEFAULT 0",
        ):
            await conn.execute_query(stmt)
        return
    if "sqlite" in raw_url:
        rows, _ = await conn.execute_query("PRAGMA table_info(form_templates)")
        names = {r[1] for r in rows} if rows else set()
        if "oo_key_nonce" not in names:
            await conn.execute_query(
                "ALTER TABLE form_templates ADD COLUMN oo_key_nonce INTEGER NOT NULL DEFAULT 0"
            )
        if "file_version" not in names:
            await conn.execute_query(
                "ALTER TABLE form_templates ADD COLUMN file_version INTEGER NOT NULL DEFAULT 0"
            )


async def init_db() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    await _ensure_form_template_oo_columns()


async def is_db_connected() -> bool:
    try:
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1")
        return True
    except Exception:
        return False


async def close_db() -> None:
    await Tortoise.close_connections()
