# retrieve chunks from the chroma collection using bm25 keyword scoring
# bm25 ranks chunks by term overlap with the query, so it works well when the question shares exact words with the source text  

from rank_bm25 import BM25Okapi
from src.vectorstore.chroma_store import get_collection

def load_chunks(collection_name: str = "documents") -> list[dict]:
    # pull every stored chunk back out of chromadb, bm25 needs the full text set to build its index
    collection = get_collection(collection_name)
    result = collection.get(include=["documents", "metadatas"])

    chunks = []
    for text, metadata in zip(result["documents"], result["metadatas"]):
        chunks.append({
            "text": text,
            "metadata": metadata
        })

    return chunks 

def tokenize(text: str) -> list[str]:
    # lowercase and split on whitespace
    return text.lower().split()

def bm25_search(query: str, collection_name: str = "documents", top_k: int = 5) -> list[dict]:
    chunks = load_chunks(collection_name)

    # rebuild the index on every call since the chunk set is small right now, revisit if this gets slow
    tokenized_corpus = [tokenize(chunk['text']) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    # pair each chunk with its score then keep the top_k highest scoring ones
    scored_chunks = list(zip(chunks, scores))
    scored_chunks.sort(key=lambda pair: pair[1], reverse=True) 

    results = []
    for chunk, score in scored_chunks[:top_k]:
        results.append({
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "score": float(score)
        })

    return results