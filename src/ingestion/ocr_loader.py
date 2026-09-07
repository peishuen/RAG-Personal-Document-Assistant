# extract text from scanned image-based pdfs using ocr
# only use this when the pdf has no selectable text

import pytesseract
from PIL import Image
from pypdf import PdfReader
import io

# point pytesseract to the tesseract executable on windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def load_scanned_pdf(file_path: str) -> list[dict]:
    reader = PdfReader(file_path)
    pages = []

    for i, page in enumerate(reader.pages):
        # try extracting text the normal way first
        text = page.extract_text()

        # if no text found, fall back to ocr
        if not text or not text.strip():
            for image_file in page.images:
                # convert the embedded image to a format pillow can read
                image = Image.open(io.BytesIO(image_file.data))
                text = pytesseract.image_to_string(image)

        # skip if still nothing found
        if not text or not text.strip():
            continue

        pages.append({
            "text": text.strip(),
            "metadata": {
                "source": file_path,
                "page": i + 1,
                "type": "scanned"
            }
        })

    return pages