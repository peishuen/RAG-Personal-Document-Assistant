"""
This file builds the prompt (the text we send to the llm).
The prompt has the question, the retrieved chunks as context, and the recent chat.
It tells the model to answer only from the context, so it does not make things up.
It also tells the model to cite its sources, so citation_tracker can link the
answer back to a chunk.
"""

# keep only the last few turns in the prompt
# sending the whole chat every time would make cost and waiting time grow
MAX_HISTORY_TURNS = 5

def build_prompt(query: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    # number each chunk so the model can point back to a specific source
    context = "\n\n".join(
        f"[{i+1}] (source: {c['metadata']['source']}, page {c['metadata']['page']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    # turn the recent turns into plain text, or an empty string if there is no history yet
    recent_history = (chat_history or [])[-MAX_HISTORY_TURNS:]
    history_text = "\n".join(
        f"User: {turn['question']}\nAssistant: {turn['answer']}" for turn in recent_history
    )

    # add the history section only when there is history to show
    history_block = f"""
    Conversation history (for context only, do not treat as a source): {history_text} \n
    """ if history_text else ""

    # return the full prompt text for the llm
    return f"""
    Answer the question using only the context below. \n
    Cite the source you used in square brackets, like [Source 1], right after any information you use from it. \n
    If the context does not contain the answer, say you don't know. \n
    
    {history_block}

    Context:
    {context} \n

    Question: {query} \n

    Answer:
    """

