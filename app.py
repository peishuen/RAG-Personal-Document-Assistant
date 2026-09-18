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

        # save the upload to disk so the existing laoders can read it by file path
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

    # search across every stored ducoment, then generate an answer from retrievd chunks
    if st.button("Ask") and question:
        with st.spinner("searching and generating answer..."):
            chunks = cross_document_search(question, top_k=5)
            answer = generate_answer(question, chunks)

            # check the answer is actually backed by the retrieved chunks before showing it as trustworthy
            grounding = check_grounding(answer, chunks)

            # figure out which chunks the answer cites and format them as a source list
            cited = build_cited_answer(answer, chunks)

        st.write(cited["answer"])

        # show a clear pass or fail badge based on the grounding check, plus the match score behind it
        if grounding["grounded"]:
            st.success(f"grounded (best match score {grounding['best_score']:.2f})")
        else:
            st.warning(f"not clearly grounded (best match score {grounding['best_score']:.2f}), answer may be unreliable")

        st.markdown("**Sources**")
        st.markdown(cited["citations"])
else:
    st.info("upload and store at least one document before asking a question")