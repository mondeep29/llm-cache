from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://llmcache:llmcache@localhost:5432/llmcache"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:1.7b"
    ollama_embed_model: str = "nomic-embed-text"
    embedding_dim: int = 768
    similarity_threshold: float = 0.92
    cache_ttl_seconds: int | None = 86400
    ollama_timeout_seconds: float = 180.0
    ollama_think: bool = False


settings = Settings()
