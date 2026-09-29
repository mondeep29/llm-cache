# LinkedIn

Two versions below. The feed post is for the timeline. The article is the long-form post (LinkedIn → Write article). Both are formatted as plain text without Markdown tables, since LinkedIn's editor does not render tables.

Replace `[repo link]` before publishing.

---

## Feed post

Semantic caching for LLMs usually gets pitched on latency. I wanted the other number too: how often does it hand back the answer to a different question?

So I built a small local version on my laptop with Ollama, Postgres + pgvector and FastAPI. Nothing goes to a cloud API.

The speedup is real:
- Exact repeat of a prompt: ~22 ms
- Semantic hit (the embedding call is most of the cost): ~165 ms
- Generating with qwen3:1.7b: ~5.8 s, about 35x slower than a semantic hit
- Generating with qwen3.5:9b: ~36 s

Accuracy is where it gets harder.

I hand-labeled 88 prompt pairs: 40 paraphrases that should hit the cache, 40 near-misses that shouldn't, and 8 unrelated ones. Embeddings from nomic-embed-text.

At a cosine threshold of 0.92:
- Precision 0.83, recall 0.25
- Only 10 of the 40 paraphrases hit. The other 30 went to the model anyway.
- 2 different questions still got through.

Those two:
"Weekend trip from Boston under $200" vs "under $2000": 0.95. A 10x budget change, and the embedding barely moved.
"Unit test for a function that adds two numbers" vs "multiplies two numbers": 0.95. Serve the cached one and the test checks the wrong operation.

The result that surprised me most: "Explain overfitting" vs "Explain underfitting" scored 0.90. "What does it mean when a model overfits?", which is the actual paraphrase, scored 0.79. Enable vs disable 2FA scored 0.89. "Steps to turn on 2FA" scored 0.63. The wrong question was often closer than the right one, and no threshold fixes that.

Drop to 0.85 and recall goes to 0.68, but about 1 in 3 hits is wrong. Raise it to 0.97 and you get one hit in the whole set.

Where I've landed: exact-match caching is an easy yes for retries, eval loops and duplicate requests. Semantic caching on similarity alone is not something I'd trust unless a wrong answer is cheap, or there's a second check on the part that actually changes the answer (numbers, entities, verbs). I haven't built that check yet.

Small dataset, one machine, so treat the numbers as directional. Write-up in the article, code here: [repo link]

#SoftwareEngineering #LLM #MachineLearning #PostgreSQL

---

## Article

**Title:** A local semantic cache for LLM calls: 35x faster, and wrong in predictable ways

Most write-ups on semantic caching for LLMs show the same diagram: embed the prompt, find the nearest cached prompt, and if it's close enough, return that answer and skip the model.

The latency win is easy to believe. I wanted to know how often "close enough" is actually the same question, so I built a small version on my laptop and measured both.

### The setup

Everything runs locally:
- Ollama for the models
- Postgres with pgvector for the cache
- FastAPI with a single /chat endpoint
- Embeddings: nomic-embed-text (768 dimensions)
- Chat models: qwen3:1.7b by default, qwen3.5:9b for a heavier comparison

Each request goes through three steps:
1. Exact match: lowercase the prompt, collapse whitespace, SHA-256 it, look up the hash.
2. Semantic match: embed the prompt, find the nearest cached vector by cosine similarity, and return that answer if it clears the threshold.
3. Miss: generate with Ollama, then store the prompt, hash, embedding and response.

### Latency

- Exact match: ~22 ms, end to end through /chat. Same string, so there's no risk of answering the wrong question.
- Semantic hit: ~165 ms. That's the embedding call, which is most of the cost. I didn't time the pgvector lookup separately, and on a table this small it's minor.
- Generating with qwen3:1.7b: ~5.8 s. About 35x slower than a semantic hit.
- Generating with qwen3.5:9b: ~36 s. Each avoided call saves over half a minute. Embedding was slower in that run (~1.6 s), probably because the 9B model was sharing the same machine, but generation still dominated.

How I measured: one prompt, models warmed up first, averaged over two runs. Numbers moved noticeably between runs (an earlier run had 3.8 s for the 1.7B model), so treat them as ballpark. The ratio is the part that holds up.

On speed alone, the cache does what it says. Accuracy is the harder question.

