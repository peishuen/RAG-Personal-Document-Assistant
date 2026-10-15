"""
This file is the streamlit demo app for the rag personal document assistant.
It has a simple single-column page: upload documents, ask a question, and read
the grounded answer with its sources.
It also lets the user manage stored documents, limit the search to chosen files,
and save and resume chats from the sidebar.
It uses the same pipeline and the same saved chats as the FastAPI backend.
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


def already_stored(content_hash: str, collection_name: str = "documents") -> bool:
    # check by file content (hash), not by name, so the same file under a new name is not embedded again
    collection = get_collection(collection_name)
    result = collection.get(where={"content_hash": content_hash}, limit=1)
    return len(result["ids"]) > 0


def short_name(source: str) -> str:
    # show only the file name, and hide the folder path
    return source.split("/")[-1]


def show_citations(citations) -> None:
    # show sources saved as a list (react app) or as text (older streamlit chats)
    if isinstance(citations, list):
        for c in citations:
            st.markdown(f"- [{c['number']}] {c['source']} (page {c['page']}, chunk {c['chunk_index']})")
    elif citations:
        st.markdown(citations)


def show_turn(turn: dict) -> None:
    # show one question and answer, with the grounding result and the sources
    st.markdown(f"**You:** {turn['question']}")
    st.write(turn["answer"])

    # show if the answer is backed by the sources (the react app may still be checking)
    if turn.get("grounded") is None:
        st.caption("grounding check not finished")
    elif turn["grounded"]:
        st.success(f"grounded: {turn['grounding_reason']}")
    else:
        st.warning(f"not clearly grounded: {turn['grounding_reason']}, answer may be unreliable")

    with st.expander("Sources"):
        show_citations(turn.get("citations"))


st.set_page_config(page_title="Personal Document Assistant")

# create the upload folder if it is missing
os.makedirs(UPLOAD_DIR, exist_ok=True)

# keep the past turns in session state, so they stay after streamlit reruns the script
# they are also used as context for follow-up questions, and saved to disk by save_session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# give this chat an id, so it can be saved and resumed later
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = new_session_id()

# ---------------------------------------------------------------------------
# sidebar: saved chats
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Chat history")

    # start a fresh chat with a new id
    if st.button("+ New chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.active_session_id = new_session_id()
        st.rerun()

    saved_sessions = list_sessions()

    if not saved_sessions:
        st.caption("no saved chats yet, ask a question to start one")

    for sess in saved_sessions:
        # mark the chat that is open now, and disable its button
        is_active = sess["id"] == st.session_state.active_session_id
        label = f"{'🟢 ' if is_active else ''}{sess['title']}"

        resume_col, delete_col = st.columns([5, 1])

        # load the saved chat when its button is clicked
        if resume_col.button(label, key=f"resume_{sess['id']}", use_container_width=True, disabled=is_active):
            st.session_state.chat_history = load_session(sess["id"])
            st.session_state.active_session_id = sess["id"]
            st.rerun()

        resume_col.caption(f"{sess['turn_count']} turn(s) · {format_relative_time(sess['updated_at'])}")

        if delete_col.button("🗑️", key=f"delete_session_{sess['id']}", help="delete this chat"):
            delete_session(sess["id"])

            # start a fresh chat if the open one was deleted, so there is always a chat to write to
            if is_active:
                st.session_state.chat_history = []
                st.session_state.active_session_id = new_session_id()

            st.rerun()

# ---------------------------------------------------------------------------
# main page: upload, documents, question and answers
# ---------------------------------------------------------------------------
st.title("Personal Document Assistant")
st.write("Upload documents, then ask a question about their content.")

# accept one or more pdf or text files at once
uploaded_files = st.file_uploader(
    "Upload PDF or text files",
    type=["pdf", "txt"],
    accept_multiple_files=True
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

# let the user ask only when the store has chunks in it
if get_collection().count() > 0:
    sources = list_sources()

    # list the stored documents, with a button to delete each one
    with st.expander(f"Stored documents ({len(sources)})"):
        for doc in sources:
            name_col, delete_col = st.columns([6, 1])
            name_col.markdown(f"**{short_name(doc['source'])}**  \n{doc['page_count']} page(s), {doc['chunk_count']} chunk(s)")

            if delete_col.button("🗑️", key=f"delete_{doc['source']}", help="delete this document"):
                delete_source(doc["source"])

                # delete the file from disk too, if it is an uploaded file
                if os.path.exists(doc["source"]) and os.path.abspath(doc["source"]).startswith(os.path.abspath(UPLOAD_DIR)):
                    os.remove(doc["source"])

                # refresh the page to show the updated list
                st.rerun()

    # let the user limit the search to chosen documents, and search all of them when none is chosen
    selected_sources = st.multiselect(
        "Search in",
        options=[doc["source"] for doc in sources],
        format_func=short_name,
        placeholder="all documents"
    )

    # use a form, so the question box clears after each question
    with st.form("ask_form", clear_on_submit=True):
        question = st.text_input("Ask a question about your uploaded documents")
        asked = st.form_submit_button("Ask")

    if asked and question:
        with st.spinner("searching and generating answer..."):
            prior_history = st.session_state.chat_history

            # rewrite follow-up questions so they make sense alone
            standalone_query = rewrite_query(question, prior_history)

            # find the best chunks and write the answer from them
            chunks = cross_document_search(standalone_query, top_k=5, sources=selected_sources)
            answer = generate_answer(standalone_query, chunks, prior_history)

            # check that the chunks really support the answer
            grounding = check_grounding(answer, chunks)

            # find the cited chunks and make a source list
            cited = build_cited_answer(answer, chunks)

        # add this turn to the chat and save it, so it stays after a reload
        st.session_state.chat_history.append({
            "question": question,
            "answer": cited["answer"],
            "grounded": grounding["grounded"],
            "grounding_reason": grounding["reason"],
            "citations": cited["citations"]
        })
        save_session(st.session_state.active_session_id, st.session_state.chat_history)

    # show the chat with the newest question first
    for turn in reversed(st.session_state.chat_history):
        st.divider()
        show_turn(turn)
else:
    st.info("upload and store at least one document before asking a question")
