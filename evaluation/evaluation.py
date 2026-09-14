# run retrieval and generation evaluation using the labeled qa dataset
# computes precision@k and recall@k for bm25, semantic and hybrid retrieval and answer correctness

import sys
import os 
import json

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.semantic_retriever import semantic_search
from src.retrieval.hybrid_ranker import hybrid_search, build_chunk_id
from src.generation.generator import generate_answer
from src.generation.grounding_check import cosine_similarity
from src.embeddings.embedder import get_dashscope_embedder

TOP_K = 5

# below this similarity, a generated answer is treated as not matching the expected answer
CORRECTNESS_THRESHOLD = 0.75

def load_qa_dataset(path: str = "evaluation/qa_dataset.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def precision_recall_at_k(results: list[dict], ground_truth_ids: list[str]) -> tuple[float, float]:
    # build the same chunk id used everywhere else
    retrieved_ids = [build_chunk_id(r) for r in results]

    # count how many retrieved chunks are actually relevant
    relevant_retrieved = sum(1 for cid in retrieved_ids if cid in ground_truth_ids)

    precision = relevant_retrieved / len(retrieved_ids) if retrieved_ids else 0
    recall = relevant_retrieved / len(ground_truth_ids) if ground_truth_ids else 0

    return precision, recall


def run_evaluation(qa_dataset: list[dict]) -> dict:
    methods = {
        "bm25": lambda q: bm25_search(q, top_k=TOP_K),
        "semantic": lambda q: semantic_search(q, top_k=TOP_K),
        "hybrid": lambda q: hybrid_search(q, top_k=TOP_K)
    }

    scores = {name: {"precision": [], "recall": []} for name in methods}
    embedder = get_dashscope_embedder()
    correct_count = 0
    details = []

    for item in qa_dataset:
        hybrid_results = None

        # run every retrieval method once, score it then keep the hybrid results for generation below
        for name, search_fn in methods.items():
            results = search_fn(item['question'])
            if name == "hybrid":
                hybrid_results = results

            precision, recall = precision_recall_at_k(results, item['ground_truth_chunk_ids'])
            scores[name]["precision"].append(precision)
            scores[name]["recall"].append(recall)

        # generate an answer from the hybrid results and compare it to expected ans
        generated_answer = generate_answer(item['question'], hybrid_results)
        generated_vector = embedder.embed_query(generated_answer)
        expected_vector = embedder.embed_query(item['expected_answer'])
        # cast to plain python types, numpy's float64/bool_ from cosine_similarity are not json serializable
        similarity = float(cosine_similarity(generated_vector, expected_vector))
        is_correct = bool(similarity >= CORRECTNESS_THRESHOLD)

        if is_correct:
            correct_count += 1

        # record this question's own result, so failures can be traced back to real evidence later
        details.append({
            "question": item['question'],
            "expected_answer": item['expected_answer'],
            "generated_answer": generated_answer,
            "similarity": similarity,
            "correct": is_correct
        })

    # average precision and recall across every question, per method
    retrieval_summary = {
        name: {
            "precision@k": sum(values['precision']) / len(values['precision']),
            'recall@k': sum(values['recall']) / len(values['recall'])
        }
        for name, values in scores.items()
    }

    return {
        "retrieval": retrieval_summary,
        "answer_accuracy": correct_count / len(qa_dataset),
        "details": details
    }

if __name__ == "__main__":
    qa_dataset = load_qa_dataset()
    print(f"loaded {len(qa_dataset)} labeled questions\n")

    results = run_evaluation(qa_dataset)

    print("retrieval results:")
    for method, metrics in results['retrieval'].items():
        print(f"{method}: precision@{TOP_K} = {metrics['precision@k']:.3f}, recall@{TOP_K} = {metrics['recall@k']:.3f}")

    print(f"\nanswer correctness: {results['answer_accuracy']:.1%} of generated answers matched the expected answer")

    # save every question's result to disk, so specific findings can be traced back to real evidence
    details_path = "evaluation/results/detailed_results.json"
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(results['details'], f, indent=2, ensure_ascii=False)
    print(f"\nper-question results saved to {details_path}")

    failures = [d for d in results['details'] if not d['correct']]
    if failures:
        print(f"\n{len(failures)} question(s) failed the correctness check:")
        for d in failures:
            print(f"\n- {d['question']} (similarity {d['similarity']:.3f})")
            print(f"  expected: {d['expected_answer']}")
            print(f"  generated: {d['generated_answer']}")