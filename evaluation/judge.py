"""
This file grades generated answers with an llm judge.
It replaces the fixed 0.75 cosine cutoff, which marked good paraphrases as wrong.
The judge gives one label: correct, partial or wrong.
For questions the documents cannot answer, the right behaviour is to decline, and the judge grades that instead.
"""

import re
from concurrent.futures import ThreadPoolExecutor

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
from src.generation.llm_client import get_llm
from src.generation.generator import generate_answer
from src.retrieval.hybrid_ranker import hybrid_search
from retrieval_metrics import ci_stat

# give each label a score, so a partial answer counts for half
LABEL_SCORES = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}

def build_judge_prompt(question: str, expected: str, generated: str) -> str:
    # ask for a fixed reply format, so it is easy to parse
    return f"""
    You are grading an answer to a question. Compare it with the expected answer.
    Judge the facts, not the wording. Different wording is fine if the meaning is the same.
    Extra correct detail in the generated answer is fine.

    Question: {question}
    Expected answer: {expected}
    Generated answer: {generated}

    Use these labels:
    - correct: it contains all key facts of the expected answer and nothing that contradicts it
    - partial: it contains some key facts but misses or changes others
    - wrong: it misses the key facts, contradicts the expected answer, or says it does not know

    Reply in exactly this format, nothing else:
    VERDICT: correct or partial or wrong
    REASON: one short sentence
    """

def build_unanswerable_prompt(question: str, generated: str) -> str:
    # grade a question the documents cannot answer: the right behaviour is to decline, not to invent an answer
    return f"""
    The documents do NOT contain the answer to the question below, so a good system declines to answer.
    Grade the generated answer on that behaviour.

    Question: {question}
    Generated answer: {generated}

    Use these labels:
    - correct: it says the information is not in the documents (or that it does not know), and does not present any made-up fact as the answer.
      Mentioning related facts that are clearly labeled as different from what was asked is fine.
    - partial: it declines, but also offers a specific figure or fact as a tentative answer to the question that was asked
    - wrong: it gives a confident answer to the question as if the documents supported it

    Reply in exactly this format, nothing else:
    VERDICT: correct or partial or wrong
    REASON: one short sentence
    """

def parse_judge_response(response_text: str) -> dict:
    # find the verdict and the reason with regex
    verdict_match = re.search(r"VERDICT:\s*(correct|partial|wrong)", response_text, re.IGNORECASE)
    reason_match = re.search(r"REASON:\s*(.+)", response_text)

    # treat the answer as wrong when the reply cannot be read
    verdict = verdict_match.group(1).lower() if verdict_match else "wrong"
    reason = reason_match.group(1).strip() if reason_match else "no reason given"

    return {"verdict": verdict, "score": LABEL_SCORES[verdict], "reason": reason}

def judge_answer(question: str, expected: str, generated: str, answerable: bool = True) -> dict:
    # set temperature to 0 so the same answer gets the same grade each time
    llm = get_llm("judge").bind(temperature=0)

    # use the decline-to-answer rubric when the documents cannot answer the question
    if answerable:
        prompt = build_judge_prompt(question, expected, generated)
    else:
        prompt = build_unanswerable_prompt(question, generated)

    response = llm.invoke(prompt)
    return parse_judge_response(response.content)

def grade_answers(questions: list[dict], collection: str = "documents") -> dict:
    # for each question: find the chunks like the app does, write an answer, and let the judge grade it
    def grade(item: dict) -> dict:
        chunks = hybrid_search(item["question"], collection_name=collection, top_k=5)
        generated = generate_answer(item["question"], chunks)
        judged = judge_answer(item["question"], item["expected_answer"], generated, item.get("answerable", True))
        return {
            "question": item["question"],
            "category": item.get("category", "development"),
            "expected_answer": item["expected_answer"],
            "generated_answer": generated,
            "verdict": judged["verdict"],
            "judge_reason": judged["reason"],
            "score": judged["score"],
        }

    with ThreadPoolExecutor(max_workers=4) as executor:
        details = list(executor.map(grade, questions))

    # count the verdicts overall, and for each question category (paraphrased, cross-document, unanswerable)
    counts = {label: 0 for label in LABEL_SCORES}
    by_category = {}
    for d in details:
        counts[d["verdict"]] += 1
        by_category.setdefault(d["category"], {label: 0 for label in LABEL_SCORES})[d["verdict"]] += 1

    return {
        "details": details,
        "counts": counts,
        "by_category": by_category,
        "score": ci_stat([d["score"] for d in details]),
    }
