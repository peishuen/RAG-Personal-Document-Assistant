# store chunk embeddings and metadata in chromadb so they can be searched later
# uses a persistent local store, so data survives between runs

import os
import shutil
import chromadb

# folder where chromadb saves its data on disk
PERSIST_DIR = "data/chroma_db"

# prebuilt, committed db containing only the sample docs (see testing/build_seed_db.py).
# copied into PERSIST_DIR on startup if it's empty, so a fresh container gets the sample
# docs without render having to run ocr/embedding itself at runtime (that's what caused
# an out-of-memory crash on the 512mb free tier)
SEED_DIR = "data/seed_chroma_db"


def seed_if_empty() -> bool:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    if os.listdir(PERSIST_DIR):
        return False  # already has data — either a prior seed or real uploads, leave it

    if not os.path.isdir(SEED_DIR) or not os.listdir(SEED_DIR):
        return False  # no seed shipped in this image, nothing to do

    shutil.copytree(SEED_DIR, PERSIST_DIR, dirs_exist_ok=True)
    return True

# cache the client so it only opens once per process
# opening a new client every call makes chromadb replay its unsaved write log each time, which is slow and noisy
_client = None

def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
    return _client

def get_collection(name: str = "documents"):
    # connect to (or create) a local persistent chromadb collection
    client = get_client()
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"} # cosine distance
    )
    return collection

# embed and metadata already attached to each chunk, just write them into the collection
def store_chunks(chunks: list[dict], collection_name: str = "documents"):
    collection = get_collection(collection_name)

    # chromadb needs a unique string id for every chunk
    # eg. data/sample_docs_OPV2V.pdf_p1_c0
    ids = [f"{c['metadata']['source']}_p{c['metadata']['page']}_c{c['metadata']['chunk_index']}" for c in chunks]
    texts = [c['text'] for c in chunks]
    embeddings = [c['embedding'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )

    return collection

# group stored chunks by source file so the ui can show what's been ingested
def list_sources(collection_name: str = "documents") -> list[dict]:
    collection = get_collection(collection_name)
    result = collection.get(include=["metadatas"])

    sources = {}
    for metadata in result["metadatas"]:
        source = metadata["source"]
        entry = sources.setdefault(source, {"source": source, "chunk_count": 0, "pages": set(), "type": metadata["type"]})
        entry["chunk_count"] += 1
        entry["pages"].add(metadata["page"])

    return [
        {
            "source": entry["source"],
            "chunk_count": entry["chunk_count"],
            "page_count": len(entry["pages"]),
            "type": entry["type"]
        }
        for entry in sorted(sources.values(), key=lambda e: e["source"])
    ]

# remove every chunk belonging to a source file from the collection
def delete_source(source: str, collection_name: str = "documents"):
    collection = get_collection(collection_name)
    collection.delete(where={"source": source})