"""
This file checks if the answer is really backed by the retrieved chunks.
It asks the llm to fact-check the specific claims in the answer against the
text of each chunk.
This is better than comparing embeddings, which only notices a different topic
and misses cases where the topic is the same but the fact is wrong.
"""

import re
from src.generation.llm_client import get_llm

def build_grounding_prompt(answer: str, chunks: list[dict]) -> str:
    # number each chunk so the llm can name the best one
    context = "\n\n".join(
        f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)
    )

    # return the fact-check prompt, which asks for a fixed reply format
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
    # find the three parts of the reply with regex
    grounded_match = re.search(r"GROUNDED:\s*(yes|no)", response_text, re.IGNORECASE)
    chunk_match = re.search(r"BEST_CHUNK:\s*(\d+)", response_text)
    reason_match = re.search(r"REASON:\s*(.+)", response_text)

    # treat the answer as grounded only when the reply says yes
    grounded = bool(grounded_match) and grounded_match.group(1).lower() == "yes"

    # convert the chunk number to a list index, and use the first chunk if it is invalid
    chunk_index = int(chunk_match.group(1)) - 1 if chunk_match else 0
    if not (0 <= chunk_index < len(chunks)):
        chunk_index = 0

    reason =reason_match.group(1).strip() if reason_match else "no reason given"

    return {
        "grounded": grounded,
        "best_chunk": chunks[chunk_index],
        "reason": reason
    }

def check_grounding(answer: str, chunks: list[dict]) -> dict:
    # mark as not grounded when there are no chunks to check against
    if not chunks:
        return {"grounded": False, "best_chunk": None, "reason": "no chunks were retrieved"}

    llm = get_llm()
    prompt = build_grounding_prompt(answer, chunks)
    response = llm.invoke(prompt)

    # turn the llm reply into a simple result
    return parse_grounding_response(response.content, chunks)
