"""
This file scores retrieval, and holds the helpers shared by the evaluation scripts.
A retrieved chunk counts as relevant when it contains the question's ground truth quote.
Matching on a quote instead of a chunk id keeps the labels valid when the chunk size changes.
"""

import json
import random
from concurrent.futures import ThreadPoolExecutor

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.semantic_retriever import semantic_search
from src.retrieval.hybrid_ranker import reciprocal_rank_fusion

# set how many chunks each search returns, and how many candidates each search gives to the merge
TOP_K = 5
FUSION_K = 20

def load_questions(path: str = "evaluation/qa_dataset.json", answerable_only: bool = False) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    # unanswerable questions have no answer chunk, so they cannot be scored for retrieval
    return [q for q in questions if q.get("answerable", True)] if answerable_only else questions

def pick_subset(items: list[dict], count: int) -> list[dict]:
    # take evenly spaced items, so every document is represented
    if count >= len(items):
        return items
    step = len(items) / count
    return [items[int(i * step)] for i in range(count)]

def normalise(text: str) -> str:
    # lowercase and collapse spaces, so line breaks do not break the quote match
    return " ".join(text.lower().split())

def quotes_of(item: dict) -> list[str]:
    # return the quotes that mark the answer: one for most questions, several for questions that need more than one chunk
    return item.get("ground_truth_quotes") or [item["ground_truth_quote"]]

def score_results(results: list[dict], item: dict) -> dict:
    texts = [normalise(r["text"]) for r in results]
    quotes = [normalise(q) for q in quotes_of(item)]

    # find the rank (starting at 1) of every chunk that holds any of the quotes
    relevant_ranks = [rank for rank, text in enumerate(texts, start=1) if any(q in text for q in quotes)]
    found = sum(1 for q in quotes if any(q in text for text in texts))

    return {
        # precision is the share of results that are relevant
        "precision": len(relevant_ranks) / len(results) if results else 0.0,
        # recall is the share of needed quotes found: 1 for a single-chunk question when its chunk is in the results
        "recall": found / len(quotes),
        # reciprocal rank rewards putting the answer chunk near the top (1, 1/2, 1/3, ...)
        "rr": 1.0 / relevant_ranks[0] if relevant_ranks else 0.0,
    }

def ci_stat(values: list[float], rounds: int = 2000, seed: int = 0) -> dict:
    # the mean, with a 95% interval from resampling the questions many times (bootstrap)
    random.seed(seed)
    n = len(values)
    means = sorted(sum(random.choices(values, k=n)) / n for _ in range(rounds))
    return {"mean": sum(values) / n, "ci_low": means[int(0.025 * rounds)], "ci_high": means[int(0.975 * rounds)]}

def cell(stat: dict) -> str:
    return f"{stat['mean']:.3f} ({stat['ci_low']:.2f}-{stat['ci_high']:.2f})"

def run_methods(query: str, collection: str) -> dict:
    # get the candidates once, and reuse them for every method
    bm25_results = bm25_search(query, collection, FUSION_K)
    semantic_results = semantic_search(query, collection, FUSION_K)
    return {
        "bm25": bm25_results[:TOP_K],
        "semantic": semantic_results[:TOP_K],
        "rrf": reciprocal_rank_fusion(bm25_results, semantic_results)[:TOP_K],
    }

def evaluate_collection(questions: list[dict], collection: str) -> dict:
    # score bm25, semantic and rrf on every question, and average each metric with a confidence interval
    def score_question(item: dict) -> dict:
        return {name: score_results(results, item) for name, results in run_methods(item["question"], collection).items()}

    # score a few questions at the same time to save waiting time
    with ThreadPoolExecutor(max_workers=4) as executor:
        per_question = list(executor.map(score_question, questions))

    return {
        method: {metric: ci_stat([row[method][metric] for row in per_question]) for metric in ("precision", "recall", "rr")}
        for method in per_question[0]
    }
