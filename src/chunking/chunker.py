"""
This file splits document pages into smaller pieces called chunks.
Small chunks are easier to embed and search than a whole page.
The chunk size changes with the document type, because clean pdf text and
noisy ocr text work best with different sizes.
It tries to split at paragraphs first, then sentences, then words, so each
chunk stays easy to read.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

# set the chunk size and overlap for each document type
# use bigger chunks with less overlap for pdf, because the text is usually clean
# use smaller chunks with more overlap for ocr, because the text is noisier
CHUNK_SETTINGS = {
    "pdf": {"chunk_size": 1000, "chunk_overlap": 150},
    "text": {"chunk_size": 800, "chunk_overlap": 100},
    "scanned": {"chunk_size": 600, "chunk_overlap": 200}
}

# split in this order: paragraph, line, sentence, word, then single character
# follow this order to avoid cutting a sentence in the middle when possible
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]

# turn each page into a list of chunks and keep the page info on every chunk
def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks = []

    for page in pages:
        doc_type = page["metadata"]["type"]

        # pick the settings for this document type, and use pdf settings if the type is unknown
        settings = CHUNK_SETTINGS.get(doc_type, CHUNK_SETTINGS["pdf"])

        # create the splitter with those settings
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings["chunk_size"],
            chunk_overlap=settings["chunk_overlap"],
            separators=SEPARATORS
        )

        # split the page text into smaller pieces
        page_chunks = splitter.split_text(page["text"])

        # copy the page info onto every chunk to keep track of the source
        for i, chunk_text in enumerate(page_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **page["metadata"],
                    "chunk_index": i,
                }
            })

    return chunks