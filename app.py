"""
This file is the streamlit demo app for the rag personal document assistant.
The page has two parts: a left panel (40%) for documents and sessions,
and a right panel (60%) for the chat.
It uses the same pipeline as the backend: upload, search, answer, cite and save.
"""

import hashlib
import os
import sys
import streamlit as st
from dotenv import load_dotenv

# add the project folder to the python path, so imports like "src.xxx" work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# load the secret keys from the .env file
load_dotenv()

from src.ingestion.batch_loader import load_document
from src.chunking.chunker import chunk_pages
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection, list_sources, delete_source
from src.retrieval.cross_document import cross_document_search
from src.generation.query_rewriter import rewrite_query
from src.generation.generator import generate_answer
from src.generation.grounding_check import check_grounding
from src.citation.citation_tracker import build_cited_answer
from src.session.session_store import (
    new_session_id, save_session, load_session, list_sessions, delete_session, format_relative_time
)

# set the folder for uploaded files
UPLOAD_DIR = "data/uploads"

# show these suggestions in the chat panel before the first question
SUGGESTED_PROMPTS = [
    "Summarize the key points across all my documents",
    "What are the main findings?",
    "Compare the documents I've uploaded",
    "Explain this in simple terms",
]

# set fixed pixel heights for the three scrollable boxes, because streamlit containers need a fixed height
# change these if a box is cut off on a short screen
# CHAT_HEIGHT is only a starting value, the css below stretches it to fill the screen
DOC_LIST_HEIGHT = 140
SESSIONS_HEIGHT = 120
CHAT_HEIGHT = 425

st.set_page_config(page_title="Querio", layout="wide")

