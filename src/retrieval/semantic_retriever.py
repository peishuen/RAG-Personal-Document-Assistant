"""
This file finds chunks by meaning, not by exact words.
It turns the question into an embedding with the same model used for the chunks,
then looks for the chunks whose embeddings are closest to it.
"""

from src.embeddings.embedder import get_dashscope_embedder
from src.vectorstore.chroma_store import get_collection

def semantic_search(query: str, collection_name: str = "documents", top_k: int = 5, sources: list[str] | None = None) -> list[dict]:
    embedder = get_dashscope_embedder()
    collection = get_collection(collection_name)

    # embed the question the same way as the chunks, so they can be compared
    query_vector = embedder.embed_query(query)

    # set up the search options
    query_kwargs = {
        "query_embeddings": [query_vector],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }

    # search only inside the chosen files, if any were given
    if sources:
        query_kwargs["where"] = {"source": {"$in": sources}}

    # run the search
    result = collection.query(**query_kwargs)

    # take the first item of each list, because chroma wraps results per question
    # and we only sent one question
    texts = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    results = []
    for text, metadata, distance in zip(texts, metadatas, distances):
        # turn distance into similarity, so a higher score means more relevant (same as bm25)
        results.append({
            "text": text,
            "metadata": metadata,
            "score": 1 - distance
        })

    return results
