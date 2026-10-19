"""
This file cleans the markdown noise that the pdf reader leaves in page text.
Slide decks and tables come out with html comments, line break tags and bold markers
mixed into the words, which hurts both keyword search and meaning search.
It keeps the words, numbers and table cells, and only removes the markup around them.
"""

import re

# match the html comments that mark text found inside pictures
PICTURE_COMMENTS = re.compile(r"<!--\s*(Start|End) of picture text\s*-->")

# match html tags that carry no words, like <br>, <sup> and </sup>
HTML_TAGS = re.compile(r"</?(br|sup|sub)\s*/?>", re.IGNORECASE)

# match the divider row of a markdown table, like |---|---|
TABLE_DIVIDER = re.compile(r"^\|(?:\s*:?-{2,}:?\s*\|)+\s*$", re.MULTILINE)

# set whether the loaders clean page text; the evaluation turns this off to build a raw baseline
ENABLED = True

def clean_if_enabled(text: str) -> str:
    # clean the text only when cleaning is switched on
    return clean_page_text(text) if ENABLED else text

def clean_page_text(text: str) -> str:
    # remove the picture markers and the tags, and put a space where a line break tag was
    text = PICTURE_COMMENTS.sub(" ", text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = HTML_TAGS.sub("", text)

    # remove the divider rows of tables, because they carry no content
    text = TABLE_DIVIDER.sub("", text)

    # remove bold markers
    text = text.replace("**", "")

    # tidy the spaces: collapse repeated spaces, and limit blank lines to one
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
