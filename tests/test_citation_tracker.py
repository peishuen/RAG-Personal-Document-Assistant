"""
This file tests the citation tracker without any api key.
It checks which chunks are picked from an answer and how the sources are listed.
"""

from src.citation.citation_tracker import extract_cited_chunks, format_citations, build_cited_answer


def make_chunks(count=3):
    # build chunks with different pages, so we can tell them apart
    return [{"text": f"chunk {i}", "metadata": {"source": f"doc{i}.pdf", "page": i, "chunk_index": i}} for i in range(1, count + 1)]


def test_picks_only_the_cited_chunks_in_order():
    chunks = make_chunks()
    cited = extract_cited_chunks("It is X [Source 3] and Y [Source 1].", chunks)
    assert [c["text"] for c in cited] == ["chunk 1", "chunk 3"]


def test_repeated_citations_are_counted_once():
    cited = extract_cited_chunks("A [Source 2] B [Source 2]", make_chunks())
    assert len(cited) == 1


def test_short_form_is_used_when_the_word_source_is_missing():
    cited = extract_cited_chunks("A [2]", make_chunks())
    assert cited[0]["text"] == "chunk 2"


def test_no_citation_returns_all_chunks():
    chunks = make_chunks()
    assert extract_cited_chunks("No citations here.", chunks) == chunks


def test_numbers_outside_the_list_are_ignored():
    cited = extract_cited_chunks("A [Source 9] B [Source 0] C [Source 1]", make_chunks())
    assert [c["text"] for c in cited] == ["chunk 1"]


def test_format_lists_file_page_and_chunk():
    text = format_citations(make_chunks(1))
    assert text == "- doc1.pdf (page 1, chunk 1)"


def test_build_cited_answer_keeps_the_answer_and_lists_sources():
    result = build_cited_answer("Fact [Source 2].", make_chunks())
    assert result["answer"] == "Fact [Source 2]."
    assert result["citations"] == "- doc2.pdf (page 2, chunk 2)"
    assert len(result["cited_chunks"]) == 1
