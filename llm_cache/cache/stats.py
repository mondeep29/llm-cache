from dataclasses import dataclass


@dataclass
class CacheStats:
    total_requests: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0

    def record(self, tier: str | None) -> None:
        self.total_requests += 1
        if tier == "exact":
            self.exact_hits += 1
        elif tier == "semantic":
            self.semantic_hits += 1
        else:
            self.misses += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "total_requests": self.total_requests,
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "misses": self.misses,
        }


stats = CacheStats()