### Accuracy

I wrote and labeled 88 prompt pairs by hand:
- 40 paraphrases that should hit, like "How do I reset my password?" / "I forgot my password, how can I reset it?"
- 40 near-misses that shouldn't, like "return policy for electronics" / "return policy for groceries"
- 8 unrelated pairs

For each pair I embedded both prompts, computed cosine similarity, and checked it against a range of thresholds. "Hit rate" below is the share of all 88 pairs that would have been served from cache.

- 0.85: precision 0.66, recall 0.68, hit rate 47%
- 0.90: precision 0.80, recall 0.40, hit rate 23%
- 0.92 (default): precision 0.83, recall 0.25, hit rate 14%
- 0.95: precision 0.67, recall 0.05, hit rate 3%
- 0.97: precision 1.00, recall 0.03, hit rate 1%

The dip at 0.95 is small numbers: 2 correct hits and 1 wrong one. With 88 pairs, one pair changes precision a lot at the high end.

At 0.92:
- 10 of 40 paraphrases would have been served from cache.
- 30 fell below the line and would have gone to the model.
- 2 pairs asking different questions cleared it and would have gotten the wrong answer.

At 0.85 you catch 27 of 40 paraphrases but also let in 14 wrong matches, so about 1 in 3 hits answers a different question. At 0.97 exactly one paraphrase hits. 0.90 is the most balanced point on this set. 0.92 is the cautious one.

What surprised me most was that for a lot of prompts, the wrong question scored higher than the right one:
- "Explain overfitting in machine learning." vs "Explain underfitting...": 0.90. The real paraphrase, "What does it mean when a model overfits?": 0.79.
- "How do I enable two-factor authentication?" vs "...disable...": 0.89. "Steps to turn on 2FA on my account.": 0.63.
- The unit test prompt vs the "multiplies" version: 0.95. "Show a pytest example testing an add function.": 0.65.
- Flat bicycle tire vs flat car tire: 0.90. "Walk me through replacing a punctured bike tire.": 0.77.

No threshold can separate those. Whatever you set it to, you either accept the wrong one or reject the right one. In practice the semantic tier only caught paraphrases that were already worded almost the same.

One caveat: this compares each pair on its own. A real cache searches across every stored entry, so a query has more chances to land on the wrong neighbour. If anything, I'd expect the false positive rate to be worse in production, not better.

### Where it breaks

The five near-misses with the highest scores. The first two are real false positives at 0.92. The rest sit just below it and would get through if you lowered the threshold to catch more paraphrases.

1. 0.95: "Recommend a weekend trip from Boston under $200." vs "...under $2000." The budget is the whole question, and the embedding barely noticed a 10x change.
2. 0.95: "Write a unit test for a Python function that adds two numbers." vs "...multiplies two numbers." One verb. The cached test would check the wrong operation.
3. 0.91: "How can I reduce blue light from my monitor at night?" vs "...reduce brightness..." Same sentence, different setting.
4. 0.90: "Explain overfitting in machine learning." vs "Explain underfitting..." Related terms, opposite diagnosis.
5. 0.90: "How do I change a flat bicycle tire?" vs "...a flat car tire?" Same template, different tools and safety steps.

Every one of these follows the same pattern. The sentence is identical except for one word, and that word decides the answer: a number, a verb, an entity, or on/off. The embedding weights all the shared words and mostly ignores the one that changed.

### Would I use it?

Exact-match caching, yes. It's cheap, it can't answer the wrong question, and it pays off for retries, batch jobs and eval loops where the same prompt comes up again and again.

Semantic caching on similarity alone, only when a wrong answer is cheap and easy to spot, or the domain is narrow enough that near-misses rarely come up. An internal FAQ bot, maybe. Anything where $200 and $2000 have to be treated differently needs something more.

I didn't build that part. If I did, I'd start with:
- Pulling out numbers, entities and key verbs, and requiring them to match before accepting a semantic hit
- Combining keyword and vector search, or re-scoring the top candidates with a cross-encoder

So picking a threshold is a product decision more than a tuning knob. The latency chart looks great, but the real question is whether saving 5 seconds is worth occasionally sending someone a $2000 itinerary when they asked for $200.

Code and eval harness: [repo link]
