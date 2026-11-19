"""
This file tests the text cleaner without any api key.
It checks that markup is removed and the real words and numbers are kept.
"""

from src.ingestion import text_cleaner
from src.ingestion.text_cleaner import clean_page_text, clean_if_enabled


def test_picture_markers_are_removed():
    text = "Before <!-- Start of picture text --> chart words <!-- End of picture text --> after"
    cleaned = clean_page_text(text)
    assert "<!--" not in cleaned
    assert "chart words" in cleaned


def test_br_becomes_a_space_and_sup_is_dropped():
    assert clean_page_text("line one<br>line two") == "line one line two"
    assert clean_page_text("x<sup>2</sup>") == "x2"


def test_table_divider_rows_are_removed_but_cells_stay():
    table = "| name | score |\n|---|---|\n| bm25 | 0.8 |"
    cleaned = clean_page_text(table)
    assert "---" not in cleaned
    assert "bm25" in cleaned and "0.8" in cleaned


def test_bold_markers_are_removed():
    assert clean_page_text("this is **important** text") == "this is important text"


def test_spaces_and_blank_lines_are_tidied():
    cleaned = clean_page_text("a    b\n\n\n\n\nc")
    assert cleaned == "a b\n\nc"


def test_clean_if_enabled_respects_the_switch(monkeypatch):
    monkeypatch.setattr(text_cleaner, "ENABLED", False)
    assert clean_if_enabled("**keep**") == "**keep**"
    monkeypatch.setattr(text_cleaner, "ENABLED", True)
    assert clean_if_enabled("**keep**") == "keep"
