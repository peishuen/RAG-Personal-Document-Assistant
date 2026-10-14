"""
This file turns a follow-up question into a full question that stands alone.
For example, "what about its accuracy" becomes a question that names the
thing "its" points to.
This lets the search work on follow-up questions.
"""

from src.generation.llm_client import get_llm
from src.generation.prompt_templates import MAX_HISTORY_TURNS

# rewrite the question using the chat history
def rewrite_query(question: str, chat_history: list[dict]) -> str:
    # skip rewriting when there is no earlier chat, because the question already stands alone
    if not chat_history:
        return question

    llm = get_llm()

    # use only the question and answer text, and ignore grounding and citation info
    history_text = "\n".join(
        f"User: {turn['question']}\nAssistant: {turn['answer']}" for turn in chat_history[-MAX_HISTORY_TURNS:]
    )

    prompt = f"""
    Given the conversation history and a follow-up question, rewrite the follow-up question
    into a standalone question that makes sense without the history. \n

    If the follow-up question is already standalone, return it unchanged.
    Only output the rewritten question, nothing else. \n

    Conversation history: {history_text} \n

    Follow-up question: {question} \n

    Standalone question:
    """

    # ask the llm to rewrite, then remove extra spaces around the reply
    response = llm.invoke(prompt)
    return response.content.strip()
