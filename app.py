# streamlit demo app for the rag personal document assistant
# lets a user upload documents, ask a question and see the grounded answer with citations

import os
import sys
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from src.ingestion.batch_loader import load_document
from src.chunking.chunker import chunk_pages
from src.embeddings.embedder import generate_embeddings
from src.vectorstore.chroma_store import store_chunks, get_collection
from src.retrieval.cross_document import cross_document_search
from src.generation.query_rewriter import rewrite_query
from src.generation.generator import generate_answer
from src.generation.grounding_check import check_grounding
from src.citation.citation_tracker import build_cited_answer

UPLOAD_DIR = "data/uploads"

def already_stored(file_path: str, collection_name: str = "documents") -> bool:
    # check if this file's chunks are already in the collection so re-uploading the same file dows not re-embed it
    collection = get_collection(collection_name)
    result = collection.get(where={"source": file_path}, limit=1)
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

    for uploaded_file in uploaded_files:
        # normalize to forward slashes so paths stay consistent with the sample doc paths used in testing/ingest_sample_docs.py
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name).replace(os.sep, "/")

        # save the upload to disk so the existing loaders can read it by file path
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # skip files that are already embedded and stored, so re-uploading the same file does not redo the work
        if already_stored(file_path):
            st.info(f"{uploaded_file.name} is already stored, skipping...")
            continue

        pages = load_document(file_path)
        new_chunks.extend(chunk_pages(pages))

    # embed and store only the chunks from newly uploaded files
    if new_chunks:
        with st.spinner(f"embedding and storing {len(new_chunks)} chunk(s)..."):
            new_chunks = generate_embeddings(new_chunks)
            store_chunks(new_chunks)
        st.success(f"stored {len(new_chunks)} new chunk(s)")

# only let the user ask once the store actually has chunks in it, covers both a fresh upload and docs stored from before
if get_collection().count() > 0:
    question = st.text_input("Ask a question about your uploaded documents")

    # search across every stored document, then generate an answer from retrieved chunks
    if st.button("Ask") and question:
        with st.spinner("searching and generating answer..."):
            # resolve follow-ups like "what about its accuracy" into a standalone query before retrieval
            standalone_query = rewrite_query(question, st.session_state.chat_history)

            chunks = cross_document_search(standalone_query, top_k=5)
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
                "best_score": grounding["best_score"],
                "citations": cited["citations"]
            })

    # loop through every past turn, oldest first, so the thread always renders regardless of button state
    for turn in st.session_state.chat_history:
        st.markdown(f"**You:** {turn['question']}")
        st.write(turn["answer"])

        # check this turn's own grounding result
        if turn["grounded"]:
            st.success(f"grounded (best match score {turn['best_score']:.2f})")
        else:
            st.warning(f"not clearly grounded (best match score {turn['best_score']:.2f}), answer may be unreliable")

        st.markdown("**Sources**")
        st.markdown(turn["citations"])
        st.divider()
else:
    st.info("upload and store at least one document before asking a question")