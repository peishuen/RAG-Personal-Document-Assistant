# streamlit demo app for the rag personal document assistant
# lets a user upload documents, ask a question and see the grounded answer with citations

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

UPLOAD_DIR = "data/uploads"

def already_stored(content_hash: str, collection_name: str = "documents") -> bool:
    # check by content hash, not file path, so re-uploading the same content under a new
    # filename is still recognized as a duplicate instead of being re-embedded
    collection = get_collection(collection_name)
    result = collection.get(where={"content_hash": content_hash}, limit=1)
    return len(result["ids"]) > 0

st.title("Personal Document Assistant")
st.write("Upload documents, then ask a question about their content.")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# keep a running list of prior turns in session state so they survive a streamlit rerun
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# accept one or more pdf or text files at once, matches the batch upload support in batch_loader
uploaded_files = st.file_uploader(
    "Upload PDF or text files",
    type=["pdf", "txt"],
    accept_multiple_files=True
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

st.divider()

# let the user see what's currently stored and remove anything they no longer want searched
if get_collection().count() > 0:
    with st.expander("Manage stored documents"):
        for doc in list_sources():
            col1, col2 = st.columns([4, 1])
            col1.write(f"{doc['source']} — {doc['page_count']} page(s), {doc['chunk_count']} chunk(s)")

            if col2.button("Delete", key=f"delete_{doc['source']}"):
                delete_source(doc["source"])

                # also remove the file from disk if it's one of our own uploads
                if os.path.exists(doc["source"]) and os.path.abspath(doc["source"]).startswith(os.path.abspath(UPLOAD_DIR)):
                    os.remove(doc["source"])

                st.rerun()

    st.divider()

# only let the user ask once the store actually has chunks in it, covers both a fresh upload and docs stored from before
if get_collection().count() > 0:
    # render past turns first, above the input, so the thread stays on screen and
    # doesn't get overwritten by the spinner below while a new answer is generating
    # each turn renders as a chat bubble so the history reads visually distinct from the rest of the page
    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(turn["question"])

        with st.chat_message("assistant"):
            st.write(turn["answer"])

            # check this turn's own grounding result
            if turn["grounded"]:
                st.success(f"grounded: {turn['grounding_reason']}")
            else:
                st.warning(f"not clearly grounded: {turn['grounding_reason']}, answer may be unreliable")

            st.markdown("**Sources**")
            st.markdown(turn["citations"])

    if st.session_state.chat_history:
        st.divider()

    # let the user narrow retrieval to specific documents, empty selection searches everything
    selected_sources = st.multiselect(
        "Limit search to specific document(s) (leave empty to search all)",
        options=[doc["source"] for doc in list_sources()]
    )

    question = st.text_input("Ask a question about your uploaded documents")

    # search across every stored document, then generate an answer from retrieved chunks
    if st.button("Ask") and question:
        with st.spinner("searching and generating answer..."):
            # resolve follow-ups like "what about its accuracy" into a standalone query before retrieval
            standalone_query = rewrite_query(question, st.session_state.chat_history)

            chunks = cross_document_search(standalone_query, top_k=5, sources=selected_sources)
            answer = generate_answer(standalone_query, chunks, st.session_state.chat_history)

            # check the answer is actually backed by the retrieved chunks before showing it as trustworthy
            grounding = check_grounding(answer, chunks)

            # figure out which chunks the answer cites and format them as a source list
            cited = build_cited_answer(answer, chunks)

            # save this turn so it stays available for the rest of the session
            st.session_state.chat_history.append({
                "question": question,
                "answer": cited["answer"],
                "grounded": grounding["grounded"],
                "grounding_reason": grounding["reason"],
                "citations": cited["citations"]
            })

        # rerun so the new turn renders immediately in the history loop above
        st.rerun()
else:
    st.info("upload and store at least one document before asking a question")