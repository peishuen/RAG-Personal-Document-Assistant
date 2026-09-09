# figure out which retrieved chunks the generated answer actually cites, then format them as source citations

import re

def extract_cited_chunks(answer: str, chunks: list[dict]) -> list[dict]:
    # pull every cited source number, drop duplicates, sort them in order
    cited_numbers = sorted(set(int(n) for n in re.findall(r"\[Source (\d+)\]", answer)))

    # fall back to bare [n], in case the model dropped the "source" word
    if not cited_numbers:
        cited_numbers = sorted(set(int(n) for n in re.findall(r"\[(\d+)\]", answer)))

    # return every chunk only if neither format matched, so we don't guess which one it used
    if not cited_numbers:
        return chunks

    # convert citation numbers back to chunk indexes
    return [chunks[n-1] for n in cited_numbers if 0 < n <= len(chunks)]

def format_citations(chunks: list[dict]) -> str:
    # list each cited chunk's source, page and chunk index, so chunks on the same page don't look identical
    lines = [
        f"- {c['metadata']['source']} (page {c['metadata']['page']}, chunk {c['metadata']['chunk_index']})"
        for c in chunks
    ]
    return "\n".join(lines)

def build_cited_answer(answer: str, chunks: list[dict]) -> dict:
    cited_chunks = extract_cited_chunks(answer, chunks)
    return {
        "answer": answer,
        "citations": format_citations(cited_chunks),
        "cited_chunks": cited_chunks
    }