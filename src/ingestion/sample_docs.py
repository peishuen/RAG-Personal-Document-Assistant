"""
This file loads the sample documents into the vector database.
It loads, chunks, embeds and stores each sample doc, and skips any that are
already stored. Both the testing script and the backend startup use it, so an
empty database (like a fresh Render deploy) gets the sample docs automatically.
"""

from src.ingestion.batch_loader import load_documents
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection

# list the sample files that come with the app
SAMPLE_DOCS = [
    "data/sample_docs/OPV2V.pdf",
    "data/sample_docs/Final-Presentation-Slide.pdf",
    "data/sample_docs/Coop-Percep.txt",
]


def _already_stored(file_path: str, collection_name: str = "documents") -> bool:
    # check if any chunk from this file is already in the database
    collection = get_collection(collection_name)
    result = collection.get(where={"source": file_path}, limit=1)
    return len(result["ids"]) > 0


def ingest_sample_docs() -> int:
    # keep only the files that are not stored yet
    new_docs = [f for f in SAMPLE_DOCS if not _already_stored(f)]

    # return 0 when everything is already there
    if not new_docs:
        return 0

    # load and chunk, then turn the chunks into embeddings, then save them
    chunks = load_documents(new_docs)
    chunks = generate_embeddings(chunks)
    store_chunks(chunks)

    # return how many new chunks were stored

    return len(chunks)
