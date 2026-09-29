import logging
from datetime import UTC, datetime, timedelta

import asyncpg

from llm_cache.cache import CacheEntry
from llm_cache.cache.backend import CacheBackend
from llm_cache.config import settings
from llm_cache.prompts import prompt_hash, to_pgvector

logger = logging.getLogger(__name__)


class PostgresCacheBackend(CacheBackend):
    def __init__(
        self,
        pool: asyncpg.Pool,
        similarity_threshold: float | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        self.pool = pool
        self.similarity_threshold = (
            settings.similarity_threshold if similarity_threshold is None else similarity_threshold
        )
        self.ttl_seconds = settings.cache_ttl_seconds if ttl_seconds is None else ttl_seconds

    async def get(self, prompt: str) -> CacheEntry | None:
        hashed = prompt_hash(prompt)
        exact = await self._get_by_hash(hashed)
        if exact is not None:
            await self._bump_hit_count(exact.id)
            logger.info("cache exact-hit id=%s", exact.id)
            return exact

        return None

    async def get_semantic(self, embedding: list[float]) -> CacheEntry | None:
        nearest = await self._nearest(embedding)
        if nearest is None or nearest.similarity is None:
            return None
        if nearest.similarity < self.similarity_threshold:
            logger.info(
                "cache semantic-below-threshold similarity=%.4f threshold=%.4f",
                nearest.similarity,
                self.similarity_threshold,
            )
            return None
        await self._bump_hit_count(nearest.id)
        logger.info(
            "cache semantic-hit id=%s similarity=%.4f",
            nearest.id,
            nearest.similarity,
        )
        return nearest

    async def set(
        self,
        prompt: str,
        response: str,
        embedding: list[float],
        model_used: str,
    ) -> None:
        hashed = prompt_hash(prompt)
        expires_at = None
        if self.ttl_seconds:
            expires_at = datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)
        await self.pool.execute(
            """
            INSERT INTO cache_entries (
                prompt_hash, prompt_text, embedding, response_text, model_used, expires_at
            )
            VALUES ($1, $2, $3::vector, $4, $5, $6)
            ON CONFLICT (prompt_hash) DO UPDATE SET
                prompt_text = EXCLUDED.prompt_text,
                embedding = EXCLUDED.embedding,
                response_text = EXCLUDED.response_text,
                model_used = EXCLUDED.model_used,
                expires_at = EXCLUDED.expires_at,
                created_at = now()
            """,
            hashed,
            prompt,
            to_pgvector(embedding),
            response,
            model_used,
            expires_at,
        )

    async def _get_by_hash(self, hashed: str) -> CacheEntry | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, prompt_hash, prompt_text, response_text, model_used,
                   created_at, expires_at, hit_count
            FROM cache_entries
            WHERE prompt_hash = $1
              AND (expires_at IS NULL OR expires_at > now())
            """,
            hashed,
        )
        if row is None:
            return None
        return _row_to_entry(row, similarity=1.0, tier="exact")

    async def _nearest(self, embedding: list[float]) -> CacheEntry | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, prompt_hash, prompt_text, response_text, model_used,
                   created_at, expires_at, hit_count,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM cache_entries
            WHERE embedding IS NOT NULL
              AND (expires_at IS NULL OR expires_at > now())
            ORDER BY embedding <=> $1::vector
            LIMIT 1
            """,
            to_pgvector(embedding),
        )
        if row is None:
            return None
        return _row_to_entry(row, similarity=float(row["similarity"]), tier="semantic")

    async def _bump_hit_count(self, entry_id: int) -> None:
        await self.pool.execute(
            "UPDATE cache_entries SET hit_count = hit_count + 1 WHERE id = $1",
            entry_id,
        )


def _row_to_entry(row: asyncpg.Record, similarity: float, tier: str) -> CacheEntry:
    return CacheEntry(
        id=row["id"],
        prompt_hash=row["prompt_hash"],
        prompt_text=row["prompt_text"],
        response_text=row["response_text"],
        model_used=row["model_used"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        hit_count=row["hit_count"],
        similarity=similarity,
        tier=tier,  # type: ignore[arg-type]
    )
