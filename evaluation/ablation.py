"""
This file runs the ablation study: it removes or changes one part of the retrieval
pipeline at a time, to show how much each part adds.
Part 1 (components): bm25 only, semantic only, and bm25 + semantic merged by rank (rrf, the search the app uses).
Part 2 (chunk size and text preparation): the same three methods on collections built with different chunk sizes,
plus the app's current setup (cleaned text and a source header).
It scores retrieval only (no answers are generated), so it only needs a few question embeddings.
It runs on the separate evaluation database (data/eval_chroma_db), built by build_eval_db.py.
Run it like this: python evaluation/ablation.py
"""

import os

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
from retrieval_metrics import cell, evaluate_collection, load_questions, TOP_K

RESULTS_DIR = "evaluation/results"

# the app's current setup: default chunk size, cleaned text and a source header on every chunk
CURRENT_LABEL = "current app (600 / 200 pdf, 800 / 100 text, cleaned text + header)"

# list the collections for the study, with a readable label for each
SETUPS = [
    ("chunks_400_60", "400 / 60"),
    ("documents", "600 / 200 pdf, 800 / 100 text (raw text)"),
    ("chunks_1000_150", "1000 / 150"),
    ("chunks_1500_200", "1500 / 200"),
    ("documents_clean_header", CURRENT_LABEL),
]

def build_report(question_count: int, results: dict) -> str:
    lines = [
        "# Ablation Study",
        "",
        f"Retrieval only, {question_count} labeled questions, top {TOP_K} results, Qwen embeddings. Each cell is the mean with a 95% bootstrap confidence interval.",
        "",
        "## Part 1: pipeline components (the app's current setup)",
        "",
        "| Method | Recall@5 | MRR@5 | Precision@5 |",
        "|---|---|---|---|",
    ]
    for method, metrics in results[CURRENT_LABEL].items():
        lines.append(f"| {method} | {cell(metrics['recall'])} | {cell(metrics['rr'])} | {cell(metrics['precision'])} |")

    lines += ["", "## Part 2: chunk size, overlap and text preparation", "", "Recall@5 for each method.", "",
              "| Setup | bm25 | semantic | rrf |", "|---|---|---|---|"]
    for label, metrics in results.items():
        lines.append(f"| {label} | " + " | ".join(cell(metrics[m]["recall"]) for m in ("bm25", "semantic", "rrf")) + " |")
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    questions = load_questions(answerable_only=True)
    print(f"loaded {len(questions)} labeled questions\n")

    results = {}
    for collection, label in SETUPS:
        print(f"running {collection} ({label})...")
        results[label] = evaluate_collection(questions, collection)

    report = build_report(len(questions), results)
    print("\n" + report)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(f"{RESULTS_DIR}/ablation_report.md", "w", encoding="utf-8") as f:
        f.write(report)
