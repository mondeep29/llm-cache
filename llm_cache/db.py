import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg

from llm_cache.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "001_init.sql"


async def apply_schema(pool: asyncpg.Pool) -> None:
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    async with pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("schema applied")


async def create_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=5)
        await apply_schema(_pool)
        logger.info("postgres pool created")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("postgres pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool is not initialized")
    return _pool


@asynccontextmanager
async def pool_lifespan() -> AsyncIterator[asyncpg.Pool]:
    pool = await create_pool()
    try:
        yield pool
    finally:
        await close_pool()
