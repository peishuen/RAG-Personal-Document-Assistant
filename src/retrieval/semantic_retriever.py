# retrieve chunks from the chroma collection using semantic similarity search
# embeds the query with the same model used on the chunks, then finds the closest vectors in the store

from src.embeddings.embedder import get_dashscope_embedder
from src.vectorstore.chroma_store import get_collection

def semantic_search(query: str, collection_name: str = "documents", top_k: int = 5) -> list[dict]:
    embedder = get_dashscope_embedder()
    collection = get_collection(collection_name)

    # embed the query the same way chunks were embedded so they land in the same vector space
    query_vector = embedder.embed_query(query)

    result = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    # chroma nests results one level per query
    # unwrap index 0 since only one query is sent
    texts = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    results = []
    for text, metadata, distance in zip(texts, metadatas, distances):
        # convert cosine distance to similarity
        # a higher score means more relevant like bm25
        results.append({
            "text": text,
            "metadata": metadata,
            "score": 1 - distance
        })

    return results
