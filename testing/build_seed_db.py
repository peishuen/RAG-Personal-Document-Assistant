"""
This file builds the seed database, a small chromadb folder (data/seed_chroma_db)
that only has the sample docs.
The folder is committed and shipped in the docker image. The backend copies it
into data/chroma_db on startup if that folder is empty, so render does not need
to run ocr and embedding itself (this ran out of memory on the free tier).
Run this file by hand whenever the sample docs change, then commit the new folder.
"""

import sys
import os
import shutil
import chromadb
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.ingestion.sample_docs import SAMPLE_DOCS
from src.ingestion.batch_loader import load_documents
from src.embeddings.embedder import generate_embeddings

SEED_DIR = "data/seed_chroma_db"

# delete the old seed folder first, so no old data is left behind
if os.path.exists(SEED_DIR):
    shutil.rmtree(SEED_DIR)

# load and chunk the sample docs
chunks = load_documents(SAMPLE_DOCS)
print(f"loaded and chunked {len(SAMPLE_DOCS)} sample doc(s) into {len(chunks)} chunks")

# turn the chunks into embeddings
chunks = generate_embeddings(chunks)

# create a new database with cosine similarity
client = chromadb.PersistentClient(path=SEED_DIR)
collection = client.create_collection(name="documents", metadata={"hnsw:space": "cosine"})

# build the same chunk ids used in chroma_store.py, then save everything
ids = [f"{c['metadata']['source']}_p{c['metadata']['page']}_c{c['metadata']['chunk_index']}" for c in chunks]
collection.add(
    ids=ids,
    embeddings=[c["embedding"] for c in chunks],
    documents=[c["text"] for c in chunks],
    metadatas=[c["metadata"] for c in chunks],
)

print(f"\ndone, {SEED_DIR} now has {collection.count()} chunks across {len(SAMPLE_DOCS)} doc(s)")
print("commit data/seed_chroma_db/ so render ships it in the image")
