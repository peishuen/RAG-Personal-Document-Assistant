"""
This file compares the original pipeline with the tuned pipeline, on two sets of questions:
- the 87 development questions, which were used while tuning
- the 19 held-out questions in qa_hard.json (paraphrased, cross-document, unanswerable), written after the tuning
Original: whitespace bm25 tokens, raw pdf text, no source header.
Tuned: punctuation-stripped bm25 tokens with stop words removed, cleaned text, source header (the app's current setup).
Both use the same embedder and chat model, so the comparison is fair.
Retrieval is scored on every answerable question. Answers are written and graded by the llm judge
(on all held-out questions, and on an evenly spaced 30 of the development questions).
Run it like this: python evaluation/final_comparison.py
"""

import os

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
import src.retrieval.bm25_retriever as bm25_module
from judge import grade_answers
from retrieval_metrics import cell, evaluate_collection, load_questions, pick_subset

RESULTS_DIR = "evaluation/results"

# keep the app's current tokenizer, so it can be put back after the original one is tested
CURRENT_TOKENIZER = bm25_module.tokenize

CONFIGS = [
    {"name": "original", "collection": "documents", "tokenizer": lambda text: text.lower().split()},
    {"name": "tuned (current app)", "collection": "documents_clean_header", "tokenizer": CURRENT_TOKENIZER},
]

DATASETS = [
    {"name": "development set (87 questions, used while tuning)", "path": "evaluation/qa_dataset.json", "answers": 30},
    {"name": "held-out set (19 questions, written after tuning)", "path": "evaluation/qa_hard.json", "answers": 100},
]

def compare(datasets: list[dict]) -> str:
    lines = ["# Original vs Tuned Pipeline", "",
             "Both pipelines use the same embedder and chat model, so they can be compared with each other.", ""]

    for dataset in datasets:
        questions = load_questions(dataset["path"])
        answerable = [q for q in questions if q.get("answerable", True)]
        subset = pick_subset(questions, dataset["answers"])
        retrieval_rows, answer_rows, category_rows = [], [], []

        for config in CONFIGS:
            # switch the bm25 tokenizer, and clear the saved indexes so they are rebuilt with it
            bm25_module.tokenize = config["tokenizer"]
            bm25_module._bm25_cache.clear()

            print(f"{dataset['name']} | {config['name']}: retrieval on {len(answerable)} questions...")
            for method, metrics in evaluate_collection(answerable, config["collection"]).items():
                retrieval_rows.append(f"| {config['name']} | {method} | {cell(metrics['recall'])} | {cell(metrics['rr'])} |")

            print(f"{dataset['name']} | {config['name']}: grading {len(subset)} answers...")
            graded = grade_answers(subset, config["collection"])
            answer_rows.append(f"| {config['name']} | {graded['counts']['correct']} / {len(subset)} | {cell(graded['score'])} |")
            for category, group in graded["by_category"].items():
                category_rows.append(f"| {config['name']} | {category} | {group['correct']} | {group['partial']} | {group['wrong']} |")

        # put the app's own tokenizer back
        bm25_module.tokenize = CURRENT_TOKENIZER
        bm25_module._bm25_cache.clear()

        lines += [f"## {dataset['name']}", "",
                  "**Retrieval (top 5)**", "", "| Pipeline | Method | Recall@5 | MRR@5 |", "|---|---|---|---|"] + retrieval_rows + [""]
        lines += ["**Answers graded by the LLM judge**", "", "| Pipeline | Fully correct | Average score (partial = 0.5) |", "|---|---|---|"] + answer_rows + [""]
        lines += ["**Verdicts by question type**", "", "| Pipeline | Type | Correct | Partial | Wrong |", "|---|---|---|---|---|"] + category_rows + [""]

    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    report = compare(DATASETS)
    print("\n" + report)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(f"{RESULTS_DIR}/final_comparison.md", "w", encoding="utf-8") as f:
        f.write(report)
