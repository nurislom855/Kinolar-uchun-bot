import os

import asyncpg

_pool: asyncpg.Pool | None = None


def _pool_or_raise() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Ma'lumotlar bazasi ulanmagan. init_db() ni chaqiring.")
    return _pool


async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=5,
        statement_cache_size=0,  # Supabase pooler bilan ishlashi uchun
    )
    await _pool.execute(
        """
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            title TEXT,
            file_id TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS channels (
            chat_id BIGINT PRIMARY KEY,
            title TEXT,
            invite_link TEXT
        );
        """
    )


async def add_movie(code: str, title: str | None, file_id: str) -> None:
    await _pool_or_raise().execute(
        "INSERT INTO movies (code, title, file_id) VALUES ($1, $2, $3)",
        code, title, file_id,
    )


async def get_movie(code: str) -> dict | None:
    row = await _pool_or_raise().fetchrow(
        "SELECT code, title, file_id FROM movies WHERE code = $1", code
    )
    return dict(row) if row else None


async def list_movies() -> list[dict]:
    rows = await _pool_or_raise().fetch(
        "SELECT code, title FROM movies ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


async def delete_movie(code: str) -> bool:
    status = await _pool_or_raise().execute(
        "DELETE FROM movies WHERE code = $1", code
    )
    return status.endswith("1")


async def add_channel(chat_id: int, title: str | None, invite_link: str) -> None:
    await _pool_or_raise().execute(
        """
        INSERT INTO channels (chat_id, title, invite_link) VALUES ($1, $2, $3)
        ON CONFLICT (chat_id) DO UPDATE
        SET title = EXCLUDED.title, invite_link = EXCLUDED.invite_link
        """,
        chat_id, title, invite_link,
    )


async def list_channels() -> list[dict]:
    rows = await _pool_or_raise().fetch(
        "SELECT chat_id, title, invite_link FROM channels ORDER BY chat_id"
    )
    return [dict(r) for r in rows]


async def delete_channel(chat_id: int) -> bool:
    status = await _pool_or_raise().execute(
        "DELETE FROM channels WHERE chat_id = $1", chat_id
    )
    return status.endswith("1")
