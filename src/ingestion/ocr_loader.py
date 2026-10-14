"""
This file reads text from scanned pdfs (pdfs that are really just images).
It uses OCR (a tool that reads text from pictures) when a page has no real text.
Pages that already have selectable text go through pymupdf4llm first, which
handles multi-column layouts and keeps the correct reading order.
"""

import platform
import shutil
import pymupdf4llm
import pytesseract
from PIL import Image
from pypdf import PdfReader
import io

# set the tesseract path by hand on windows, because it is not on PATH by default
# skip this on linux (render, docker), where apt-get already puts tesseract on PATH
if platform.system() == "Windows" and shutil.which("tesseract") is None:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def _ocr_image(image):
    # run ocr with the default mode, which expects one neat block of text
    text = pytesseract.image_to_string(image)
    # retry with sparse mode (psm 11) to find scattered text on busy images
    if not text or not text.strip():
        text = pytesseract.image_to_string(image, config="--psm 11")
    return text

def load_scanned_pdf(file_path: str) -> list[dict]:
    # open the pdf with pypdf, only to pull out images for the ocr fallback below
    reader = PdfReader(file_path)
    pdf_pages = pymupdf4llm.to_markdown(file_path, page_chunks=True)
    pages = []

    for i, pdf_page in enumerate(pdf_pages):
        # try to get the text the normal way first
        text = pdf_page["text"]

        # use ocr on the page images if no text was found
        if not text or not text.strip():
            ocr_texts = []
            for image_file in reader.pages[i].images:
                # convert the embedded image to a format pillow can read
                image = Image.open(io.BytesIO(image_file.data))
                ocr_text = _ocr_image(image)
                if ocr_text and ocr_text.strip():
                    ocr_texts.append(ocr_text.strip())
            text = "\n\n".join(ocr_texts)

        # skip the page if there is still no text
        if not text or not text.strip():
            continue

        # store the text and where it came from
        pages.append({
            "text": text.strip(),
            "metadata": {
                "source": file_path,
                "page": i + 1,
                "type": "scanned"
            }
        })

    return pages
