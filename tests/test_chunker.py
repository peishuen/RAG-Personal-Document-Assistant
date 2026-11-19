"""
This file tests the chunker without any api key.
It checks chunk size, page info, the context header and chunk numbering.
"""

from src.chunking import chunker
from src.chunking.chunker import chunk_pages, build_header


def make_page(text, doc_type="pdf", page=1):
    # build a page in the same shape the loaders return
    return {"text": text, "metadata": {"source": "data/sample_docs/My-Report_v2.pdf", "page": page, "type": doc_type}}


def test_header_uses_a_readable_file_name():
    # dashes and underscores become spaces, and the folder and extension are dropped
    header = build_header({"source": "data/sample_docs/My-Report_v2.pdf", "page": 3})
    assert header == "Source: My Report v2, page 3\n"


def test_short_page_gives_one_chunk_with_header():
    chunks = chunk_pages([make_page("A short page.")])
    assert len(chunks) == 1
    assert chunks[0]["text"].startswith("Source: My Report v2, page 1\n")
    assert chunks[0]["text"].endswith("A short page.")


def test_header_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(chunker, "ADD_CONTEXT_HEADER", False)
    chunks = chunk_pages([make_page("A short page.")])
    assert chunks[0]["text"] == "A short page."


def test_long_page_is_split_and_chunks_stay_small(monkeypatch):
    monkeypatch.setattr(chunker, "ADD_CONTEXT_HEADER", False)
    text = " ".join(f"Sentence number {i}." for i in range(200))
    chunks = chunk_pages([make_page(text)])
    assert len(chunks) > 1
    # no chunk may be longer than the pdf chunk size
    assert all(len(c["text"]) <= chunker.CHUNK_SETTINGS["pdf"]["chunk_size"] for c in chunks)


def test_chunks_keep_page_info_and_count_from_zero_per_page(monkeypatch):
    monkeypatch.setattr(chunker, "ADD_CONTEXT_HEADER", False)
    long_text = " ".join(f"Word{i}" for i in range(400))
    chunks = chunk_pages([make_page(long_text, page=1), make_page(long_text, page=2)])
    page_two = [c for c in chunks if c["metadata"]["page"] == 2]
    assert page_two[0]["metadata"]["chunk_index"] == 0
    assert [c["metadata"]["chunk_index"] for c in page_two] == list(range(len(page_two)))
    assert all(c["metadata"]["source"].endswith("My-Report_v2.pdf") for c in chunks)


def test_unknown_type_falls_back_to_pdf_settings(monkeypatch):
    monkeypatch.setattr(chunker, "ADD_CONTEXT_HEADER", False)
    text = " ".join(f"Sentence number {i}." for i in range(200))
    chunks = chunk_pages([make_page(text, doc_type="mystery")])
    assert all(len(c["text"]) <= chunker.CHUNK_SETTINGS["pdf"]["chunk_size"] for c in chunks)


def test_empty_page_gives_no_chunks():
    assert chunk_pages([make_page("")]) == []
