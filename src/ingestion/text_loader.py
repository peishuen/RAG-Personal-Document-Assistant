# load plain text or markdown files, return content with metadata

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