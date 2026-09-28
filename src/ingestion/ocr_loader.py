# extract text from scanned image-based pdfs using ocr
# only use this when the pdf has no selectable text

import pytesseract
from PIL import Image
from pypdf import PdfReader
import io

# point pytesseract to the tesseract executable on windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def _ocr_image(image):
    # default page segmentation assumes a uniform block of text, which
    # misses sparse text sitting on a busy photo/diagram background
    text = pytesseract.image_to_string(image)
    if not text or not text.strip():
        text = pytesseract.image_to_string(image, config="--psm 11")
    return text

def load_scanned_pdf(file_path: str) -> list[dict]:
    reader = PdfReader(file_path)
    pages = []

    for i, page in enumerate(reader.pages):
        # try extracting text the normal way first
        text = page.extract_text()

        # if no text found, fall back to ocr
        if not text or not text.strip():
            ocr_texts = []
            for image_file in page.images:
                # convert the embedded image to a format pillow can read
                image = Image.open(io.BytesIO(image_file.data))
                ocr_text = _ocr_image(image)
                if ocr_text and ocr_text.strip():
                    ocr_texts.append(ocr_text.strip())
            text = "\n\n".join(ocr_texts)

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