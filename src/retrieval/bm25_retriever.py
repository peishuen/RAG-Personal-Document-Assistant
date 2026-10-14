"""
This file finds chunks using bm25, a keyword search method.
bm25 gives a higher score to chunks that share more words with the question,
so it works well when the question uses the same words as the document.
"""

from rank_bm25 import BM25Okapi
from src.vectorstore.chroma_store import get_collection

def load_chunks(collection_name: str = "documents") -> list[dict]:
    # get every stored chunk from chromadb, because bm25 needs all the text to build its index
    collection = get_collection(collection_name)
    result = collection.get(include=["documents", "metadatas"])

    return [
        {"text": text, "metadata": metadata}
        for text, metadata in zip(result["documents"], result["metadatas"])
    ]

def tokenize(text: str) -> list[str]:
    # lowercase and split on whitespace
    return text.lower().split()

# save the built index for each collection, together with the chunk count
# rebuild it only when the count changes (after an upload or delete), not on every search
_bm25_cache: dict[str, dict] = {}

def get_bm25_index(collection_name: str) -> tuple[list[dict], BM25Okapi | None]:
    collection = get_collection(collection_name)
    current_count = collection.count()

    # reuse the saved index if the chunk count is the same
    cached = _bm25_cache.get(collection_name)
    if cached and cached["count"] == current_count:
        return cached["chunks"], cached["bm25"]

    # build a new index from all the chunks
    chunks = load_chunks(collection_name)
    bm25 = BM25Okapi([tokenize(chunk["text"]) for chunk in chunks]) if chunks else None

    # save it for next time
    _bm25_cache[collection_name] = {"count": current_count, "chunks": chunks, "bm25": bm25}
    return chunks, bm25

def bm25_search(query: str, collection_name: str = "documents", top_k: int = 5, sources: list[str] | None = None) -> list[dict]:
    chunks, bm25 = get_bm25_index(collection_name)

    # return nothing if there are no chunks to search
    if not chunks or bm25 is None:
        return []

    # score every chunk against the question
    scores = bm25.get_scores(tokenize(query))

    # pair each chunk with its score, then keep only the chosen files, if any
    scored_chunks = list(zip(chunks, scores))
    if sources:
        scored_chunks = [(chunk, score) for chunk, score in scored_chunks if chunk["metadata"]["source"] in sources]

    # sort so the best score comes first
    scored_chunks.sort(key=lambda pair: pair[1], reverse=True)

    # keep only the top results
    results = []
    for chunk, score in scored_chunks[:top_k]:
        results.append({
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "score": float(score)
        })

    return results
