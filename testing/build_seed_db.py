# one-off local dev tool: embeds the sample docs into a clean, standalone chromadb
# folder (data/seed_chroma_db) containing ONLY the sample docs, which gets committed
# and shipped in the docker image. the backend copies it into the live data/chroma_db
# on startup if that's empty, so render never has to run ocr/embedding itself (that's
# what caused the OOM on the 512mb free tier) — re-run this manually whenever the
# sample docs themselves change, then commit the regenerated data/seed_chroma_db/

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

# rebuild from scratch each time so the seed never accumulates stale data
if os.path.exists(SEED_DIR):
    shutil.rmtree(SEED_DIR)

chunks = load_documents(SAMPLE_DOCS)
print(f"loaded and chunked {len(SAMPLE_DOCS)} sample doc(s) into {len(chunks)} chunks")

chunks = generate_embeddings(chunks)

client = chromadb.PersistentClient(path=SEED_DIR)
collection = client.create_collection(name="documents", metadata={"hnsw:space": "cosine"})

ids = [f"{c['metadata']['source']}_p{c['metadata']['page']}_c{c['metadata']['chunk_index']}" for c in chunks]
collection.add(
    ids=ids,
    embeddings=[c["embedding"] for c in chunks],
    documents=[c["text"] for c in chunks],
    metadatas=[c["metadata"] for c in chunks],
)

print(f"\ndone, {SEED_DIR} now has {collection.count()} chunks across {len(SAMPLE_DOCS)} doc(s)")
print("commit data/seed_chroma_db/ so render ships it in the image")
