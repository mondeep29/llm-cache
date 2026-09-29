# LLM Semantic Cache POC — Agent Context

Standalone portfolio/blog artifact: a **fully local semantic cache for LLM calls**. Inference via **Ollama** (already-running host daemon). Cache via **PostgreSQL + pgvector**. Goal: measured latency savings plus honest false-positive analysis. No cloud APIs, no production concerns.

## Stack

- FastAPI (async) + `asyncpg` + pgvector
- Poetry
- Ollama REST (`POST /api/generate`, `POST /api/embed`) at `http://localhost:11434`
- Docker Compose: **Postgres+pgvector only** (app runs locally so it can reach host Ollama)
- stdlib `logging`

## Models

| Model | Role |
|---|---|
| `qwen3:0.6b` | Smoke tests |
| `qwen3:1.7b` | Default demo/eval chat model |
| `qwen3.5:9b` | Optional expensive-model latency comparison |
| `nomic-embed-text` | Default embeddings (768-dim). Alternative: `all-minilm` (384-dim) — keep schema dim in sync |

Config **everything** via env vars (base URL, chat/embed models, threshold, TTL, embedding dim). Sane defaults, no hardcoded secrets or model names in call sites.

## Architecture

```
Client → POST /chat
  1. Exact-match (hash of normalized prompt)
  2. Semantic (embed → pgvector cosine, threshold-gated)
  3. Miss → Ollama generate → store (prompt, embedding, response, ttl) → return
```

Interface-first: `CacheBackend` ABC (`get` / `set`). One Postgres implementation containing both tiers.

## Data model

Single table `cache_entries`: `prompt_hash` (unique), `prompt_text`, `embedding VECTOR(768)`, `response_text`, `model_used`, `created_at`, `expires_at`, `hit_count`. HNSW index on embedding (`vector_cosine_ops`).

## Eval (primary blog deliverable)

Separate from the API. Labeled prompt pairs (`eval/prompt_pairs.json`, 50–100). Sweep thresholds (0.85, 0.90, 0.92, 0.95, 0.97). Precision / recall / hit-rate. Real latency: cache hit vs `qwen3:1.7b` (optional `qwen3.5:9b`). 3–5 concrete false positives with commentary. CSV + matplotlib charts.

## Non-goals

No auth, multi-tenancy, scaling, metrics/tracing stack, K8s/Helm, streaming, admin UI, or cloud LLM/embedding APIs.

## Endpoints

- `GET /health`
- `POST /chat` — cache-wrapped generate; log hit/miss, tier, latency
- `GET /cache/stats` — total requests, exact hits, semantic hits, misses
