"""
This file searches across all uploaded documents at once.
It makes sure one document does not take over all the results, by limiting
how many chunks can come from the same file.
This helps with questions that need facts from more than one document.
"""

import math

from src.retrieval.hybrid_ranker import hybrid_search

def cross_document_search(query: str, top_k: int = 5, candidate_k: int = 15, max_per_document: int = 2, sources: list[str] | None = None) -> list[dict]:
    # get a bigger pool of candidates first, so there is enough variety across documents
    candidates = hybrid_search(query, top_k=candidate_k, sources=sources)

    # raise the limit per document when only a few files are chosen
    # so we can still return enough results
    if sources:
        max_per_document = max(max_per_document, math.ceil(top_k / len(sources)))

    # go through the ranked candidates and limit how many come from the same file
    selected = []
    per_document_count = {}

    for chunk in candidates:
        source = chunk["metadata"]["source"]
        count = per_document_count.get(source, 0)

        # keep the chunk only if this file is under its limit
        if count < max_per_document:
            selected.append(chunk)
            per_document_count[source] = count + 1

        # stop when we have enough results
        if len(selected) == top_k:
            break

    return selected