"""
This file measures how well the grounding check works.
It takes answers that the llm judge marked correct, so they really are supported by the retrieved chunks,
and checks that the grounding check approves them (a "false alarm" is a good answer it rejects).
Then it damages each good answer in three ways and checks that the grounding check catches the damage:
- changed fact: one number, name or direction in the answer is changed
- swapped answer: the answer is replaced by the good answer of a different question
- added claim: one plausible but unsupported sentence is added to the answer
It compares the grounding check with its current thinking budget against thinking switched off.
It runs on the separate evaluation database (data/eval_chroma_db), built by build_eval_db.py.
Run it like this: python evaluation/grounding_eval.py [question count]
"""

import sys
from concurrent.futures import ThreadPoolExecutor

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
import src.generation.llm_client as llm_client
from src.generation.generator import generate_answer
from src.generation.grounding_check import check_grounding
from src.generation.llm_client import get_llm
from src.retrieval.cross_document import cross_document_search
from judge import judge_answer
from retrieval_metrics import ci_stat, load_questions, pick_subset

def change_one_fact(answer: str) -> str:
    # ask the llm to change exactly one key fact, keeping everything else the same
    prompt = f"""
    Rewrite the answer below, changing exactly ONE key fact (a number, a name, or a direction such as higher or lower)
    to a different, plausible value. Keep everything else, including the [Source N] markers, exactly the same.
    Output only the rewritten answer.

    Answer: {answer}
    """
    return get_llm("answer").bind(temperature=0.3).invoke(prompt).content.strip()

def add_unsupported_claim(answer: str, chunks: list[dict]) -> str:
    # ask the llm to add one sentence with a specific fact that the chunks do not contain
    context = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(chunks))
    prompt = f"""
    Below are some source chunks and an answer. Add ONE extra sentence at the end of the answer that states a specific,
    plausible-sounding fact on the same topic that is NOT stated anywhere in the chunks, and end it with a [Source 1] marker.
    Keep the original answer unchanged. Output the full answer.

    Chunks:
    {context}

    Answer: {answer}
    """
    return get_llm("answer").bind(temperature=0.3).invoke(prompt).content.strip()

def prepare_case(item: dict) -> dict | None:
    # find the chunks like the app does, write an answer, and keep it only when the judge says it is correct
    chunks = cross_document_search(item["question"], top_k=5)
    answer = generate_answer(item["question"], chunks)
    if judge_answer(item["question"], item["expected_answer"], answer)["verdict"] != "correct":
        return None
    return {"chunks": chunks, "answer": answer,
            "changed": change_one_fact(answer), "added": add_unsupported_claim(answer, chunks)}

def share_flagged(texts_by_case: list[tuple[dict, str]]) -> str:
    # run the grounding check on each text and report how often it says "not grounded"
    def flagged(pair):
        case, text = pair
        return 1.0 if not check_grounding(text, case["chunks"])["grounded"] else 0.0

    with ThreadPoolExecutor(max_workers=4) as executor:
        flags = list(executor.map(flagged, texts_by_case))
    stat = ci_stat(flags)
    return f"{stat['mean']:.0%} ({stat['ci_low']:.0%}-{stat['ci_high']:.0%}), n={len(flags)}"

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    questions = load_questions(answerable_only=True)

    print(f"preparing {count} questions (answer, judge, and two damaged versions each)...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        cases = [c for c in executor.map(prepare_case, pick_subset(questions, count)) if c]
    print(f"{len(cases)} good answers kept\n")

    # swap in the good answer of the next question, so each answer is checked against the wrong chunks
    swapped = [(c, cases[(i + 1) % len(cases)]["answer"]) for i, c in enumerate(cases)]

    print("share of answers flagged as not grounded (95% interval):")
    print("| Setting | good answer (false alarm) | changed fact | swapped answer | added unsupported claim |")
    print("|---|---|---|---|---|")
    for label, budget in (("thinking budget 200 (current app)", 200), ("thinking off", 0)):
        # change the grounding check's thinking budget, then run all the checks
        llm_client.JOB_SETTINGS["grounding"]["thinking_budget"] = budget
        row = [
            share_flagged([(c, c["answer"]) for c in cases]),
            share_flagged([(c, c["changed"]) for c in cases if c["changed"] != c["answer"]]),
            share_flagged(swapped),
            share_flagged([(c, c["added"]) for c in cases if c["added"] != c["answer"]]),
        ]
        print(f"| {label} | " + " | ".join(row) + " |")
