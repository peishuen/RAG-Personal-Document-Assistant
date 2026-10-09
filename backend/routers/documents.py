# *** documents router: upload new files, list what's stored, delete a document ***
import hashlib
import os

from fastapi import APIRouter, UploadFile, File

from src.ingestion.batch_loader import load_document
from src.chunking.chunker import chunk_pages
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection, list_sources, delete_source

router = APIRouter()
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def already_stored(content_hash: str) -> bool:
    # same content-hash dedup app.py used, so re-uploads under a new filename are still caught
    result = get_collection().get(where={"content_hash": content_hash}, limit=1)
    return len(result["ids"]) > 0


@router.get("")
def get_documents():
    return list_sources()


@router.post("")
async def upload_documents(files: list[UploadFile] = File(...)):
    stored, skipped = [], []
    new_chunks = []
    seen_hashes = set()

    for upload in files:
        file_bytes = await upload.read()
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        file_path = os.path.join(UPLOAD_DIR, upload.filename).replace(os.sep, "/")

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        if content_hash in seen_hashes or already_stored(content_hash):
            skipped.append(upload.filename)
            continue

        seen_hashes.add(content_hash)
        pages = load_document(file_path)
        chunks = chunk_pages(pages)
        for chunk in chunks:
            chunk["metadata"]["content_hash"] = content_hash
        new_chunks.extend(chunks)
        stored.append(upload.filename)

    if new_chunks:
        new_chunks = generate_embeddings(new_chunks)
        store_chunks(new_chunks)

    return {"stored": stored, "skipped": skipped}


@router.delete("/{source:path}")
def remove_document(source: str):
    delete_source(source)
    if os.path.exists(source) and os.path.abspath(source).startswith(os.path.abspath(UPLOAD_DIR)):
        os.remove(source)
    return {"deleted": source}
