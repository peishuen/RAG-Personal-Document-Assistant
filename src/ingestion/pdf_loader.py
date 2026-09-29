# load and extract text from pdf files, return a list of pages with metadata
# uses pymupdf4llm, which detects multi-column layouts (common in research papers)
# automatically and returns each page's text in the correct reading order

import pymupdf4llm

def load_pdf(file_path: str) -> list[dict]:
    pdf_pages = pymupdf4llm.to_markdown(file_path, page_chunks=True)
    pages = []

    for i, pdf_page in enumerate(pdf_pages):
        text = pdf_page["text"]

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
