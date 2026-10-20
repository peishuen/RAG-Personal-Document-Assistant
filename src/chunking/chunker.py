"""
This file splits document pages into smaller pieces called chunks.
Small chunks are easier to embed and search than a whole page.
The chunk size changes with the document type, because clean pdf text and
noisy ocr text work best with different sizes.
It tries to split at paragraphs first, then sentences, then words, so each
chunk stays easy to read.
"""

import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

# set whether each chunk starts with a short header naming its file and page
# this helps search find chunks like a title slide, whose own text never names the document
# it raised MRR@5 from 0.864 to 0.889 in the ingestion comparison, a small gain (see evaluation/results/evaluation_report.md)
ADD_CONTEXT_HEADER = True

def build_header(metadata: dict) -> str:
    # turn "data/sample_docs/Final-Presentation-Slide.pdf" into "Final Presentation Slide"
    name = os.path.splitext(os.path.basename(metadata["source"]))[0].replace("-", " ").replace("_", " ")
    return f"Source: {name}, page {metadata['page']}\n"

# set the chunk size and overlap for each document type
# use the same small chunks for pdf and scanned, to keep the chunk numbers the same as before
# the evaluation questions and the seed database use those chunk numbers
# try bigger chunks for pdf (for example 1000 and 150) only when the evaluation is updated too
CHUNK_SETTINGS = {
    "pdf": {"chunk_size": 600, "chunk_overlap": 200},
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
            # add the header in front of the text, when it is switched on
            if ADD_CONTEXT_HEADER:
                chunk_text = build_header(page["metadata"]) + chunk_text

            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **page["metadata"],
                    "chunk_index": i,
                }
            })

    return chunks