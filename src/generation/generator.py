"""
This file creates the final answer to the user's question.
It builds a prompt from the question and the retrieved chunks, sends it to
the qwen llm, and returns the answer text.
There are two versions: generate_answer waits for the full answer, and
stream_answer gives the answer piece by piece, so the user can start reading at once.
"""

from src.generation.prompt_templates import build_prompt
from src.generation.llm_client import get_llm
from src.metrics.tracker import timed, record_llm, set_stage, elapsed_ms

# build the prompt, send it to the llm, then return only the answer text
def generate_answer(query: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    llm = get_llm("answer")
    prompt = build_prompt(query, chunks, chat_history)

    # send the prompt to the llm, and time how long it takes to reply
    with timed("generate"):
        response = llm.invoke(prompt)

    # count the tokens used by this call
    record_llm(response)
    return response.content

# build the prompt, then give back the answer text in small pieces as the llm writes it
def stream_answer(query: str, chunks: list[dict], chat_history: list[dict] = None):
    llm = get_llm("answer")
    prompt = build_prompt(query, chunks, chat_history)

    full_reply = None
    first_piece_seen = False

    with timed("generate"):
        for piece in llm.stream(prompt):
            # save the time of the first words, measured from the start of the request
            if piece.content and not first_piece_seen:
                set_stage("first_token", elapsed_ms())
                first_piece_seen = True

            # add the pieces together, so the token count is available at the end
            full_reply = piece if full_reply is None else full_reply + piece

            if piece.content:
                yield piece.content

    # count the tokens used by the whole reply
    if full_reply is not None:
        record_llm(full_reply)
