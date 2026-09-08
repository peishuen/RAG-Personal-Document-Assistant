# load, chunk, embed and store every sample doc into the same chromadb collection

import sys
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.ingestion.pdf_loader import load_pdf
from src.ingestion.text_loader import load_text
from src.ingestion.ocr_loader import load_scanned_pdf
from src.chunking.chunker import chunk_pages
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection

def already_stored(file_path: str, collection_name: str = "documents") -> bool:
    # check if any chunk from this file is already in the collection
    collection = get_collection(collection_name)
    result = collection.get(
        where={"source": file_path},
        limit=1
    )
    return len(result["ids"]) > 0

# every sample doc to ingest
sample_docs = [
    ("data/sample_docs/OPV2V.pdf", load_pdf),
    ("data/sample_docs/Final-Presentation-Slide.pdf", load_scanned_pdf),
    ("data/sample_docs/Coop-Percep.txt", load_text)
]

for file_path, loader in sample_docs:
    if already_stored(file_path):
        continue

    # load and chunk this document
    pages = loader(file_path)
    chunks = chunk_pages(pages)
    print(f"{file_path}: loaded and chunked into {len(chunks)} chunks")

    # embed and store the chunks
    chunks = generate_embeddings(chunks)
    store_chunks(chunks)

    collection = get_collection()
    print(f'\n done, collection now has {collection.count()} chunks total')