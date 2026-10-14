# manual entrypoint for seeding the sample docs into chromadb (the same logic the
# backend runs automatically on startup — see src/ingestion/sample_docs.py)

import sys
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.ingestion.sample_docs import ingest_sample_docs
from src.vectorstore.chroma_store import get_collection

stored = ingest_sample_docs()

if stored == 0:
    print("all sample docs already stored, nothing to do")
else:
    print(f"stored {stored} new chunk(s)")

collection = get_collection()
print(f'\ndone, collection now has {collection.count()} chunks total')
