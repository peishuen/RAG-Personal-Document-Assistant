# streamlit demo app for the rag personal document assistant
# layout: 40% left panel (documents + sessions), 60% right panel (chat)

import hashlib
import os
import sys
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
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

UPLOAD_DIR = "data/uploads"

# shown in the middle of the right panel before any question has been asked, chatgpt-style
SUGGESTED_PROMPTS = [
    "Summarize the key points across all my documents",
    "What are the main findings?",
    "Compare the documents I've uploaded",
    "Explain this in simple terms",
]

# fixed pixel heights for the three independently scrollable regions — streamlit's
# container only takes a fixed height (no vh/percent/flex-fill), so these are picked to
# leave room for the headers/uploader/input around them within one normal browser window.
# tune these if a panel clips on a particularly short screen. CHAT_HEIGHT is only a seed:
# the css below replaces it with a calc(100vh - ...) so the chat box actually stretches
# to fill the screen instead of sitting at this fixed size
DOC_LIST_HEIGHT = 140
SESSIONS_HEIGHT = 120
CHAT_HEIGHT = 425

st.set_page_config(page_title="Querio", layout="wide")

# lock the page itself to one viewport (no outer scrollbar) and trim streamlit's default
# padding/spacing — the three st.container(height=...) boxes below already scroll on their
# own, this just stops the page around them from ALSO scrolling as one, and claws back
# enough vertical room that the fixed-height boxes above actually have space to sit in
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
    /* the divider between documents and session memory has its own built-in margin on
       top of that gap, making the space between the two sections larger than the rest */
    hr {
        margin: 0.15rem 0;
    }
    /* breathing room between the dropzone's "drag and drop" text and the browse button —
       the two sit in a flex row with no gap set by streamlit by default */
    [data-testid="stFileUploaderDropzone"] {
        gap: 1rem;
    }
    /* shrink just the per-document delete buttons, scoped to the box that DIRECTLY holds
       the del-btn-marker (not just any ancestor — :has() with no child combinators also
       matched the page's own outer wrapper, since it contains the marker too, which
       shrank every button on the page; the fixed-depth chain below avoids that) */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > [data-testid="stMarkdown"] .del-btn-marker
    ) button {
        padding: 0.1rem 0.4rem;
        min-height: unset;
        height: 1.75rem;
        width: 1.75rem;
        font-size: 0.75rem;
    }
    /* keep the suggested-prompt buttons at their current width even though the chat box
       and input below grow wider — same fixed-depth scoping as above */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] > [data-testid="stMarkdown"] .suggested-prompts-marker
    ) [data-testid="stHorizontalBlock"] {
        max-width: 1120px;
        margin: 0 auto;
    }
    /* give every suggestion button the same box, regardless of how many lines its own
       text wraps to — fixed height, content centered inside it both ways */
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
    /* stretch the chat box to fill the space down to just above the input, instead of
       the smaller fixed height it only needs to be independently scrollable — this is
       what pushes the prompt box down near the bottom of the viewport without the page
       growing a scrollbar (the box itself still scrolls internally once it's full) */
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
    # check by content hash, not file path, so re-uploading the same content under a new
    # filename is still recognized as a duplicate instead of being re-embedded
    collection = get_collection(collection_name)
    result = collection.get(where={"content_hash": content_hash}, limit=1)
    return len(result["ids"]) > 0


os.makedirs(UPLOAD_DIR, exist_ok=True)

# keep a running list of prior turns in session state so they survive a streamlit rerun —
# this is also what rewrite_query/generate_answer use as follow-up context, and it's
# persisted to disk (see save_session below) under active_session_id so it can be
# resumed later, since session_state itself doesn't survive a page reload
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = new_session_id()

# holds a question clicked from the suggested-prompts panel until it's processed below
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# small full-width name band, replaces the old big title
with st.container(border=True):
    st.markdown("<span style='font-size:0.85rem; font-weight:600;'>Querio</span>", unsafe_allow_html=True)

left_col, right_col = st.columns([4, 6], gap="large")

# collected while rendering the document scope checkboxes below, read by the right panel
# further down this same script run to narrow retrieval
selected_sources = []

