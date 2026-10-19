"""
This file tests how good the search and the answers are, using a labeled question set.
Retrieval (bm25, semantic and their rank fusion) is scored on every answerable question with
precision, recall and mrr at 5, each with a 95% confidence interval.
Answers are written from the top 5 chunks and graded by an llm judge (correct, partial or wrong)
on an evenly spaced subset of the questions, because that part costs the most tokens.
It runs on the separate evaluation database (data/eval_chroma_db), built by build_eval_db.py.
Run it like this: python evaluation/evaluation.py --answers 30
"""

import argparse
import json
import os

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
from judge import grade_answers
from retrieval_metrics import cell, evaluate_collection, load_questions, pick_subset

RESULTS_DIR = "evaluation/results"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", type=int, default=30, help="how many questions to grade the answers for")
    parser.add_argument("--dataset", default="evaluation/qa_dataset.json", help="the labeled question file")
    args = parser.parse_args()

    questions = load_questions(args.dataset)
    print(f"loaded {len(questions)} labeled questions from {args.dataset}\n")

    print("retrieval (top 5, mean with 95% confidence interval):")
    retrieval = evaluate_collection([q for q in questions if q.get("answerable", True)], "documents")
    for method, metrics in retrieval.items():
        print(f"  {method}: recall {cell(metrics['recall'])}, mrr {cell(metrics['rr'])}, precision {cell(metrics['precision'])}")

    subset = pick_subset(questions, args.answers)
    print(f"\ngrading answers for {len(subset)} questions...")
    graded = grade_answers(subset)
    counts = graded["counts"]
    print(f"  {counts['correct']} correct, {counts['partial']} partial, {counts['wrong']} wrong")
    print(f"  average score (partial = 0.5): {cell(graded['score'])}")
    for category, group in graded["by_category"].items():
        print(f"    {category}: {group['correct']} correct, {group['partial']} partial, {group['wrong']} wrong")

    # save every graded answer, so the failures can be checked later
    # add the question file name to the output file, so a second dataset does not overwrite the first
    tag = "" if args.dataset.endswith("qa_dataset.json") else "_" + os.path.splitext(os.path.basename(args.dataset))[0]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(f"{RESULTS_DIR}/detailed_results{tag}.json", "w", encoding="utf-8") as f:
        json.dump(graded["details"], f, indent=2, ensure_ascii=False)

    misses = [d for d in graded["details"] if d["verdict"] != "correct"]
    for d in misses:
        print(f"\n- {d['question']} ({d['verdict']}: {d['judge_reason']})")
        print(f"  expected: {d['expected_answer']}")
        print(f"  generated: {d['generated_answer'][:300]}")
