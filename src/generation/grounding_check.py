# check whether the generated answer is actually backed by the retrieved chunks
# asks the llm to fact-check the answer's specific claims against each chunk's actual text,
# instead of just comparing embeddings, which only catches "different topic", not "same topic, wrong fact"

import re
from src.generation.llm_client import get_llm

def build_grounding_prompt(answer: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)
    )

    return f"""
    You are fact-checking an answer against source chunks. Do not judge by general topic similarity,
    check whether the chunk actually contains the specific claims made in the answer. \n

    Source chunks:
    {context} \n

    Answer to check: {answer} \n

    Is this answer's specific claims actually supported by one of the source chunks above?
    Reply in exactly this format, nothing else: \n

    GROUNDED: yes or no
    BEST_CHUNK: the number of the chunk that best supports (or best contradicts) the answer
    REASON: one short sentence explaining why
    """

def parse_grounding_response(response_text: str, chunks: list[dict]) -> dict:
    grounded_match = re.search(r"GROUNDED:\s*(yes|no)", response_text, re.IGNORECASE)
    chunk_match = re.search(r"BEST_CHUNK:\s*(\d+)", response_text)
    reason_match = re.search(r"REASON:\s*(.+)", response_text)

    grounded = bool(grounded_match) and grounded_match.group(1).lower() == "yes"

    chunk_index = int(chunk_match.group(1)) - 1 if chunk_match else 0
    if not (0 <= chunk_index < len(chunks)):
        chunk_index = 0

    reason = reason_match.group(1).strip() if reason_match else "no reason given"

    return {
        "grounded": grounded,
        "best_chunk": chunks[chunk_index],
        "reason": reason
    }

def check_grounding(answer: str, chunks: list[dict]) -> dict:
    if not chunks:
        return {"grounded": False, "best_chunk": None, "reason": "no chunks were retrieved"}

    llm = get_llm()
    prompt = build_grounding_prompt(answer, chunks)
    response = llm.invoke(prompt)

    return parse_grounding_response(response.content, chunks)
