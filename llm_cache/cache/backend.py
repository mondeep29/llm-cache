from abc import ABC, abstractmethod

from llm_cache.cache import CacheEntry


class CacheBackend(ABC):
    @abstractmethod
    async def get(self, prompt: str) -> CacheEntry | None:
        """Exact-match lookup on the normalized prompt hash."""

    @abstractmethod
    async def get_semantic(self, embedding: list[float]) -> CacheEntry | None:
        """Nearest-neighbor lookup gated by the similarity threshold."""

    @abstractmethod
    async def set(
        self,
        prompt: str,
        response: str,
        embedding: list[float],
        model_used: str,
    ) -> None:
        """Store a prompt/response pair with its embedding."""
