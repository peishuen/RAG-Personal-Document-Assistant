# search across every uploaded document and make sure results are not dominated by just one of them
# useful for questions that need facts pulled from more than one document at once

from src.retrieval.hybrid_ranker import hybrid_search

def cross_document_search(query: str, top_k: int = 5, candidate_k: int = 15, max_per_document: int = 2) -> list[dict]:
    # pull a larger candidate pool first
    # so there is enough variety to pick from across documents
    candidates = hybrid_search(query, top_k=candidate_k)

    # walk the ranked candidates and cap how many chunks come from the same source document
    selected = []
    per_document_count = {}

    for chunk in candidates:
        source = chunk["metadata"]["source"]
        count = per_document_count.get(source, 0)

        if count < max_per_document:
            selected.append(chunk)
            per_document_count[source] = count + 1

        if len(selected) == top_k:
            break

    return selected