# ---------------------------------------------------------------------------
# left panel, upper half: document list + upload
# the uploader stays fixed; only the stored-document list scrolls on its own
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
        seen_hashes = set()  # catches duplicate content uploaded together in the same batch

        for uploaded_file in uploaded_files:
            # normalize to forward slashes so paths stay consistent with the sample doc paths used in testing/ingest_sample_docs.py
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name).replace(os.sep, "/")
            file_bytes = uploaded_file.getbuffer()
            content_hash = hashlib.sha256(file_bytes).hexdigest()

            # save the upload to disk so the existing loaders can read it by file path
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            # skip content that's already stored (even under a different filename) or repeated within this same upload
            if content_hash in seen_hashes or already_stored(content_hash):
                st.info(f"{uploaded_file.name} matches content already stored, skipping...")
                continue

            seen_hashes.add(content_hash)

            pages = load_document(file_path)
            chunks = chunk_pages(pages)

            # stamp every chunk with the file's content hash so future uploads can be matched by content
            for chunk in chunks:
                chunk["metadata"]["content_hash"] = content_hash

            new_chunks.extend(chunks)

        # embed and store only the chunks from newly uploaded files
        if new_chunks:
            with st.spinner(f"embedding and storing {len(new_chunks)} chunk(s)..."):
                new_chunks = generate_embeddings(new_chunks)
                store_chunks(new_chunks)
            st.success(f"stored {len(new_chunks)} new chunk(s)")

    # let the user see what's currently stored, scope retrieval to specific documents,
    # and remove anything they no longer want searched — all from one scrollable list
    if get_collection().count() > 0:
        st.caption("check document(s) to limit search to them — leave all unchecked to search everything")

        with st.container(height=DOC_LIST_HEIGHT, border=True):
            for doc in list_sources():
                check_col, label_col, delete_col = st.columns([1, 5, 1])

                in_scope = check_col.checkbox(
                    "in scope",
                    key=f"scope_{doc['source']}",
                    label_visibility="collapsed"
                )
                if in_scope:
                    selected_sources.append(doc["source"])

                label_col.markdown(f"**{doc['source']}**  \n{doc['page_count']} page(s), {doc['chunk_count']} chunk(s)")

                # invisible marker the css above uses to find just this button and shrink it
                delete_col.markdown('<span class="del-btn-marker"></span>', unsafe_allow_html=True)

                if delete_col.button("🗑️", key=f"delete_{doc['source']}", help="delete this document"):
                    delete_source(doc["source"])

                    # also remove the file from disk if it's one of our own uploads
                    if os.path.exists(doc["source"]) and os.path.abspath(doc["source"]).startswith(os.path.abspath(UPLOAD_DIR)):
                        os.remove(doc["source"])

                    st.rerun()
    else:
        st.caption("no documents uploaded yet")

    st.divider()

    # ---------------------------------------------------------------------
    # left panel, bottom half: sessions
    # every conversation with at least one finished turn is saved to disk as it goes
    # (src/session/session_store.py), since streamlit's own session_state resets on
    # every page reload — this panel is what lets a reload actually resume something
    # ---------------------------------------------------------------------
    st.subheader("🧠 Sessions")

    if st.button("+ New chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.active_session_id = new_session_id()
        st.rerun()

    saved_sessions = list_sessions()

    if saved_sessions:
        st.caption("resume a past conversation — this replaces what the assistant currently remembers")

        with st.container(height=SESSIONS_HEIGHT, border=True):
            for sess in saved_sessions:
                is_active = sess["id"] == st.session_state.active_session_id
                label = f"{'🟢 ' if is_active else ''}{sess['title']}"
                meta = f"{sess['turn_count']} turn(s) · {format_relative_time(sess['updated_at'])}"

                resume_col, delete_col = st.columns([5, 1])

                if resume_col.button(label, key=f"resume_{sess['id']}", use_container_width=True, disabled=is_active):
                    st.session_state.chat_history = load_session(sess["id"])
                    st.session_state.active_session_id = sess["id"]
                    st.rerun()

                resume_col.caption(meta)

                # invisible marker the css above uses to find just this button and shrink it
                delete_col.markdown('<span class="del-btn-marker"></span>', unsafe_allow_html=True)

                if delete_col.button("🗑️", key=f"delete_session_{sess['id']}", help="delete this session"):
                    delete_session(sess["id"])

                    # deleting the active session starts a fresh one so there's always something to write to
                    if is_active:
                        st.session_state.chat_history = []
                        st.session_state.active_session_id = new_session_id()

                    st.rerun()
    else:
        st.caption("no saved sessions yet — ask a question to start one")

# ---------------------------------------------------------------------------
# right panel: chat history scrolls on its own, the prompt box stays fixed below it
# document scope is set from the checkboxes in the left panel above, not here
# ---------------------------------------------------------------------------
with right_col:
    has_docs = get_collection().count() > 0

    if not has_docs:
        st.subheader("💬 Ask your documents")
        st.info("upload and store at least one document before asking a question")
    else:
        history_box = st.container(height=CHAT_HEIGHT, border=True)

        with history_box:
            # invisible marker that's always present (unlike the suggested-prompts one
            # below, which only renders before the first question) so the css above can
            # find this exact box in either state and stretch it toward the bottom
            st.markdown('<span class="chat-box-marker"></span>', unsafe_allow_html=True)

            if not st.session_state.chat_history:
                # empty state: suggested prompts centered above the input, like chatgpt's new-chat screen
                st.markdown(
                    "<div style='text-align:center; margin-top:3rem;'>"
                    "<h3>what would you like to know?</h3>"
                    "<p style='color:gray;'>pick a suggestion or type your own question below</p>"
                    "</div>",
                    unsafe_allow_html=True
                )

                # invisible marker the css above uses to pin this row's width, independent
                # of how wide the surrounding chat box is
                st.markdown('<span class="suggested-prompts-marker"></span>', unsafe_allow_html=True)

                prompt_cols = st.columns(2)
                for i, suggestion in enumerate(SUGGESTED_PROMPTS):
                    if prompt_cols[i % 2].button(suggestion, use_container_width=True, key=f"suggested_{i}"):
                        st.session_state.pending_question = suggestion
            else:
                # render past turns as chat bubbles, oldest first. the most recent turn can
                # be "pending" — question asked, answer not generated yet — in which case its
                # user bubble still renders immediately below, and the assistant bubble runs
                # the actual pipeline right here under a spinner, then reruns once done so the
                # spinner is cleanly replaced by the finished answer on the next render
                for i, turn in enumerate(st.session_state.chat_history):
                    with st.chat_message("user"):
                        st.markdown(turn["question"])

                    with st.chat_message("assistant"):
                        if turn.get("pending"):
                            with st.spinner("searching and generating answer..."):
                                # only the turns before this one count as context for follow-ups
                                prior_history = st.session_state.chat_history[:i]

                                # resolve follow-ups like "what about its accuracy" into a standalone query before retrieval
                                standalone_query = rewrite_query(turn["question"], prior_history)

                                chunks = cross_document_search(standalone_query, top_k=5, sources=selected_sources)
                                answer = generate_answer(standalone_query, chunks, prior_history)

                                # check the answer is actually backed by the retrieved chunks before showing it as trustworthy
                                grounding = check_grounding(answer, chunks)

                                # figure out which chunks the answer cites and format them as a source list
                                cited = build_cited_answer(answer, chunks)

                                # fill in this same turn in place, now that the answer is ready
                                turn.update({
                                    "answer": cited["answer"],
                                    "grounded": grounding["grounded"],
                                    "grounding_reason": grounding["reason"],
                                    "citations": cited["citations"],
                                    "pending": False
                                })

                                # persist now that the turn is complete, so this conversation
                                # survives a reload and shows up in the sessions list
                                save_session(st.session_state.active_session_id, st.session_state.chat_history)

                            # rerun so this turn renders as a finished answer instead of a spinner
                            st.rerun()
                        else:
                            st.write(turn["answer"])

                            if turn["grounded"]:
                                st.success(f"grounded: {turn['grounding_reason']}")
                            else:
                                st.warning(f"not clearly grounded: {turn['grounding_reason']}, answer may be unreliable")

                            st.markdown("**Sources**")
                            st.markdown(turn["citations"])

        # history_box above has a fixed height and scrolls on its own, so this always renders
        # directly below it at a consistent spot — streamlit's own chat_input auto-pin only
        # works page-wide and turns itself off once nested in a column, so a fixed-height
        # history box (rather than relying on that) is what keeps this in place here
        typed_question = st.chat_input("ask a question about your uploaded documents")

        # a clicked suggestion takes priority over a leftover typed value from the same rerun
        question = st.session_state.pending_question or typed_question
        st.session_state.pending_question = None

        if question:
            # append as pending and rerun right away, before generating anything — the loop
            # above picks this turn up on the next render, shows the question immediately,
            # and only then runs the pipeline under a spinner in the assistant's bubble
            st.session_state.chat_history.append({"question": question, "pending": True})
            st.rerun()
