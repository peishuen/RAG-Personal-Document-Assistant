# load and extract text from pdf files, return a list of pages with metadata

from pypdf import PdfReader

def load_pdf(file_path: str) -> list[dict]:
    # open the pdf file
    reader = PdfReader(file_path)
    pages = []

    # loop through each page and extract text
    for i, page in enumerate(reader.pages):
        text = page.extract_text()

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