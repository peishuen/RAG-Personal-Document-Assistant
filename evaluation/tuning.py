"""
This file tests ways to improve retrieval, one change at a time, on the labeled questions.
Part 1: bm25 tokenizers (plain whitespace splitting, punctuation stripping, stop words, light stemming).
Part 2: how bm25 and semantic results are merged (rrf constant and bm25 weight).
It runs on the separate evaluation database (data/eval_chroma_db), built by build_eval_db.py.
Run it like this: python evaluation/tuning.py [collection]
"""

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
import src.retrieval.bm25_retriever as bm25_module
from src.retrieval.bm25_retriever import STOP_WORDS
from src.retrieval.hybrid_ranker import build_chunk_id
from src.retrieval.semantic_retriever import semantic_search
from retrieval_metrics import FUSION_K, TOP_K, cell, ci_stat, load_questions, score_results

RESULTS_DIR = "evaluation/results"

def light_stem(word: str) -> str:
    # cut a few common endings, so "retrieves", "retrieved" and "retrieving" look alike
    for suffix, minimum in (("ies", 4), ("ing", 5), ("ed", 4), ("es", 4), ("s", 4)):
        if word.endswith(suffix) and len(word) >= minimum + len(suffix) - 1:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word

def words(text: str) -> list[str]:
    # lowercase, and keep only the words (this is what the app does before removing stop words)
    return re.findall(r"\w+", text.lower())

# list the tokenizers to compare
TOKENIZERS = {
    "whitespace (old app setting)": lambda text: text.lower().split(),
    "punctuation stripped": words,
    "stripped + stop words (now in the app)": lambda text: [w for w in words(text) if w not in STOP_WORDS],
    "stripped + stop words + stemming": lambda text: [light_stem(w) for w in words(text) if w not in STOP_WORDS],
}

def weighted_rrf(bm25_results: list[dict], semantic_results: list[dict], k: int, bm25_weight: float) -> list[dict]:
    # merge two ranked lists, and let the bm25 list count more or less than the semantic list
    scores, lookup = {}, {}
    for weight, results in ((bm25_weight, bm25_results), (1.0, semantic_results)):
        for rank, result in enumerate(results):
            chunk_id = build_chunk_id(result)
            scores[chunk_id] = scores.get(chunk_id, 0) + weight / (k + rank + 1)
            lookup[chunk_id] = result
    return [lookup[chunk_id] for chunk_id in sorted(scores, key=scores.get, reverse=True)]

def summarise(results_per_question: list[list[dict]], questions: list[dict]) -> dict:
    # average recall and mrr at 5 over all questions
    scores = [score_results(results[:TOP_K], q) for results, q in zip(results_per_question, questions)]
    return {metric: ci_stat([s[metric] for s in scores]) for metric in ("recall", "rr")}

def main(collection: str) -> None:
    questions = load_questions(answerable_only=True)
    print(f"{len(questions)} questions, collection {collection}\n")

    # run the semantic search once per question and reuse it everywhere
    with ThreadPoolExecutor(max_workers=4) as executor:
        semantic = list(executor.map(lambda q: semantic_search(q["question"], collection, FUSION_K), questions))

    lines = ["# Tuning Report", "", f"{len(questions)} questions, collection `{collection}`, top {TOP_K}. Mean with 95% confidence interval.", "",
             "## Part 1: bm25 tokenizer", "", "| Tokenizer | bm25 Recall@5 | bm25 MRR@5 |", "|---|---|---|"]

    bm25_by_tokenizer = {}
    for name, tokenizer in TOKENIZERS.items():
        # swap the tokenizer, and clear the saved index so it is rebuilt with the new one
        bm25_module.tokenize = tokenizer
        bm25_module._bm25_cache.clear()
        bm25_by_tokenizer[name] = [bm25_module.bm25_search(q["question"], collection, FUSION_K) for q in questions]
        stats = summarise(bm25_by_tokenizer[name], questions)
        lines.append(f"| {name} | {cell(stats['recall'])} | {cell(stats['rr'])} |")
        print(f"tokenizer {name}: recall@5 {stats['recall']['mean']:.3f}, mrr {stats['rr']['mean']:.3f}")

    # use the app's tokenizer for part 2
    bm25 = bm25_by_tokenizer["stripped + stop words (now in the app)"]

    lines += ["", "## Part 2: merging bm25 and semantic results (with the app's tokenizer)", "",
              "| rrf constant | bm25 weight | Recall@5 | MRR@5 |", "|---|---|---|---|"]
    for k, weight in [(60, 1.0), (60, 0.5), (60, 0.3), (30, 1.0), (30, 0.5), (10, 1.0), (10, 0.5)]:
        fused = [weighted_rrf(b, s, k, weight) for b, s in zip(bm25, semantic)]
        stats = summarise(fused, questions)
        current = " (current)" if (k, weight) == (60, 1.0) else ""
        lines.append(f"| {k}{current} | {weight} | {cell(stats['recall'])} | {cell(stats['rr'])} |")
        print(f"fusion k={k} bm25 weight={weight}: recall@5 {stats['recall']['mean']:.3f}, mrr {stats['rr']['mean']:.3f}")

    report = "\n".join(lines) + "\n"
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = f"{RESULTS_DIR}/tuning_report_{collection}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nsaved {out}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "documents")
