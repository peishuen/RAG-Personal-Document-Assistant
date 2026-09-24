# build the prompt that gives the llm the question plus the retrieved chunks as context
# tells the model to answer only from the context, so it stays grounded instead of making things up
# also tells it to cite which source it used, so citation_tracker can trace the answer back to a chunk

def build_prompt(query: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    # number each chunk so the model can point back to a specific source
    context = "\n\n".join(
        f"[{i+1}] (source: {c['metadata']['source']}, page {c['metadata']['page']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    # format prior turns as plain conversation, empty string when there is no history yet
    history_text = "\n".join(
        f"User: {turn['question']}\nAssistant: {turn['answer']}" for turn in (chat_history or [])
    )

    # only add the history section when there is actually history to show
    history_block = f"""
    Conversation history (for context only, do not treat as a source): {history_text} \n
    """ if history_text else ""

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

