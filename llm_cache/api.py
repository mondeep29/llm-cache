import logging
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from llm_cache.cache.postgres import PostgresCacheBackend
from llm_cache.cache.stats import stats
from llm_cache.config import settings
from llm_cache.db import get_pool
from llm_cache.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

router = APIRouter()
ollama: OllamaClient | None = None


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    skip_cache: bool = False


class ChatResponse(BaseModel):
    response: str
    cache_tier: Literal["exact", "semantic", "miss"]
    latency_ms: float
    similarity: float | None = None
    model: str


class HealthResponse(BaseModel):
    status: str
    chat_model: str
    embed_model: str


def set_ollama(client: OllamaClient) -> None:
    global ollama
    ollama = client


def _client() -> OllamaClient:
    if ollama is None:
        raise RuntimeError("Ollama client is not initialized")
    return ollama


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        chat_model=settings.ollama_chat_model,
        embed_model=settings.ollama_embed_model,
    )


@router.get("/cache/stats")
async def cache_stats() -> dict[str, int]:
    return stats.as_dict()


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    cache = PostgresCacheBackend(get_pool())
    client = _client()

    if not body.skip_cache:
        exact = await cache.get(body.prompt)
        if exact is not None:
            stats.record("exact")
            return _chat_response(exact.response_text, "exact", started, exact.similarity, exact.model_used)

        embedding = await client.embed(body.prompt)
        semantic = await cache.get_semantic(embedding)
        if semantic is not None:
            stats.record("semantic")
            return _chat_response(
                semantic.response_text,
                "semantic",
                started,
                semantic.similarity,
                semantic.model_used,
            )
    else:
        embedding = await client.embed(body.prompt)

    response_text = await client.generate(body.prompt)
    await cache.set(body.prompt, response_text, embedding, client.chat_model)
    stats.record(None)
    logger.info("cache miss stored model=%s", client.chat_model)
    return _chat_response(response_text, "miss", started, None, client.chat_model)


def _chat_response(
    text: str,
    tier: Literal["exact", "semantic", "miss"],
    started: float,
    similarity: float | None,
    model: str,
) -> ChatResponse:
    latency_ms = (time.perf_counter() - started) * 1000
    logger.info("chat served tier=%s latency_ms=%.1f model=%s", tier, latency_ms, model)
    return ChatResponse(
        response=text,
        cache_tier=tier,
        latency_ms=round(latency_ms, 2),
        similarity=None if similarity is None else round(similarity, 4),
        model=model,
    )
