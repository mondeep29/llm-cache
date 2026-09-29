from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CacheTier = Literal["exact", "semantic"]


@dataclass(frozen=True)
class CacheEntry:
    id: int
    prompt_hash: str
    prompt_text: str
    response_text: str
    model_used: str
    created_at: datetime | None
    expires_at: datetime | None
    hit_count: int
    similarity: float | None = None
    tier: CacheTier = "exact"
