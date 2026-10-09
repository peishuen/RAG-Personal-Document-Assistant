# retrieve chunks from the chroma collection using bm25 keyword scoring
# bm25 ranks chunks by term overlap with the query, so it works well when the question shares exact words with the source text

from rank_bm25 import BM25Okapi
from src.vectorstore.chroma_store import get_collection

def load_chunks(collection_name: str = "documents") -> list[dict]:
    # pull every stored chunk back out of chromadb, bm25 needs the full text set to build its index
    collection = get_collection(collection_name)
    result = collection.get(include=["documents", "metadatas"])

    return [
        {"text": text, "metadata": metadata}
        for text, metadata in zip(result["documents"], result["metadatas"])
    ]

def tokenize(text: str) -> list[str]:
    # lowercase and split on whitespace
    return text.lower().split()

# cache the built index per collection, keyed by chunk count, so an upload or delete still
# invalidates it correctly but a plain search just reuses it instead of rebuilding every time
_bm25_cache: dict[str, dict] = {}

def get_bm25_index(collection_name: str) -> tuple[list[dict], BM25Okapi | None]:
    collection = get_collection(collection_name)
    current_count = collection.count()

    cached = _bm25_cache.get(collection_name)
    if cached and cached["count"] == current_count:
        return cached["chunks"], cached["bm25"]

    chunks = load_chunks(collection_name)
    bm25 = BM25Okapi([tokenize(chunk["text"]) for chunk in chunks]) if chunks else None

    _bm25_cache[collection_name] = {"count": current_count, "chunks": chunks, "bm25": bm25}
    return chunks, bm25

def bm25_search(query: str, collection_name: str = "documents", top_k: int = 5, sources: list[str] | None = None) -> list[dict]:
    chunks, bm25 = get_bm25_index(collection_name)

    if not chunks or bm25 is None:
        return []

    scores = bm25.get_scores(tokenize(query))

    # score against the full cached corpus, then narrow down to the requested scope, if any
    scored_chunks = list(zip(chunks, scores))
    if sources:
        scored_chunks = [(chunk, score) for chunk, score in scored_chunks if chunk["metadata"]["source"] in sources]

    scored_chunks.sort(key=lambda pair: pair[1], reverse=True)

    results = []
    for chunk, score in scored_chunks[:top_k]:
        results.append({
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "score": float(score)
        })

    return results
