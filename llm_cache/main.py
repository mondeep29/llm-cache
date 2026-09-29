import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI

from llm_cache.api import router, set_ollama
from llm_cache.config import settings
from llm_cache.db import close_pool, create_pool
from llm_cache.logging_setup import configure_logging
from llm_cache.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await create_pool()
    client = OllamaClient()
    await client.start()
    set_ollama(client)
    logger.info(
        "app started chat_model=%s embed_model=%s threshold=%.2f",
        settings.ollama_chat_model,
        settings.ollama_embed_model,
        settings.similarity_threshold,
    )
    try:
        yield
    finally:
        await client.close()
        await close_pool()


app = FastAPI(title="LLM Semantic Cache POC", lifespan=lifespan)
app.include_router(router)


def run() -> None:
    uvicorn.run("llm_cache.main:app", host="0.0.0.0", port=8000, reload=False)
