import aiosqlite

DB_PATH = "kino.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                title TEXT,
                file_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS channels (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                invite_link TEXT
            );
            """
        )
        await db.commit()


async def add_movie(code: str, title: str | None, file_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO movies (code, title, file_id) VALUES (?, ?, ?)",
            (code, title, file_id),
        )
        await db.commit()


async def get_movie(code: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT code, title, file_id FROM movies WHERE code = ?", (code,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_movies() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT code, title FROM movies ORDER BY created_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_movie(code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.commit()
        return cur.rowcount > 0


async def add_channel(chat_id: int, title: str | None, invite_link: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO channels (chat_id, title, invite_link) VALUES (?, ?, ?)",
            (chat_id, title, invite_link),
        )
        await db.commit()


async def list_channels() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT chat_id, title, invite_link FROM channels ORDER BY rowid"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_channel(chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
        await db.commit()
        return cur.rowcount > 0
