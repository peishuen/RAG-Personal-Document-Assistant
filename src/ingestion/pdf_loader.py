"""
This file reads a PDF and gets the text out of it.
It returns a list of pages, and each page has its text and some info
about where it came from (file name, page number, type).
It uses pymupdf4llm, which can handle multi-column pages (like research
papers) and keeps the text in the right reading order.
"""

import pymupdf4llm

from src.ingestion import text_cleaner

def load_pdf(file_path: str) -> list[dict]:
    # convert every page of the pdf into markdown text
    pdf_pages = pymupdf4llm.to_markdown(file_path, page_chunks=True)
    pages = []

    for i, pdf_page in enumerate(pdf_pages):
        # remove the markdown noise from the page text
        text = text_cleaner.clean_if_enabled(pdf_page["text"])

        # skip blank pages
        if not text or not text.strip():
            continue

        # store the text and where it came from
        pages.append({
            "text": text.strip(),
            "metadata": {
                "source": file_path,
                "page": i + 1,
                "type": "pdf"
            }
        })

    return pages
