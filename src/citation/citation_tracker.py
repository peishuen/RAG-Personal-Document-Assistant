"""
This file finds which chunks the answer really cites, like [Source 1].
Then it turns those chunks into a readable list of sources,
with the file name, page and chunk number.
"""

import re

def extract_cited_chunks(answer: str, chunks: list[dict]) -> list[dict]:
    # find every cited source number, remove duplicates and sort them
    cited_numbers = sorted(set(int(n) for n in re.findall(r"\[Source (\d+)\]", answer)))

    # try the short form [n] if the model left out the word "source"
    if not cited_numbers:
        cited_numbers = sorted(set(int(n) for n in re.findall(r"\[(\d+)\]", answer)))

    # return all chunks if no citation was found, because we cannot guess which ones were used
    if not cited_numbers:
        return chunks

    # turn citation numbers into chunks (numbers start at 1, lists start at 0)
    return [chunks[n-1] for n in cited_numbers if 0 < n <= len(chunks)]

# turn cited chunks into a readable list of source, page and chunk number
def format_citations(chunks: list[dict]) -> str:
    # write one line per chunk, and include the chunk number so chunks on the same page look different
    lines = [
        f"- {c['metadata']['source']} (page {c['metadata']['page']}, chunk {c['metadata']['chunk_index']})"
        for c in chunks
    ]
    return "\n".join(lines)

# put the answer and its citations together in one result
def build_cited_answer(answer: str, chunks: list[dict]) -> dict:
    cited_chunks = extract_cited_chunks(answer, chunks)
    return {
        "answer": answer,
        "citations": format_citations(cited_chunks),
        "cited_chunks": cited_chunks
    }