# add css to fit the page in one screen and remove the extra spacing
# the three boxes already scroll by themselves, so the whole page should not scroll too
st.markdown(
    """
    <style>
    .stAppViewMain {
        height: 100vh;
        overflow: hidden;
    }
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 1.75rem;
        padding-bottom: 0.5rem;
    }
    [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    /* shrink the divider margin, so the two sections are not too far apart */
    hr {
        margin: 0.15rem 0;
    }
    /* add space between the drag and drop text and the browse button */
    [data-testid="stFileUploaderDropzone"] {
        gap: 1rem;
    }
    /* shrink only the delete buttons, by finding the box that directly holds the marker */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > [data-testid="stMarkdown"] .del-btn-marker
    ) button {
        padding: 0.1rem 0.4rem;
        min-height: unset;
        height: 1.75rem;
        width: 1.75rem;
        font-size: 0.75rem;
    }
    /* keep the suggested prompt buttons at a fixed width, even when the chat box grows */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > [data-testid="stMarkdown"] .suggested-prompts-marker
    ) [data-testid="stHorizontalBlock"] {
        max-width: 1120px;
        margin: 0 auto;
    }
    /* give every suggestion button the same height, with the text centered */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > [data-testid="stMarkdown"] .suggested-prompts-marker
    ) [data-testid="stHorizontalBlock"] button {
        height: 4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        white-space: normal;
        text-align: center;
    }
    /* stretch the chat box down to just above the input box, without making the page scroll */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > [data-testid="stMarkdown"] .chat-box-marker
    ) {
        height: calc(100vh - 180px) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def already_stored(content_hash: str, collection_name: str = "documents") -> bool:
    # check by file content (hash), not by name, so the same file under a new name is not embedded again
    collection = get_collection(collection_name)
    result = collection.get(where={"content_hash": content_hash}, limit=1)
    return len(result["ids"]) > 0


# create the upload folder if it is missing
os.makedirs(UPLOAD_DIR, exist_ok=True)

# keep the past turns in session state, so they stay after streamlit reruns the script
# they are also used as context for follow-up questions, and saved to disk by save_session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# give this chat an id, so it can be saved and resumed later
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = new_session_id()

# hold a clicked suggestion until it is processed below
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# show a small name band at the top
with st.container(border=True):
    st.markdown("<span style='font-size:0.85rem; font-weight:600;'>Querio</span>", unsafe_allow_html=True)

# split the page into a left column (40%) and a right column (60%)
left_col, right_col = st.columns([4, 6], gap="large")

# collect the documents the user ticks, and use them later to limit the search
selected_sources = []

# ---------------------------------------------------------------------------
# left panel, upper half: document list and upload
# ---------------------------------------------------------------------------
with left_col:
    st.subheader("📁 Documents")

    uploaded_files = st.file_uploader(
        "Upload PDF or text files",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        new_chunks = []
        # track hashes to catch duplicate files in the same upload
        seen_hashes = set()

        for uploaded_file in uploaded_files:
            # use forward slashes, so the path matches the sample doc paths
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name).replace(os.sep, "/")
            file_bytes = uploaded_file.getbuffer()
            content_hash = hashlib.sha256(file_bytes).hexdigest()

            # save the file to disk, because the loaders read files by path
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            # skip the file if the same content is already stored or repeated in this upload
            if content_hash in seen_hashes or already_stored(content_hash):
                st.info(f"{uploaded_file.name} matches content already stored, skipping...")
                continue

            seen_hashes.add(content_hash)

            # read the file and split it into chunks
            pages = load_document(file_path)
            chunks = chunk_pages(pages)

            # add the hash to every chunk, so future uploads can be matched by content
            for chunk in chunks:
                chunk["metadata"]["content_hash"] = content_hash

            new_chunks.extend(chunks)

        # embed and store only the chunks from new files
        if new_chunks:
            with st.spinner(f"embedding and storing {len(new_chunks)} chunk(s)..."):
                new_chunks = generate_embeddings(new_chunks)
                store_chunks(new_chunks)
            st.success(f"stored {len(new_chunks)} new chunk(s)")

    # show the stored documents in one scrollable list
    # the user can tick a document to limit the search, or delete it
    if get_collection().count() > 0:
        st.caption("check document(s) to limit search to them — leave all unchecked to search everything")

        with st.container(height=DOC_LIST_HEIGHT, border=True):
            for doc in list_sources():
                check_col, label_col, delete_col = st.columns([1, 5, 1])

                # show a checkbox to include this document in the search
                in_scope = check_col.checkbox(
                    "in scope",
                    key=f"scope_{doc['source']}",
                    label_visibility="collapsed"
                )
                if in_scope:
                    selected_sources.append(doc["source"])

                # show the file name with its page and chunk counts
                label_col.markdown(f"**{doc['source']}**  \n{doc['page_count']} page(s), {doc['chunk_count']} chunk(s)")

                # add an invisible marker, so the css can find this button and shrink it
                delete_col.markdown('<span class="del-btn-marker"></span>', unsafe_allow_html=True)

                if delete_col.button("🗑️", key=f"delete_{doc['source']}", help="delete this document"):
                    delete_source(doc["source"])

                    # delete the file from disk too, if it is an uploaded file
                    if os.path.exists(doc["source"]) and os.path.abspath(doc["source"]).startswith(os.path.abspath(UPLOAD_DIR)):
                        os.remove(doc["source"])

                    # refresh the page to show the updated list
                    st.rerun()
    else:
        st.caption("no documents uploaded yet")

    st.divider()

    # ---------------------------------------------------------------------
    # left panel, bottom half: sessions
    # every chat with at least one finished turn is saved to disk
    # this lets the user resume a chat after reloading the page
    # ---------------------------------------------------------------------
    st.subheader("🧠 Sessions")

    # start a fresh chat with a new id
    if st.button("+ New chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.active_session_id = new_session_id()
        st.rerun()

    saved_sessions = list_sessions()

    if saved_sessions:
        st.caption("resume a past conversation — this replaces what the assistant currently remembers")

        with st.container(height=SESSIONS_HEIGHT, border=True):
            for sess in saved_sessions:
                # mark the chat that is open now with a green dot
                is_active = sess["id"] == st.session_state.active_session_id
                label = f"{'🟢 ' if is_active else ''}{sess['title']}"
                meta = f"{sess['turn_count']} turn(s) · {format_relative_time(sess['updated_at'])}"

                resume_col, delete_col = st.columns([5, 1])

                # load the saved chat when its button is clicked
                if resume_col.button(label, key=f"resume_{sess['id']}", use_container_width=True, disabled=is_active):
                    st.session_state.chat_history = load_session(sess["id"])
                    st.session_state.active_session_id = sess["id"]
                    st.rerun()

                resume_col.caption(meta)

                # add an invisible marker, so the css can find this button and shrink it
                delete_col.markdown('<span class="del-btn-marker"></span>', unsafe_allow_html=True)

                if delete_col.button("🗑️", key=f"delete_session_{sess['id']}", help="delete this session"):
                    delete_session(sess["id"])

                    # start a fresh chat if the open one was deleted, so there is always a chat to write to
                    if is_active:
                        st.session_state.chat_history = []
                        st.session_state.active_session_id = new_session_id()

                    st.rerun()
    else:
        st.caption("no saved sessions yet — ask a question to start one")

# ---------------------------------------------------------------------------
# right panel: the chat history scrolls, and the input box stays below it
# the documents to search come from the checkboxes in the left panel
# ---------------------------------------------------------------------------
with right_col:
    has_docs = get_collection().count() > 0

    # ask the user to upload a document first if there are none
    if not has_docs:
        st.subheader("💬 Ask your documents")
        st.info("upload and store at least one document before asking a question")
    else:
        history_box = st.container(height=CHAT_HEIGHT, border=True)

        with history_box:
            # add an invisible marker, so the css can find this box and stretch it
            st.markdown('<span class="chat-box-marker"></span>', unsafe_allow_html=True)

            if not st.session_state.chat_history:
                # show a welcome message and suggestions when the chat is empty
                st.markdown(
                    "<div style='text-align:center; margin-top:3rem;'>"
                    "<h3>what would you like to know?</h3>"
                    "<p style='color:gray;'>pick a suggestion or type your own question below</p>"
                    "</div>",
                    unsafe_allow_html=True
                )

                # add an invisible marker, so the css can fix the width of this row
                st.markdown('<span class="suggested-prompts-marker"></span>', unsafe_allow_html=True)

                # show the suggestions as buttons in two columns
                prompt_cols = st.columns(2)
                for i, suggestion in enumerate(SUGGESTED_PROMPTS):
                    if prompt_cols[i % 2].button(suggestion, use_container_width=True, key=f"suggested_{i}"):
                        st.session_state.pending_question = suggestion
            else:
                # show past turns as chat bubbles, oldest first
                # the last turn may be "pending" (asked but not answered yet)
                # in that case, show the question and run the pipeline under a spinner
                for i, turn in enumerate(st.session_state.chat_history):
                    with st.chat_message("user"):
                        st.markdown(turn["question"])

                    with st.chat_message("assistant"):
                        if turn.get("pending"):
                            with st.spinner("searching and generating answer..."):
                                # use only the earlier turns as context for follow-ups
                                prior_history = st.session_state.chat_history[:i]

                                # rewrite follow-up questions so they make sense alone
                                standalone_query = rewrite_query(turn["question"], prior_history)

                                # find the best chunks and write the answer from them
                                chunks = cross_document_search(standalone_query, top_k=5, sources=selected_sources)
                                answer = generate_answer(standalone_query, chunks, prior_history)

                                # check that the chunks really support the answer
                                grounding = check_grounding(answer, chunks)

                                # find the cited chunks and make a source list
                                cited = build_cited_answer(answer, chunks)

                                # fill in this same turn now that the answer is ready
                                turn.update({
                                    "answer": cited["answer"],
                                    "grounded": grounding["grounded"],
                                    "grounding_reason": grounding["reason"],
                                    "citations": cited["citations"],
                                    "pending": False
                                })

                                # save the chat now, so it stays after a reload and shows in the sessions list
                                save_session(st.session_state.active_session_id, st.session_state.chat_history)

                            # rerun the page to replace the spinner with the finished answer
                            st.rerun()
                        else:
                            # show the answer
                            st.write(turn["answer"])

                            # show if the answer is backed by the sources
                            if turn["grounded"]:
                                st.success(f"grounded: {turn['grounding_reason']}")
                            else:
                                st.warning(f"not clearly grounded: {turn['grounding_reason']}, answer may be unreliable")

                            st.markdown("**Sources**")
                            st.markdown(turn["citations"])

        # show the input box right below the chat box
        # the chat box has a fixed height, so this box always stays in the same place
        typed_question = st.chat_input("ask a question about your uploaded documents")

        # use the clicked suggestion first, then the typed question
        question = st.session_state.pending_question or typed_question
        st.session_state.pending_question = None

        if question:
            # add the question as pending and rerun at once
            # the loop above then shows the question first, and runs the pipeline after
            st.session_state.chat_history.append({"question": question, "pending": True})
            st.rerun()
