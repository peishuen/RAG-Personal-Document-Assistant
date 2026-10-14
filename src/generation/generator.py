"""
This file creates the final answer to the user's question.
It builds a prompt from the question and the retrieved chunks, sends it to
the qwen llm, and returns the answer text.
"""

from src.generation.prompt_templates import build_prompt
from src.generation.llm_client import get_llm

# build the prompt, send it to the llm, then return only the answer text
def generate_answer(query: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    llm = get_llm()
    prompt = build_prompt(query, chunks, chat_history)

    # send the prompt to the llm and wait for its reply
    response = llm.invoke(prompt)
    return response.content
