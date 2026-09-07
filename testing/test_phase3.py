# test chunking on each document type and check the chunk boundaries look reasonable

import sys
import os

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.pdf_loader import load_pdf
from src.ingestion.text_loader import load_text
from src.ingestion.ocr_loader import load_scanned_pdf
from src.chunking.chunker import chunk_pages

# load and chunk the pdf
pdf_pages = load_pdf("data/sample_docs/OPV2V.pdf")
pdf_chunks = chunk_pages(pdf_pages)
print(f"pdf: {len(pdf_pages)} pages -> {len(pdf_chunks)} chunks")
print("sample chunk:", pdf_chunks[0]["text"][:200])
print()

# load and chunk the text file
text_pages = load_text("data/sample_docs/Coop-Percep.txt")
text_chunks = chunk_pages(text_pages)
print(f"text: {len(text_pages)} pages -> {len(text_chunks)} chunks")
print("sample chunk:", text_chunks[0]["text"][:200])
print()

# load and chunk the scanned pdf
scanned_pages = load_scanned_pdf("data/sample_docs/Final-Presentation-Slide.pdf")
scanned_chunks = chunk_pages(scanned_pages)
print(f"scaned: {len(scanned_pages)} pages -> {len(scanned_chunks)} chunks")
print("sample chunk:", scanned_chunks[0]["text"][:200])