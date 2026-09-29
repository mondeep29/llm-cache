CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS cache_entries (
    id BIGSERIAL PRIMARY KEY,
    prompt_hash TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    embedding VECTOR(768),
    response_text TEXT NOT NULL,
    model_used TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    hit_count INT DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_prompt_hash ON cache_entries (prompt_hash);
CREATE INDEX IF NOT EXISTS idx_embedding_hnsw ON cache_entries USING hnsw (embedding vector_cosine_ops);
