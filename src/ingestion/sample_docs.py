# load, chunk, embed and store every sample doc into the collection, skipping any
# already stored — shared by the standalone testing script and the backend startup hook
# so a fresh (empty) chroma_db, like the one every new Render deploy starts with, gets
# the sample docs seeded automatically

from src.ingestion.batch_loader import load_documents
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection

SAMPLE_DOCS = [
    "data/sample_docs/OPV2V.pdf",
    "data/sample_docs/Final-Presentation-Slide.pdf",
    "data/sample_docs/Coop-Percep.txt",
]


def _already_stored(file_path: str, collection_name: str = "documents") -> bool:
    collection = get_collection(collection_name)
    result = collection.get(where={"source": file_path}, limit=1)
    return len(result["ids"]) > 0


def ingest_sample_docs() -> int:
    # returns the number of new chunks stored (0 if everything was already there)
    new_docs = [f for f in SAMPLE_DOCS if not _already_stored(f)]

    if not new_docs:
        return 0

    chunks = load_documents(new_docs)
    chunks = generate_embeddings(chunks)
    store_chunks(chunks)

    return len(chunks)
