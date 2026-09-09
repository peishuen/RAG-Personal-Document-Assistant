# build the prompt that gives the llm the question plus the retrieved chunks as context
# tells the model to answer only from the context, so it stays grounded instead of making things up
# also tells it to cite which source it used, so citation_tracker can trace the answer back to a chunk

def build_prompt(query: str, chunks: list[dict]) -> str:
    # number each chunk so the model can point back to a specific source
    context = "\n\n".join(
        f"[{i+1}] (source: {c['metadata']['source']}, page {c['metadata']['page']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    return f"""
    Answer the question using only the context below. 
    Cite the source you used in square brackets, like [Source 1], right after any information you use from it.
    If the context does not contain the answer, say you don't know.
    
    Context:
    {context}

    Question: {query}

    Answer:
    """

