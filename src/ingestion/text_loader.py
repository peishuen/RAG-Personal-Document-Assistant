"""
This file reads plain text (.txt) or markdown files.
It returns the content together with some info about where it came from.
The output has the same shape as the pdf loader, so the rest of the
pipeline can treat both the same way.
"""

def load_text(file_path: str) -> list[dict]:
    # read the entire file as one block
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # wrap in a list to match the same format as the pdf loader
    return [{
        "text": text.strip(),
        "metadata": {
            "source": file_path,
            "page": 1,
            "type": "text"
        }
    }]