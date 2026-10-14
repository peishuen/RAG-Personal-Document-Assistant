"""
This file loads and chunks many uploaded documents in one go.
It looks at each file extension (.txt or .pdf) to pick the right loader,
then splits the pages into smaller chunks ready for embedding.
"""

import os
from src.ingestion.text_loader import load_text
from src.ingestion.ocr_loader import load_scanned_pdf
from src.chunking.chunker import chunk_pages

def load_document(file_path: str) -> list[dict]:
    # pick the loader based on file extension
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        return load_text(file_path)
    elif ext == ".pdf":
        # try normal text extraction first, then use ocr only on pages with no text
        return load_scanned_pdf(file_path)
    else:
        # stop early if the file type is not supported
        raise ValueError(f"Unsupported file type: {ext}")

def load_documents(file_paths: list[str]) -> list[dict]:
    # collect the chunks from every file into one list
    all_chunks = []
    for file_path in file_paths:
        pages = load_document(file_path)
        all_chunks.extend(chunk_pages(pages))

    return all_chunks