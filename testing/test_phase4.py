"""
This file runs the full pipeline on one pdf.
It embeds the chunks, stores them in chromadb, then tests a similarity search.
"""

import sys
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# load the api key from the .env file
load_dotenv()

from src.ingestion.pdf_loader import load_pdf
from src.chunking.chunker import chunk_pages
from src.embeddings.embedder import generate_embeddings, get_dashscope_embedder
from src.vectorstore.chroma_store import store_chunks, get_collection

# load and chunk a sample pdf
pages = load_pdf("data/sample_docs/OPV2V.pdf")
chunks = chunk_pages(pages)
print(f"loaded and chunked: {len(chunks)} chunks")

# generate embeddings for every chunk
chunks = generate_embeddings(chunks)
print(f"embeddings generated for all chunks")

# store the chunks in chromadb
collection = store_chunks(chunks)
print(f'stored in chromadb, collection now has {collection.count()} chunks')

# test the search by embedding a question and finding the closest chunks
embedder = get_dashscope_embedder()
query = "What is vehicle-to-vehicle communication used for?"
query_vector = embedder.embed_query(query)

results = collection.query(
    query_embeddings=[query_vector],
    n_results=3
)

# print the top 3 matches
print()
print(f'query: {query}')
print('top 3 matches:')
for i, (doc, meta, distance) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
    print(f"\n{i+1}. (page {meta['page']}, distance {distance:.4f})")
    print(doc[:200])