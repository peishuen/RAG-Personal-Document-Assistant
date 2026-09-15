# test a question that needs facts from more than one uploaded document
# checks that cross_document_search returns chunks from multiple sources and the generated answer covers both

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.cross_document import cross_document_search
from src.generation.generator import generate_answer

query = "What is HYDRO-3D, and what are the three use cases presented for this project?"

chunks = cross_document_search(query, top_k=5)

print("retrieved chunks by source:")
sources = set()
for c in chunks:
    source = c['metadata']['source']
    sources.add(source)
    print(f"- {source} (page {c['metadata']['page']}, chunk {c['metadata']['chunk_index']})")  

print(f"\nchunks came from {len(sources)} different documents(s)")

answer = generate_answer(query, chunks)
print(f"\nanswer:\n{answer}")