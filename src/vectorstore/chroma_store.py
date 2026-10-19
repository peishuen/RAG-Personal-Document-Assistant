"""
This file saves chunk embeddings and their info in chromadb, a vector database,
so we can search them later.
The data is saved on disk, so it is still there after the app restarts.
It also has helpers to list the stored documents, delete one, and copy
the prebuilt sample database on the first start.
"""

import os
import shutil
import chromadb

# set the folder where chromadb saves its data on disk
# the evaluation scripts set CHROMA_DIR to use their own database, so the app's data stays untouched
PERSIST_DIR = os.getenv("CHROMA_DIR", "data/chroma_db")

# set the folder of the prebuilt database that only has the sample docs
# copy it into PERSIST_DIR on startup when that folder is empty
# do this to avoid running ocr and embedding on render, which ran out of memory on the free tier
# see testing/build_seed_db.py for how it is built
SEED_DIR = "data/seed_chroma_db"


def seed_if_empty() -> bool:
    # make sure the data folder exists
    os.makedirs(PERSIST_DIR, exist_ok=True)

    # stop if there is already data, so we do not overwrite it
    if os.listdir(PERSIST_DIR):
        return False

    # stop if there is no seed database to copy
    if not os.path.isdir(SEED_DIR) or not os.listdir(SEED_DIR):
        return False

    # copy the seed database into the data folder
    shutil.copytree(SEED_DIR, PERSIST_DIR, dirs_exist_ok=True)
    return True

# keep one client for the whole app, so it only opens once
# a new client each time is slow and noisy, because chromadb replays its unsaved log
_client = None

def get_client():
    global _client
    # open the client only the first time
    if _client is None:
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
    return _client

def get_collection(name: str = "documents"):
    # open the collection, or create it if it does not exist
    client = get_client()
    collection = client.get_or_create_collection(
        name=name,
        # measure similarity with cosine distance
        metadata={"hnsw:space": "cosine"}
    )
    return collection

# save the chunks (text, embedding and metadata) into the collection
def store_chunks(chunks: list[dict], collection_name: str = "documents"):
    collection = get_collection(collection_name)

    # build a unique id for every chunk, because chromadb needs one
    # for example: data/sample_docs/OPV2V.pdf_p1_c0
    ids = [f"{c['metadata']['source']}_p{c['metadata']['page']}_c{c['metadata']['chunk_index']}" for c in chunks]
    texts = [c['text'] for c in chunks]
    embeddings = [c['embedding'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]

    # write everything into the collection
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )

    return collection

# group the stored chunks by file, so the ui can show what was uploaded
def list_sources(collection_name: str = "documents") -> list[dict]:
    collection = get_collection(collection_name)
    result = collection.get(include=["metadatas"])

    sources = {}
    for metadata in result["metadatas"]:
        source = metadata["source"]
        # create an entry for a new file, or reuse the existing one
        entry = sources.setdefault(source, {"source": source, "chunk_count": 0, "pages": set(), "type": metadata["type"]})
        entry["chunk_count"] += 1
        entry["pages"].add(metadata["page"])

    # return the files sorted by name, with page counts instead of page sets
    return [
        {
            "source": entry["source"],
            "chunk_count": entry["chunk_count"],
            "page_count": len(entry["pages"]),
            "type": entry["type"]
        }
        for entry in sorted(sources.values(), key=lambda e: e["source"])
    ]

# delete every chunk that came from one file
def delete_source(source: str, collection_name: str = "documents"):
    collection = get_collection(collection_name)
    collection.delete(where={"source": source})