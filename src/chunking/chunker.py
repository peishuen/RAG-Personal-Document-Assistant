# split document pages into smaller chunks for embedding and retrieval
# chunk size adjusts based on document type since dense pdfs and ocr text behave differently
# splitting tries paragraphs first, then sentences, then words, so chunks stay readable

from langchain_text_splitters import RecursiveCharacterTextSplitter

# default chunk settings per document type
# pdf text is usually clean, so bigger chunks with less overlap work fine
# ocr text is noisier, so smaller chunks with more overlap help catch broken sentences
CHUNK_SETTINGS = {
    "pdf": {"chunk_size": 1000, "chunk_overlap": 150},
    "text": {"chunk_size": 800, "chunk_overlap": 100},
    "scanned": {"chunk_size": 600, "chunk_overlap": 200}
}

# split order: paragraph break, line break, sentence end, word, then character as last resort
# this keeps chunks from cutting off mid-sentence whenever possible
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " " ""]

def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks = []

    for page in pages:
        doc_type = page["metadata"]["type"]

        # pick chunk size settings based on the document type, fallback to pdf settings
        settings = CHUNK_SETTINGS.get(doc_type, CHUNK_SETTINGS["pdf"])

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings["chunk_size"],
            chunk_overlap=settings["chunk_overlap"],
            separators=SEPARATORS
        )

        # split this page text into smaller pieces
        page_chunks = splitter.split_text(page["text"])

        # attach the original metadata to every chunk so we don't lose the source
        for i, chunk_text in enumerate(page_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **page["metadata"],
                    "chunk_index": i,
                }
            })

    return chunks