# test each loader against a sample document to confirm text is extracted correctly

import sys
import os

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.pdf_loader import load_pdf
from src.ingestion.text_loader import load_text
from src.ingestion.ocr_loader import load_scanned_pdf

# test pdf loader
pdf_pages = load_pdf("data/sample_docs/OPV2V.pdf")
print(f"pdf loader: {len(pdf_pages)} pages loaded")
print("first page preview:", pdf_pages[0]["text"][:200])
print()

# test text loader
text_pages = load_text("data/sample_docs/Coop-Percep.txt")
print(f"text loader: {len(text_pages)} pages loaded")
print("preview:", text_pages[0]["text"][:200])
print()

# test ocr loader
scanned_pages = load_scanned_pdf("data/sample_docs/Final-Presentation-Slide.pdf")
print(f"ocr loader: {len(scanned_pages)} pages loaded")
print("first page preview:", scanned_pages[0]["text"][:200])