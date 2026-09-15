# load and chunk multiple uploaded documents at once, picking the right loader based on file extension

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
        # tries normal text extraction first
        # only falls back to ocr on pages with no text
        return load_scanned_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def load_documents(file_paths: list[str]) -> list[dict]:
    # load and chunk every uploaded file so they can all be embedded and stored tgt
    all_chunks = []
    for file_path in file_paths:
        pages = load_document(file_path)
        all_chunks.extend(chunk_pages(pages))

    return all_chunks