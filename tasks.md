# Tasks

## Phase 1: Project Setup

- [x] Set up Python environment and install LangChain, ChromaDB, and other dependencies
- [x] Set up API key management for the LLM provider
- [x] Create the basic project folder structure

## Phase 2: Document Ingestion

- [x] Build a loader for PDF files
- [x] Build a loader for plain text or notes files
- [x] Build a loader for scanned reports, using OCR if needed
- [x] Test each loader with a sample document

## Phase 3: Chunking

- [x] Implement a chunking function with configurable chunk size and overlap
- [x] Add logic to adjust chunk size based on document type
- [x] Test chunking output on each document type and check chunk boundaries make sense

## Phase 4: Embedding and Vector Store

- [x] Choose an embedding model
- [x] Compare two embedding models on the same document set and note differences in retrieval results
- [x] Generate embeddings for all chunks
- [x] Store embeddings and chunk metadata in ChromaDB
- [x] Test that stored chunks can be retrieved by similarity search

## Phase 5: Retrieval

- [x] Implement BM25 retrieval over the chunk set
- [x] Implement semantic search retrieval using the vector store
- [x] Test both retrieval methods on a few sample questions and compare results manually

## Phase 6: Hybrid Ranking and Reranking

- [x] Combine BM25 and semantic search results into a single ranked list
- [x] Add a reranking step on top of the combined results
- [x] Test hybrid ranking output against each individual method

## Phase 7: Grounding and Generation

- [x] Build the prompt template that passes retrieved chunks and the question to the LLM
- [x] Add a grounding check step that verifies the generated answer is supported by the retrieved chunks
- [x] Test generation on a few sample questions and check grounding works as expected

## Phase 8: Citation

- [x] Track which chunk and source document each retrieved piece of context came from
- [x] Add source citation to the final answer output
- [x] Test that citations point to the correct chunk and document

## Phase 9: Evaluation

- [x] Select 3 to 5 documents to use for the labeled evaluation set
- [x] Write 8 to 10 question and answer pairs per document
- [x] Mark the ground truth chunk or chunks for each question
- [x] Calculate Precision@K and Recall@K for BM25, semantic search, and hybrid ranking
- [x] Check answer correctness separately from retrieval accuracy
- [x] Summarize evaluation results in a short table or report

## Phase 10: Batch Upload and Cross-document Q&A

- [x] Add support for uploading multiple documents at once
- [x] Update retrieval and ranking logic to search across all uploaded documents
- [x] Test a question that requires pulling information from more than one document

## Phase 11: Documentation and Polish

- [x] Write README with project overview, features, workflow diagram, and evaluation methodology
- [x] Add setup instructions once the actual codebase is finalized
- [x] Clean up code comments and remove any leftover debug code

## Phase 12: Frontend Demo and Deployment

- [x] Build a streamlit interface for uploading documents and asking questions
- [x] Show the generated answer with its grounding status and source citations
- [x] Deploy the app to streamlit community cloud for a shareable link

## Phase 13: Conversational RAG

- [x] Add chat history storage to the streamlit app so prior turns persist within a session
- [x] Build a query rewriting step that condenses the chat history and new question into a standalone query
- [x] Update the prompt template to include recent conversation turns alongside retrieved context
- [x] Update the generator to accept and pass chat history through to the prompt
- [x] Wire history, query rewriting, and generation together in the streamlit app, and display the full conversation thread
- [x] Test multi-turn conversations, including follow-up questions and topic switches, to check retrieval and answers stay accurate
