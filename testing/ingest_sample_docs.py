# load, chunk, embed and store every sample doc into the same chromadb collection

import sys
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.ingestion.batch_loader import load_documents
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection

def already_stored(file_path: str, collection_name: str = "documents") -> bool:
    # check if any chunk from this file is already in the collection so re-running this script does not re-embed it
    collection = get_collection(collection_name)
    result = collection.get(where={"source": file_path}, limit=1)
    return len(result["ids"]) > 0

# any num of files, any mix of pdf and text, no per-file loader mapping needed
sample_docs = [
    "data/sample_docs/OPV2V.pdf",
    "data/sample_docs/Final-Presentation-Slide.pdf",
    "data/sample_docs/Coop-Percep.txt"
]

new_docs = [f for f in sample_docs if not already_stored(f)]

if not new_docs:
    print("all sample docs already stored, nothing to do")
else:
    chunks = load_documents(new_docs)
    print(f"loaded and chunked {len(new_docs)} new document(s) into {len(chunks)} chunks")

    chunks = generate_embeddings(chunks)
    store_chunks(chunks)

collection = get_collection()
print(f'\ndone, collection now has {collection.count()} chunks total')