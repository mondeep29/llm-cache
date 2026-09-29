import logging
from typing import Any

import httpx

from llm_cache.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
        timeout_seconds: float | None = None,
        think: bool | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.chat_model = chat_model or settings.ollama_chat_model
        self.embed_model = embed_model or settings.ollama_embed_model
        self.timeout = timeout_seconds or settings.ollama_timeout_seconds
        self.think = settings.ollama_think if think is None else think
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OllamaClient":
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("OllamaClient is not started")
        return self._client

    async def generate(self, prompt: str, model: str | None = None) -> str:
        model_name = model or self.chat_model
        payload: dict[str, Any] = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
        }
        logger.info("ollama generate model=%s", model_name)
        response = await self._http().post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip()

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        vectors = await self.embed_many([text], model=model)
        return vectors[0]

    async def embed_many(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model_name = model or self.embed_model
        payload = {"model": model_name, "input": texts}
        response = await self._http().post("/api/embed", json=payload)
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError(f"ollama embed returned no vectors: {data!r}")
        return [[float(v) for v in row] for row in embeddings]
