"""Eval harness for the semantic cache (not part of the API).

Measures precision/recall/hit-rate across similarity thresholds, records
real generation latency, and writes CSV + charts.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_cache.config import settings  # noqa: E402
from llm_cache.logging_setup import configure_logging  # noqa: E402
from llm_cache.ollama_client import OllamaClient  # noqa: E402

DEFAULT_THRESHOLDS = [0.85, 0.90, 0.92, 0.95, 0.97]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


@dataclass
class PairResult:
    pair_id: str
    category: str
    should_hit: bool
    canonical: str
    query: str
    similarity: float


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def metrics_at_threshold(results: list[PairResult], threshold: float) -> dict[str, float]:
    tp = fp = tn = fn = 0
    for row in results:
        predicted = row.similarity >= threshold
        if predicted and row.should_hit:
            tp += 1
        elif predicted and not row.should_hit:
            fp += 1
        elif not predicted and row.should_hit:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    hit_rate = (tp + fp) / len(results) if results else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "hit_rate": hit_rate,
        "f1": (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0,
    }


async def embed_pairs(client: OllamaClient, pairs: list[dict]) -> list[PairResult]:
    unique_texts: list[str] = []
    index: dict[str, int] = {}
    for pair in pairs:
        for key in ("canonical", "query"):
            text = pair[key]
            if text not in index:
                index[text] = len(unique_texts)
                unique_texts.append(text)

    vectors: list[list[float]] = []
    batch_size = 16
    for start in range(0, len(unique_texts), batch_size):
        batch = unique_texts[start : start + batch_size]
        vectors.extend(await client.embed_many(batch))

    results: list[PairResult] = []
    for pair in pairs:
        left = vectors[index[pair["canonical"]]]
        right = vectors[index[pair["query"]]]
        results.append(
            PairResult(
                pair_id=pair["id"],
                category=pair["category"],
                should_hit=bool(pair["should_hit"]),
                canonical=pair["canonical"],
                query=pair["query"],
                similarity=cosine_similarity(left, right),
            )
        )
    return results


async def measure_latency(
    client: OllamaClient,
    prompt: str,
    repeats: int,
    chat_model: str,
) -> dict[str, float]:
    embed_ms: list[float] = []
    gen_ms: list[float] = []
    # warmup
    await client.embed(prompt)
    await client.generate(prompt, model=chat_model)

    for _ in range(repeats):
        t0 = time.perf_counter()
        await client.embed(prompt)
        embed_ms.append((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        await client.generate(prompt, model=chat_model)
        gen_ms.append((time.perf_counter() - t1) * 1000)

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs)

    return {
        "embed_ms": mean(embed_ms),
        "generate_ms": mean(gen_ms),
        "semantic_hit_ms": mean(embed_ms),
        "repeats": float(repeats),
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_charts(
    metric_rows: list[dict[str, float]],
    latency: dict[str, dict[str, float]],
    output_dir: Path,
) -> None:
    import matplotlib.pyplot as plt

    thresholds = [row["threshold"] for row in metric_rows]
    precision = [row["precision"] for row in metric_rows]
    recall = [row["recall"] for row in metric_rows]
    hit_rate = [row["hit_rate"] for row in metric_rows]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(thresholds, precision, marker="o", label="precision")
    ax.plot(thresholds, recall, marker="o", label="recall")
    ax.plot(thresholds, hit_rate, marker="o", label="hit-rate")
    ax.set_xlabel("similarity threshold")
    ax.set_ylabel("score")
    ax.set_title("Semantic cache quality vs threshold")
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "threshold_metrics.png", dpi=140)
    plt.close(fig)

    labels: list[str] = []
    values: list[float] = []
    for model, stats in latency.items():
        labels.append(f"{model}\nembed (semantic hit)")
        values.append(stats["embed_ms"])
        labels.append(f"{model}\ngenerate (miss)")
        values.append(stats["generate_ms"])

    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#4c9f70", "#c44e52"] * (len(values) // 2)
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("latency (ms)")
    ax.set_title("Cache hit (embed) vs live generation")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "latency.png", dpi=140)
    plt.close(fig)


def false_positives(results: list[PairResult], threshold: float, limit: int = 5) -> list[PairResult]:
    fps = [row for row in results if not row.should_hit and row.similarity >= threshold]
    fps.sort(key=lambda row: row.similarity, reverse=True)
    near = [row for row in results if not row.should_hit and row.similarity < threshold]
    near.sort(key=lambda row: row.similarity, reverse=True)
    return (fps + near)[:limit]


def commentary(row: PairResult) -> str:
    notes = {
        "miss-001": "Same 'return policy' template, different product category — a cached electronics answer would be wrong for groceries.",
        "miss-002": "Password reset vs 2FA reset share 'reset' language but need different procedures.",
        "miss-003": "US vs Canada shipping; destination is the payload, not a paraphrase.",
        "miss-004": "Two Austen novels; plot summaries must not be swapped.",
        "miss-005": "Photosynthesis vs respiration are related biology topics with opposite net reactions.",
        "miss-006": "list→set vs list→tuple: one word change, different Python types.",
        "miss-009": "Cancel vs pause a subscription is a common support-bot failure mode.",
        "miss-010": "Capitals of different countries look structurally identical.",
        "miss-014": "HTTP status codes share a prefix; 429 and 404 mean very different things.",
        "miss-016": "Same source phrase, different target language.",
        "miss-028": "Enable vs disable 2FA — antonyms that embed nearby.",
        "miss-020": "Bicycle vs car tire — shared 'change a flat * tire' template.",
        "miss-023": "Blue light vs brightness: same 'reduce X from monitor at night' frame, different knob.",
        "miss-029": "Budget off by 10x still looks like the same travel query.",
        "miss-032": "Overfitting vs underfitting are adjacent ML terms with opposite diagnoses.",
        "miss-038": "Add vs multiply is a one-token swap; nomic still scores ~0.95 because the rest of the sentence is identical.",
        "miss-033": "Library card vs credit card — 'apply for a * card'.",
        "miss-035": "TCP handshake vs TLS handshake are easy to conflate.",
        "miss-037": "US city time-zone questions share structure; Denver ≠ Phoenix (no DST).",
        "miss-040": "GET/POST vs PUT/PATCH are all HTTP verb comparisons.",
    }
    return notes.get(
        row.pair_id,
        "Surface wording is close, but the distinguishing slot (entity, polarity, or destination) changes the correct answer.",
    )


async def async_main(args: argparse.Namespace) -> None:
    configure_logging()
    dataset_path = Path(args.dataset)
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    pairs = payload["pairs"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with OllamaClient() as client:
        results = await embed_pairs(client, pairs)
        latency: dict[str, dict[str, float]] = {}
        sample_prompt = "Explain overfitting in machine learning in two sentences."
        models = [args.chat_model]
        if args.expensive_model:
            models.append(args.expensive_model)
        for model in models:
            latency[model] = await measure_latency(
                client,
                sample_prompt,
                repeats=args.latency_repeats,
                chat_model=model,
            )

    thresholds = args.thresholds
    metric_rows = [metrics_at_threshold(results, t) for t in thresholds]
    operating = args.operating_threshold

    pair_rows = [
        {
            "id": row.pair_id,
            "category": row.category,
            "should_hit": row.should_hit,
            "similarity": round(row.similarity, 6),
            "canonical": row.canonical,
            "query": row.query,
        }
        for row in results
    ]
    write_csv(
        OUTPUT_DIR / "pair_similarities.csv",
        pair_rows,
        ["id", "category", "should_hit", "similarity", "canonical", "query"],
    )
    write_csv(
        OUTPUT_DIR / "threshold_metrics.csv",
        [
            {
                **row,
                "precision": round(row["precision"], 4),
                "recall": round(row["recall"], 4),
                "hit_rate": round(row["hit_rate"], 4),
                "f1": round(row["f1"], 4),
            }
            for row in metric_rows
        ],
        ["threshold", "tp", "fp", "tn", "fn", "precision", "recall", "hit_rate", "f1"],
    )

    fp_rows = false_positives(results, operating)
    fp_path = OUTPUT_DIR / "false_positives.md"
    lines = [
        f"# False-positive examples (threshold={operating})",
        "",
        "These are labeled `should_miss` pairs. If similarity is above the operating",
        "threshold they are true false positives; otherwise they are the nearest misses",
        "the model almost confused.",
        "",
    ]
    for row in fp_rows:
        predicted = row.similarity >= operating
        lines.extend(
            [
                f"## {row.pair_id} ({row.category}, similarity={row.similarity:.4f}, "
                f"{'FALSE POSITIVE' if predicted else 'near miss'})",
                "",
                f"- **Cached prompt:** {row.canonical}",
                f"- **Incoming prompt:** {row.query}",
                f"- **Why it's wrong:** {commentary(row)}",
                "",
            ]
        )
    fp_path.write_text("\n".join(lines), encoding="utf-8")

    plot_charts(metric_rows, latency, OUTPUT_DIR)

    summary = {
        "embed_model": settings.ollama_embed_model,
        "thresholds": metric_rows,
        "latency_ms": latency,
        "pair_count": len(results),
        "operating_threshold": operating,
        "false_positives": [
            {"id": row.pair_id, "similarity": row.similarity, "canonical": row.canonical, "query": row.query}
            for row in fp_rows
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("\nThreshold metrics")
    print(f"{'thr':>6} {'P':>7} {'R':>7} {'hit':>7} {'F1':>7} {'tp':>4} {'fp':>4} {'fn':>4}")
    for row in metric_rows:
        print(
            f"{row['threshold']:6.2f} {row['precision']:7.3f} {row['recall']:7.3f} "
            f"{row['hit_rate']:7.3f} {row['f1']:7.3f} {int(row['tp']):4d} {int(row['fp']):4d} {int(row['fn']):4d}"
        )
    print("\nLatency (ms)")
    for model, stats in latency.items():
        print(
            f"  {model}: embed/semantic-hit={stats['embed_ms']:.1f}  "
            f"generate={stats['generate_ms']:.1f}  "
            f"speedup={stats['generate_ms'] / stats['embed_ms']:.1f}x"
        )
    print(f"\nWrote artifacts to {OUTPUT_DIR}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run semantic-cache eval")
    parser.add_argument(
        "--dataset",
        default=str(Path(__file__).with_name("prompt_pairs.json")),
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=DEFAULT_THRESHOLDS,
    )
    parser.add_argument("--operating-threshold", type=float, default=0.92)
    parser.add_argument("--chat-model", default=settings.ollama_chat_model)
    parser.add_argument("--expensive-model", default=None)
    parser.add_argument("--latency-repeats", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    asyncio.run(async_main(parse_args()))


if __name__ == "__main__":
    main()
