# store chunk embeddings and metadata in chromadb so they can be searched later
# uses a persistent local store, so data survives between runs

import chromadb

# folder where chromadb saves its data on disk
PERSIST_DIR = "data/chroma_db"

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