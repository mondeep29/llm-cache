# LLM Semantic Cache POC

Fully local semantic cache for LLM calls: **Ollama** for chat + embeddings, **PostgreSQL + pgvector** for storage. No cloud APIs.

The interesting result is not only that cache hits are faster — it is **where the cache is wrong**: near-miss prompts that look similar but mean different things.

## Architecture

```
Client → FastAPI POST /chat
             │
             ▼
   1. Exact-match (SHA-256 of normalized prompt)
             │ miss
             ▼
   2. Semantic (nomic-embed-text → pgvector cosine, threshold-gated)
             │ miss / below threshold
             ▼
   3. Ollama generate (qwen3:1.7b) → store prompt, embedding, response, TTL
```

Docker Compose runs **only Postgres**. The API runs on the host so it can reach the local Ollama daemon at `http://localhost:11434`.

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- Docker
- [Ollama](https://ollama.com/) running locally

Pull models:

```bash
ollama pull nomic-embed-text
ollama pull qwen3:1.7b
# already used for smoke tests / optional stretch:
# ollama pull qwen3:0.6b
# ollama pull qwen3.5:9b
```

## Setup

```bash
cp .env.example .env
docker compose up -d
poetry install
poetry run uvicorn llm_cache.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Chat (first call is a miss; repeat is an exact hit):

```bash
curl -s http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"prompt\": \"Explain overfitting in two sentences.\"}"
curl -s http://127.0.0.1:8000/cache/stats
```

A paraphrase of a cached prompt should come back as `cache_tier: semantic` if similarity is above `SIMILARITY_THRESHOLD` (default `0.92`).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql://llmcache:llmcache@localhost:5432/llmcache` | asyncpg DSN |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama |
| `OLLAMA_CHAT_MODEL` | `qwen3:1.7b` | Generation model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | 768-dim embeddings |
| `EMBEDDING_DIM` | `768` | Must match the embed model / `VECTOR(n)` column |
| `SIMILARITY_THRESHOLD` | `0.92` | Cosine similarity gate |
| `CACHE_TTL_SECONDS` | `86400` | Entry lifetime |
| `OLLAMA_THINK` | `false` | Disable Qwen thinking tokens |

If you switch to `all-minilm` (384-dim), change `EMBEDDING_DIM` **and** the `VECTOR(768)` column in `sql/001_init.sql`.

## Eval harness

Labeled pairs live in `eval/prompt_pairs.json` (paraphrases, near-misses, unrelated).

```bash
poetry run python eval/run_eval.py
# optional expensive-model latency comparison:
poetry run python eval/run_eval.py --expensive-model qwen3.5:9b
```

Writes `eval/output/threshold_metrics.csv`, `pair_similarities.csv`, `false_positives.md`, `summary.json`, and PNG charts.

## Eval results (this machine)

88 labeled pairs, `nomic-embed-text`, cosine similarity. Numbers below are from a local run; re-run `eval/run_eval.py` to refresh.

| Threshold | Precision | Recall | Hit-rate | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.659 | 0.675 | 0.466 | 0.667 | 27 | 14 | 13 |
| 0.90 | 0.800 | 0.400 | 0.227 | 0.533 | 16 | 4 | 24 |
| **0.92** | **0.833** | **0.250** | **0.136** | 0.385 | 10 | 2 | 30 |
| 0.95 | 0.667 | 0.050 | 0.034 | 0.093 | 2 | 1 | 38 |
| 0.97 | 1.000 | 0.025 | 0.011 | 0.049 | 1 | 0 | 39 |

Default `SIMILARITY_THRESHOLD=0.92` is conservative: high precision, weak recall. Paraphrases that rephrase rather than swap a few tokens often land around 0.79–0.90 (the overfitting pair used in the API smoke test scored **0.79** and correctly missed at 0.92). `0.90` is the better F1 operating point on this set if you want more hits and can tolerate extra near-miss FPs.

### Latency (measured)

| Path | Latency |
|---|---|
| Exact-match cache hit (`POST /chat` repeat) | **22 ms** |
| Semantic hit (embed only; `nomic-embed-text`) | **111 ms** (`qwen3:1.7b` run) / 143 ms (during `qwen3.5:9b` run) |
| Live generate `qwen3:1.7b` | **3.8 s** (~34× vs embed) |
| Live generate `qwen3.5:9b` | **22.5 s** (~158× vs embed) |

Charts: `eval/output/threshold_metrics.png`, `eval/output/latency.png`.

### Where it fails

See `eval/output/false_positives.md`. Headline cases:

1. `$200` vs `$2000` weekend trip — **0.95** (true FP at 0.92)
2. Unit test for **add** vs **multiply** — **0.95** (true FP at 0.92)
3. Reduce **blue light** vs **brightness** — 0.91
4. **Overfitting** vs **underfitting** — 0.90
5. **Bicycle** vs **car** tire — 0.90

Embeddings collapse a single swapped slot (number, verb, entity) when the rest of the sentence is identical. That is the honest failure mode of this POC.

## Project layout

- `llm_cache/` — FastAPI app, Ollama client, `CacheBackend` + Postgres implementation
- `sql/001_init.sql` — `cache_entries` + HNSW index
- `eval/` — dataset + precision/recall/latency harness
- `AGENTS.md` — agent context for later sessions
