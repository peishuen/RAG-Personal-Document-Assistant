"""
This file builds a separate evaluation database (data/eval_chroma_db), so the
evaluation never touches the chat app's own data in data/chroma_db.
It loads the 3 sample docs and every pdf or txt file in data/eval_docs, then builds
one collection for each chunking setup:
- "documents" uses the app's own chunk settings (this is what the main evaluation uses)
- "chunks_<size>_<overlap>" collections use other sizes (the ablation study compares them)
- "documents_clean_header" is the app's current setup: cleaned page text and a source header on each chunk
A collection that already has chunks is skipped, so the script can be run again safely.
Run it like this: python evaluation/build_eval_db.py
"""

import glob

import eval_env  # sets up the evaluation database and imports, so keep it before the src imports
import src.chunking.chunker as chunker
import src.ingestion.text_cleaner as text_cleaner
from src.ingestion.sample_docs import SAMPLE_DOCS
from src.ingestion.batch_loader import load_document
from src.ingestion.text_cleaner import clean_page_text
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection

EVAL_DOCS_DIR = "data/eval_docs"

# set the other chunk setups for the ablation study, as (chunk size, overlap) in characters
# the app itself uses 600/200 for pdfs, 800/100 for text files
CHUNK_CONFIGS = {
    "chunks_400_60": (400, 60),
    "chunks_1000_150": (1000, 150),
    "chunks_1500_200": (1500, 200),
}

# the app's current setup: its own chunk size, cleaned page text, and a source header on each chunk
CURRENT_SETUP = "documents_clean_header"

def list_eval_files() -> list[str]:
    # use the sample docs plus every pdf and txt file in the eval folder
    extra = sorted(glob.glob(f"{EVAL_DOCS_DIR}/*.pdf") + glob.glob(f"{EVAL_DOCS_DIR}/*.txt"))
    # use forward slashes, so the source names match the ids used in the question set
    return SAMPLE_DOCS + [path.replace("\\", "/") for path in extra]

def build_collection(name: str, pages: list[dict], size_and_overlap: tuple[int, int] | None,
                     clean: bool = False, header: bool = False) -> None:
    collection = get_collection(name)

    # skip the collection if it was built before
    if collection.count() > 0:
        print(f"{name}: already has {collection.count()} chunks, skipped")
        return

    # clean the markdown noise out of the page text, when this variant asks for it
    if clean:
        pages = [{**page, "text": clean_page_text(page["text"])} for page in pages]

    # swap in the chunk settings and the header switch for this collection, and always restore the app's own settings
    original_settings = chunker.CHUNK_SETTINGS
    original_header = chunker.ADD_CONTEXT_HEADER
    if size_and_overlap:
        size, overlap = size_and_overlap
        chunker.CHUNK_SETTINGS = {
            doc_type: {"chunk_size": size, "chunk_overlap": overlap}
            for doc_type in ("pdf", "text", "scanned")
        }
    chunker.ADD_CONTEXT_HEADER = header
    try:
        chunks = chunker.chunk_pages(pages)
    finally:
        chunker.CHUNK_SETTINGS = original_settings
        chunker.ADD_CONTEXT_HEADER = original_header

    print(f"{name}: embedding {len(chunks)} chunks...")
    chunks = generate_embeddings(chunks)
    store_chunks(chunks, name)
    print(f"{name}: stored {get_collection(name).count()} chunks")

if __name__ == "__main__":
    # load the raw pdf text, because the app now cleans by default and the variants below do their own cleaning
    text_cleaner.ENABLED = False

    files = list_eval_files()
    print(f"loading {len(files)} documents")

    # read every document once, and reuse the pages for every chunk setup
    pages = []
    for file_path in files:
        file_pages = load_document(file_path)
        print(f"  {file_path}: {len(file_pages)} pages")
        pages.extend(file_pages)

    # build the main collection with the app's own settings, then the ablation collections
    build_collection("documents", pages, None)
    for name, size_and_overlap in CHUNK_CONFIGS.items():
        build_collection(name, pages, size_and_overlap)
    build_collection(CURRENT_SETUP, pages, None, clean=True, header=True)

    print("\ndone, evaluation database is in data/eval_chroma_db")
