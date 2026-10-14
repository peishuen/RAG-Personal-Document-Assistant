"""
This file handles the documents api.
It lets the user upload new files, see the stored files, and delete a file.
Each upload goes through load, chunk, embed and store.
"""
import hashlib
import os

from fastapi import APIRouter, UploadFile, File

from src.ingestion.batch_loader import load_document
from src.chunking.chunker import chunk_pages
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection, list_sources, delete_source

router = APIRouter()
# set the folder for uploaded files, and create it if it is missing
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def already_stored(content_hash: str) -> bool:
    # check the file content (not the name), so the same file under a new name is still caught
    result = get_collection().get(where={"content_hash": content_hash}, limit=1)
    return len(result["ids"]) > 0


# return the list of stored documents
@router.get("")
def get_documents():
    return list_sources()


# receive uploaded files and add the new ones to the database
@router.post("")
async def upload_documents(files: list[UploadFile] = File(...)):
    stored, skipped = [], []
    new_chunks = []
    seen_hashes = set()

    for upload in files:
        file_bytes = await upload.read()
        # make a fingerprint (hash) of the file content to spot duplicates
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        file_path = os.path.join(UPLOAD_DIR, upload.filename).replace(os.sep, "/")

        # save the file to disk
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # skip the file if it was uploaded before or appears twice in this upload
        if content_hash in seen_hashes or already_stored(content_hash):
            skipped.append(upload.filename)
            continue

        # read the file and split it into chunks
        seen_hashes.add(content_hash)
        pages = load_document(file_path)
        chunks = chunk_pages(pages)
        # add the hash to every chunk, so we can spot duplicates later
        for chunk in chunks:
            chunk["metadata"]["content_hash"] = content_hash
        new_chunks.extend(chunks)
        stored.append(upload.filename)

    # embed and store all new chunks together
    if new_chunks:
        new_chunks = generate_embeddings(new_chunks)
        store_chunks(new_chunks)

    return {"stored": stored, "skipped": skipped}


# delete a document from the database, and from disk if it is an uploaded file
@router.delete("/{source:path}")
def remove_document(source: str):
    delete_source(source)
    # remove the file only if it sits inside the uploads folder, so sample docs stay safe
    if os.path.exists(source) and os.path.abspath(source).startswith(os.path.abspath(UPLOAD_DIR)):
        os.remove(source)
    return {"deleted": source}
